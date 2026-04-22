#!/usr/bin/env python
# coding: utf-8

import os
import time
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import rp
from rp_overlay import overlay


def get_user_input(prompt, default_value, cast_type=float):
    value = input(f"{prompt} ('Enter' usa {default_value}): ").strip()
    if value == "":
        return default_value
    try:
        return cast_type(value)
    except ValueError:
        print("⚠️ Entrada inválida, se usa valor por defecto.")
        return default_value


def select_channels(available_channels=None):
    if available_channels is None:
        available_channels = [1, 2, 3, 4]
    user_input = input("🔴 Canales a capturar (Ej: 1,2,3,4). 'Enter' usa todos: ").strip()
    if user_input == "":
        return available_channels
    channels = [int(ch) for ch in user_input.replace(",", " ").split() if ch.isdigit()]
    channels = [ch for ch in channels if ch in available_channels]
    return channels if channels else available_channels


def choose_mode():
    print("\nModos disponibles:")
    print("  1) Contador de pulsos")
    print("  2) Escritura de señales en SD (NPZ)")
    value = input("🔴 Selecciona modo [1/2] ('Enter' usa 1): ").strip()
    return "counter" if value in ("", "1") else "npz"


def choose_stop_condition():
    print("\nCondición de parada:")
    print("  1) Tiempo de adquisición")
    print("  2) Cantidad de eventos (triggers)")
    value = input("🔴 Selecciona condición [1/2] ('Enter' usa 1): ").strip()
    if value in ("2",):
        target_events = get_user_input("🔴 Cantidad de eventos objetivo", 1000, int)
        return "events", max(1, target_events)
    acq_time_s = get_user_input("🔴 Tiempo de adquisición [s]", 10.0, float)
    return "time", max(0.1, acq_time_s)


def choose_signal_polarity():
    value = input("🔴 Polaridad esperada del pulso [neg/pos/amb] ('Enter' usa neg): ").strip().lower()
    if value not in ("neg", "pos", "amb"):
        value = "neg"
    return value


def make_trigger_source(channel, polarity):
    letter = {1: "A", 2: "B", 3: "C", 4: "D"}.get(channel, "B")
    suffix = "NE" if polarity == "neg" else "PE"
    name = f"RP_TRIG_SRC_CH{letter}_{suffix}"
    return getattr(rp, name, rp.RP_TRIG_SRC_CHB_NE)


def detect_pulse(signal, threshold, polarity):
    thr = abs(float(threshold))
    if polarity == "neg":
        return bool(np.min(signal) <= -thr)
    if polarity == "pos":
        return bool(np.max(signal) >= thr)
    return bool(np.max(np.abs(signal)) >= thr)


def _extract_data_from_result(result, expected_size):
    if isinstance(result, tuple):
        for item in reversed(result):
            if isinstance(item, np.ndarray):
                return item.astype(np.float32, copy=False)
            if isinstance(item, (list, tuple)) and len(item) == expected_size:
                return np.asarray(item, dtype=np.float32)
    if isinstance(result, np.ndarray):
        return result.astype(np.float32, copy=False)
    if isinstance(result, (list, tuple)) and len(result) == expected_size:
        return np.asarray(result, dtype=np.float32)
    return None


def read_window_vnp(channel_enum, start_pos, samples, total_buffer_size):
    # Optimized path: rp_AcqGetDataPosVNP
    call_attempts = [
        lambda: rp.rp_AcqGetDataPosVNP(channel_enum, start_pos, samples),
        lambda: rp.rp_AcqGetDataPosVNP(channel_enum, int(start_pos), int(samples)),
    ]
    for fn in call_attempts:
        try:
            data = _extract_data_from_result(fn(), samples)
            if data is not None and data.size == samples:
                return data
        except TypeError:
            # Python bindings may expose a different signature across versions.
            pass
        except Exception:
            # Some RP builds can raise runtime exceptions for unsupported calls.
            pass

    # Compatibility fallback when VNP access is not available in local bindings.
    buffer_full = rp.fBuffer(total_buffer_size)
    rp.rp_AcqGetOldestDataV(channel_enum, total_buffer_size, buffer_full)
    rotated = np.asarray([buffer_full[i] for i in range(total_buffer_size)], dtype=np.float32)
    idx = np.arange(start_pos, start_pos + samples) % total_buffer_size
    return rotated[idx]


def acquire_event(channels, samples, samples_delay, total_buffer_size, fs, trig_source):
    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(trig_source)

    while rp.rp_AcqGetTriggerState()[1] != rp.RP_TRIG_STATE_TRIGGERED:
        time.sleep(0.0001)

    trigger_time_ns = time.time_ns()
    trig_pos = rp.rp_AcqGetWritePointerAtTrig()[1]

    post_samples = max(0, samples - samples_delay)
    if post_samples > 0:
        time.sleep(post_samples / fs)

    start_pos = (trig_pos - samples_delay) % total_buffer_size

    data = {}
    for ch in channels:
        ch_enum = getattr(rp, f"RP_CH_{ch}")
        data[f"channel_{ch}"] = read_window_vnp(ch_enum, start_pos, samples, total_buffer_size)

    rp.rp_AcqStop()
    return trigger_time_ns, data


def save_npz_batch(base_name, file_index, timestamps, time_axis, channels, data_by_channel, metadata):
    filename = f"{file_index:04d}_{base_name}.npz"
    payload = {
        "timestamps_ns": np.asarray(timestamps, dtype=np.int64),
        "time_axis_s": time_axis.astype(np.float32),
        "channels": np.asarray(channels, dtype=np.int16),
        "metadata_json": np.asarray(json.dumps(metadata, ensure_ascii=False)),
    }
    for ch in channels:
        payload[f"channel_{ch}"] = np.asarray(data_by_channel[ch], dtype=np.float32)

    np.savez_compressed(filename, **payload)
    return filename


def run_counter_mode(channels, samples, samples_delay, total_buffer_size, fs, trig_source, threshold, polarity, stop_kind, stop_value):
    event_count = 0
    start_ns = time.time_ns()

    per_channel_counts = {ch: 0 for ch in channels}
    per_channel_last_ts = {ch: None for ch in channels}
    per_channel_delta_ts = {ch: [] for ch in channels}
    all_trigger_times = []

    while True:
        now_s = (time.time_ns() - start_ns) / 1e9
        if stop_kind == "time" and now_s >= stop_value:
            break
        if stop_kind == "events" and event_count >= stop_value:
            break

        ts_ns, data = acquire_event(channels, samples, samples_delay, total_buffer_size, fs, trig_source)
        event_count += 1
        all_trigger_times.append(ts_ns)

        for ch in channels:
            signal = data[f"channel_{ch}"]
            if detect_pulse(signal, threshold, polarity):
                per_channel_counts[ch] += 1
                last_ts = per_channel_last_ts[ch]
                if last_ts is not None:
                    per_channel_delta_ts[ch].append((ts_ns - last_ts) / 1e9)
                per_channel_last_ts[ch] = ts_ns

    elapsed_s = max((time.time_ns() - start_ns) / 1e9, 1e-9)

    print("\n================ RESULTADOS MODO CONTADOR ================")
    print(f"Eventos (triggers) adquiridos: {event_count}")
    print(f"Tiempo total de adquisición: {elapsed_s:.6f} s")

    for ch in channels:
        rate = per_channel_counts[ch] / elapsed_s
        print(f"Canal {ch}: pulsos={per_channel_counts[ch]} | tasa={rate:.3f} Hz")
        dts = per_channel_delta_ts[ch]
        if dts:
            print(
                f"  Δt canal {ch}: n={len(dts)} | min={np.min(dts):.9f} s | "
                f"med={np.median(dts):.9f} s | max={np.max(dts):.9f} s"
            )
        else:
            print(f"  Δt canal {ch}: insuficiente cantidad de pulsos detectados")

    if len(all_trigger_times) >= 2:
        global_delta = np.diff(np.asarray(all_trigger_times, dtype=np.int64)) / 1e9
        print(
            f"Δt entre triggers consecutivos: n={global_delta.size} | "
            f"min={np.min(global_delta):.9f} s | med={np.median(global_delta):.9f} s | "
            f"max={np.max(global_delta):.9f} s"
        )


def run_npz_mode(channels, samples, samples_delay, total_buffer_size, fs, trig_source, stop_kind, stop_value, metadata):
    events_per_file = get_user_input("🔴 Eventos por archivo NPZ", 1000, int)
    events_per_file = max(1, events_per_file)

    base_name = datetime.now().strftime("Data_%d%m%Y_%H%M")
    time_axis = np.arange(samples, dtype=np.float32) / fs

    start_ns = time.time_ns()
    event_count = 0
    file_index = 1

    timestamps = []
    data_by_channel = {ch: [] for ch in channels}

    while True:
        now_s = (time.time_ns() - start_ns) / 1e9
        if stop_kind == "time" and now_s >= stop_value:
            break
        if stop_kind == "events" and event_count >= stop_value:
            break

        ts_ns, data = acquire_event(channels, samples, samples_delay, total_buffer_size, fs, trig_source)
        event_count += 1
        timestamps.append(ts_ns)
        for ch in channels:
            data_by_channel[ch].append(data[f"channel_{ch}"])

        if len(timestamps) >= events_per_file:
            filename = save_npz_batch(base_name, file_index, timestamps, time_axis, channels, data_by_channel, metadata)
            print(f"📁 Archivo guardado: {filename} ({len(timestamps)} eventos)")
            file_index += 1
            timestamps = []
            data_by_channel = {ch: [] for ch in channels}

    if timestamps:
        filename = save_npz_batch(base_name, file_index, timestamps, time_axis, channels, data_by_channel, metadata)
        print(f"📁 Archivo guardado: {filename} ({len(timestamps)} eventos)")

    elapsed_s = max((time.time_ns() - start_ns) / 1e9, 1e-9)
    print("\n================ RESULTADOS MODO NPZ ================")
    print(f"Eventos (triggers) adquiridos: {event_count}")
    print(f"Tiempo total de adquisición: {elapsed_s:.6f} s")
    print(f"Tasa global observada: {event_count / elapsed_s:.3f} Hz")


def main():
    print("=================================================================")
    print("\033[1m       Adquisición de datos para Red Pitaya 4IN\033[0m")
    print("=================================================================\n")

    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass

    set_time = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    print(f"\033[1mHora del sistema: {set_time}\033[0m")

    mode = choose_mode()

    dec = rp.RP_DEC_1
    total_buffer_size = 16384
    fs = 125e6 / dec

    channels = select_channels([1, 2, 3, 4])
    trig_channel = get_user_input("🔴 Canal de trigger", channels[0], int)
    if trig_channel not in channels:
        trig_channel = channels[0]

    polarity = choose_signal_polarity()
    trig_lvl = get_user_input("🔴 Nivel de trigger [V]", 0.05, float)

    samples = get_user_input("🔴 Número de muestras por evento", 64, int)
    samples = min(max(8, samples), total_buffer_size)

    default_delay = max(1, samples // 4)
    samples_delay = get_user_input("🔴 Muestras pre-trigger (delay)", default_delay, int)
    samples_delay = min(max(0, samples_delay), samples - 1)

    stop_kind, stop_value = choose_stop_condition()

    trig_source = make_trigger_source(trig_channel, polarity if polarity in ("neg", "pos") else "neg")

    print("\n================ PARÁMETROS ================")
    print(f"Modo: {'Contador de pulsos' if mode == 'counter' else 'Escritura NPZ'}")
    print(f"Canales: {channels}")
    print(f"Canal trigger: {trig_channel}")
    print(f"Polaridad: {polarity}")
    print(f"Nivel trigger: {trig_lvl} V")
    print(f"Muestras/evento: {samples}")
    print(f"Pre-trigger (delay): {samples_delay}")
    print(f"Condición parada: {stop_kind} = {stop_value}")

    print("\n🟢 Inicializando FPGA...")
    _fpga = overlay()
    rp.rp_Init()

    try:
        rp.rp_AcqReset()
        rp.rp_AcqSetDecimation(dec)
        rp.rp_AcqSetTriggerLevel(getattr(rp, f"RP_CH_{trig_channel}"), trig_lvl)
        rp.rp_AcqSetTriggerDelay(0)

        metadata = {
            "set_time_ns": int(set_time.timestamp() * 1e9),
            "sampling_rate_hz": fs,
            "trigger_level_v": trig_lvl,
            "trigger_channel": trig_channel,
            "polarity": polarity,
            "samples_per_event": samples,
            "samples_delay": samples_delay,
            "buffer_size": total_buffer_size,
            "mode": mode,
        }

        if mode == "counter":
            run_counter_mode(
                channels=channels,
                samples=samples,
                samples_delay=samples_delay,
                total_buffer_size=total_buffer_size,
                fs=fs,
                trig_source=trig_source,
                threshold=trig_lvl,
                polarity=polarity,
                stop_kind=stop_kind,
                stop_value=stop_value,
            )
        else:
            run_npz_mode(
                channels=channels,
                samples=samples,
                samples_delay=samples_delay,
                total_buffer_size=total_buffer_size,
                fs=fs,
                trig_source=trig_source,
                stop_kind=stop_kind,
                stop_value=stop_value,
                metadata=metadata,
            )
    finally:
        rp.rp_AcqStop()
        rp.rp_Release()
        print("\n✅ Recursos liberados.")


if __name__ == "__main__":
    main()
