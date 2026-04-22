#!/usr/bin/env python
# coding: utf-8

import json
import os
import pathlib
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import rp
from rp_overlay import overlay


def get_delta_time_ns(ptr_trig, N, fs, state):
    """Tiempo entre triggers consecutivos en ns (con manejo de wrap del buffer circular)."""
    if state["prev_ptr"] is None:
        state["prev_ptr"] = ptr_trig
        return 0

    if ptr_trig >= state["prev_ptr"]:
        delta_samples = ptr_trig - state["prev_ptr"]
    else:
        delta_samples = ptr_trig + N - state["prev_ptr"]

    state["prev_ptr"] = ptr_trig
    return int(delta_samples * (1e9 / fs))


def get_free_space_mb(path="/"):
    statvfs = os.statvfs(path)
    free_space = statvfs.f_bavail * statvfs.f_frsize
    return free_space / (1024 * 1024)


def interpolate_params(channels):
    if channels <= 1:
        return 2.68, 1.59
    if channels >= 4:
        return 5.10, 2.30
    F = 2.68 + (5.10 - 2.68) * (channels - 1) / (4 - 1)
    P = 1.59 + (2.30 - 1.59) * (channels - 1) / (4 - 1)
    return F, P


def estimate_file_size_kb(channels, samples, events):
    data_payload = (channels * samples * 4) / 1024.0
    F, P = interpolate_params(channels)
    return F + (events - 1) * (data_payload + P)


def get_max_events_or_time(samples, channels):
    print("\n\n=================================================================")
    print("\033[1m   Configuración de almacenamiento de datos\033[0m")
    print("=================================================================\n")

    free_space = get_free_space_mb()
    available_space_mb = free_space - 200
    if available_space_mb <= 0:
        print("⚠️ No hay suficiente espacio libre en la SD. Libera espacio antes de continuar.")
        raise SystemExit(1)

    available_space_kb = available_space_mb * 1024
    per_event_size_kb = estimate_file_size_kb(channels, samples, 1)
    max_events = int(available_space_kb // per_event_size_kb)

    print(f"🔷 Espacio disponible (dejando 200 MB libres): {available_space_mb:.2f} MB")
    print(f"🔷 Máximo de eventos que se pueden guardar: {max_events}")
    print("\n🔴 ¿Deseas limitar la grabación por cantidad de eventos o por duración?")
    print("    E - número de eventos (default)")
    print("    T - duración en minutos")
    option = input(" ").strip().lower()

    if option == "t":
        while True:
            try:
                minutes = float(input("⏳ ¿Cuántos minutos deseas grabar? (Ej: 1.5): ").strip())
                if minutes <= 0:
                    raise ValueError("El tiempo debe ser mayor que cero.")
                return {"mode": "time", "duration_minutes": minutes, "max_events": max_events}
            except ValueError as e:
                print(f"⚠️ Entrada inválida: {e}")
    else:
        default_events = 10
        try:
            user_input = input(
                f"🔴 ¿Cuántos eventos deseas guardar? (Máximo {max_events}, Enter usa {default_events}): "
            ).strip()
            num_events = int(user_input) if user_input else default_events
        except ValueError:
            print("⚠️ Entrada inválida. Se guardarán 10 eventos por defecto.")
            num_events = default_events
        num_events = min(num_events, max_events)
        est_size = estimate_file_size_kb(channels, samples, num_events)
        print(f"🔷 Tamaño estimado para {num_events} eventos: {est_size:.2f} KB")
        return {"mode": "events", "num_events": num_events}


def select_channels(available_channels=None):
    if available_channels is None:
        available_channels = [1, 2, 3, 4]
    user_input = input("🔴 Ingresa los canales a capturar (Ej: 1,2,3,4 o 1 2 3 4). 'Enter' usa todos: ")
    if user_input.strip() == "":
        return available_channels
    try:
        channels = [int(ch) for ch in user_input.replace(",", " ").split() if ch.strip().isdigit()]
        channels = [ch for ch in channels if ch in available_channels]
        return channels if channels else available_channels
    except Exception:
        print("⚠️ Error en la entrada, usando todos los canales.")
        return available_channels


def select_trigger_source():
    edge_input = input("🔴 Tipo de flanco (P = positivo, N = negativo) [Default: N]: ").strip().upper()
    edge = edge_input if edge_input in ["P", "N"] else "N"

    while True:
        channel_input = input("🔴 Canal de trigger (1–4) [Default: 1]: ").strip()
        try:
            ch = int(channel_input) if channel_input else 1
            if ch in [1, 2, 3, 4]:
                break
            print("⚠️ Canal inválido. Debe ser 1 a 4.")
        except ValueError:
            print("⚠️ Entrada inválida, usando canal 1.")

    channel_letter = ["A", "B", "C", "D"][ch - 1]
    suffix = "PE" if edge == "P" else "NE"
    const_name = f"RP_TRIG_SRC_CH{channel_letter}_{suffix}"
    trigger_source = getattr(rp, const_name)
    trigger_channel = getattr(rp, f"RP_CH_{ch}")
    print(f"   --> Trigger: Canal {ch}, flanco {'positivo' if edge == 'P' else 'negativo'} ({const_name})")
    return trigger_source, trigger_channel, ch, suffix


def get_user_input(prompt, default_value, cast_type=float):
    user_input = input(f"{prompt} ('Enter' usa {default_value}): ").strip()
    try:
        return cast_type(user_input) if user_input else default_value
    except ValueError:
        print("⚠️ Entrada inválida, usando valor por defecto.")
        return default_value


def create_custom_time():
    while True:
        try:
            day = int(input("📅 Día (1–31): "))
            month = int(input("📅 Mes (1–12): "))
            year = int(input("📅 Año (ej. 2025): "))
            hour = int(input("🕒 Hora (0–23): "))
            minute = int(input("🕒 Minuto (0–59): "))
            return datetime(year, month, day, hour, minute, 0)
        except ValueError as e:
            print(f"❌ Error: {e}. Intenta de nuevo.")


def generar_nombre_archivo(day_time_of_first_pulse, file_index):
    return f"Data_{day_time_of_first_pulse}_{file_index:04d}.npz"


def generar_nombre_carpeta(set_time, channel, trig_lvl):
    day_time_of_first_pulse = set_time.strftime("%Y%m%d_%H%M")
    trig_mV = int(round(trig_lvl * 1000))
    trig_str = f"{trig_mV:+04d}"
    return f"Data_{day_time_of_first_pulse}_TCH{channel}_TL{trig_str}mV"


def read_event_data_pos_vnp(ptr_trig, channels_to_acquire, samples, samples_delay, N):
    """Lee ventana de muestras por canal usando rp_AcqGetDataPosVNP.

    Incluye fallback compatible para firmwares con firma diferente.
    """
    start_pos = (ptr_trig + N - samples_delay) % N
    data = {}

    for ch in channels_to_acquire:
        rp_ch = getattr(rp, f"RP_CH_{ch}")
        out = np.empty(samples, dtype=np.float32)
        read_ok = False

        call_variants = (
            lambda: rp.rp_AcqGetDataPosVNP(rp_ch, start_pos, samples, out),
            lambda: rp.rp_AcqGetDataPosVNP(rp_ch, start_pos, samples),
            lambda: rp.rp_AcqGetDataPosVNP(rp_ch, start_pos, (start_pos + samples - 1) % N, out),
        )

        for call in call_variants:
            try:
                ret = call()
                if isinstance(ret, tuple) and len(ret) >= 2:
                    candidate = np.asarray(ret[-1], dtype=np.float32)
                    if candidate.size >= samples:
                        data[f"channel_{ch}"] = candidate[:samples]
                        read_ok = True
                        break
                elif ret is not None and not isinstance(ret, (int, np.integer)):
                    candidate = np.asarray(ret, dtype=np.float32)
                    if candidate.size >= samples:
                        data[f"channel_{ch}"] = candidate[:samples]
                        read_ok = True
                        break
                elif np.any(out):
                    data[f"channel_{ch}"] = out.copy()
                    read_ok = True
                    break
            except TypeError:
                continue
            except Exception:
                continue

        if not read_ok:
            fb = rp.fBuffer(N)
            rp.rp_AcqGetOldestDataV(rp_ch, N, fb)
            data[f"channel_{ch}"] = np.array([fb[(start_pos + i) % N] for i in range(samples)], dtype=np.float32)

    return data


def flush_npz(output_dir, day_time_of_first_pulse, file_index, chunk_events, chunk_meta, global_metadata):
    if not chunk_events:
        return None

    filename = generar_nombre_archivo(day_time_of_first_pulse, file_index)
    fullpath = output_dir / filename

    arrays = {
        "metadata_json": np.array(json.dumps(global_metadata, ensure_ascii=False)),
        "event_index": np.array([m["event_index"] for m in chunk_meta], dtype=np.int64),
        "timestamp_fpga_ns": np.array([m["timestamp_fpga_ns"] for m in chunk_meta], dtype=np.int64),
        "delta_fpga_ns": np.array([m["delta_fpga_ns"] for m in chunk_meta], dtype=np.int64),
        "timestamp_linux_ns": np.array([m["timestamp_linux_ns"] for m in chunk_meta], dtype=np.int64),
    }

    channels = global_metadata["channels"]
    for ch in channels:
        arrays[f"channel_{ch}"] = np.stack([ev[f"channel_{ch}"] for ev in chunk_events]).astype(np.float32)

    np.savez_compressed(fullpath, **arrays)
    return filename


print("=================================================================")
print("\033[1m          Adquisición de datos para Red Pitaya\033[0m")
print("=================================================================\n")

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")
set_time = datetime.now(TZ_AR)
print(f"\033[1m     Hora local Argentina: {set_time}\033[0m\n")
time_option = input("🔴 ¿Usar hora del sistema o personalizada? (S = sistema, C = custom): ").strip().lower()
if time_option == "c":
    set_time = create_custom_time()
    print(f"ℹ️ Hora local Argentina: {set_time}\n")

print("\n🟢 INICIANDO FPGA...\n")
fpga = overlay()
rp.rp_Init()

dec = rp.RP_DEC_1
trig_dly = 0
N = 16384

print("\n\n=================================================================")
print("\033[1m   Configuración de los parámetros de adquisición\033[0m")
print("=================================================================\n")

acq_trig_sour, trig_channel, channel, flanco = select_trigger_source()
trig_lvl = get_user_input("🔴 Nivel de trigger [V]", -0.05)
samples = get_user_input("\n🔴 Número de muestras por evento", 32, int)
samples_delay = get_user_input("🔴 Delay de muestras", 8, int)

available_channels = [1, 2, 3, 4]
channels_to_acquire = select_channels(available_channels)
num_channels = len(channels_to_acquire)
config = get_max_events_or_time(samples, num_channels)

fs = 125e6 / dec

print("\n\n=================================================================")
print("\033[1m PARÁMETROS DE ADQUISICIÓN SELECCIONADOS\033[0m")
print("=================================================================\n")
print(f"🔷 Frecuencia de muestreo = {fs/1e6:.2f} MHz")
print(f"🔷 Canal de trigger: {channel}")
print(f"🔷 Flanco = {flanco}")
print(f"🔷 Nivel de trigger = {trig_lvl} V")
print(f"🔷 Muestras por evento = {samples}")
print(f"🔷 Delay de muestras = {samples_delay}")
print(f"🔷 Canales seleccionados = {channels_to_acquire}")
if config["mode"] == "events":
    print(f"🔷 Eventos a adquirir: {config['num_events']}\n")
else:
    print(f"🔷 Adquisición durante {config['duration_minutes']} minutos.\n")

day_time_of_first_pulse = set_time.strftime("%Y%m%d_%H%M")
BASE_DIR = pathlib.Path(os.getenv("REDPITAYA_DATA_DIR", "/home/jupyter/RedPitaya/DATOS")).resolve()
folder_name = generar_nombre_carpeta(set_time, channel, trig_lvl)
output_dir = BASE_DIR / folder_name
output_dir.mkdir(exist_ok=True, parents=True)
os.chdir(output_dir)
print(f"📂 Ruta a carpeta de DATOS: {output_dir}\n")

file_threshold_bytes = 10 * 1024 * 1024
file_index = 1
chunk_events = []
chunk_meta = []
chunk_size_bytes = 0

event = 0
start_time = time.time()
trigger_times_linux = []

MAX_WAIT_BETWEEN_TRIGGERS_S = 60
LOG_EVERY_EVENTS = 100
max_total_duration = config["duration_minutes"] * 60 if config["mode"] == "time" else float("inf")
max_events = config["num_events"] if config["mode"] == "events" else config["max_events"]

state = {"prev_ptr": None}
fpga_time_ns = 0
channel_counts = {ch: 0 for ch in channels_to_acquire}

global_metadata = {
    "timestamp_local_iso": set_time.isoformat(),
    "timezone": "America/Argentina/Buenos_Aires",
    "timestamp_utc": set_time.astimezone(ZoneInfo("UTC")).isoformat(),
    "decimation": int(dec),
    "trigger_level": float(trig_lvl),
    "trigger_channel": int(channel),
    "trigger_flank": flanco,
    "trigger_delay": int(trig_dly),
    "samples_per_event": int(samples),
    "samples_delay": int(samples_delay),
    "channels": channels_to_acquire,
    "sampling_rate": float(fs),
    "mode": config["mode"],
}
if config["mode"] == "time":
    global_metadata["duration_minutes"] = float(config["duration_minutes"])
else:
    global_metadata["num_events"] = int(config["num_events"])

rp.rp_AcqSetTriggerLevel(trig_channel, trig_lvl)

print("\033[1m🟢 INICIANDO ADQUISICIÓN...\033[0m\n")
while True:
    elapsed_total = time.time() - start_time
    if config["mode"] == "events" and event >= max_events:
        break
    if config["mode"] == "time" and (elapsed_total >= max_total_duration or event >= max_events):
        break

    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(acq_trig_sour)

    wait_start = time.time()
    triggered = False
    ptr_trig = 0

    while True:
        if rp.rp_AcqGetTriggerState()[1] == rp.RP_TRIG_STATE_TRIGGERED:
            ptr_trig = rp.rp_AcqGetWritePointerAtTrig()[1]
            triggered = True
            break
        if (time.time() - wait_start) >= MAX_WAIT_BETWEEN_TRIGGERS_S:
            print("No se detectaron triggers durante el tiempo máximo de espera. Finalizando...")
            break
        if config["mode"] == "time" and (time.time() - start_time) >= max_total_duration:
            break
        time.sleep(0.0001)

    if not triggered:
        rp.rp_AcqStop()
        break

    delta_ns = get_delta_time_ns(ptr_trig, N, fs, state)
    fpga_time_ns += delta_ns
    data = read_event_data_pos_vnp(ptr_trig, channels_to_acquire, samples, samples_delay, N)

    rp.rp_AcqStop()
    trigger_linux_ns = time.time_ns()
    trigger_times_linux.append(trigger_linux_ns)

    chunk_events.append(data)
    chunk_meta.append(
        {
            "event_index": event + 1,
            "timestamp_fpga_ns": fpga_time_ns,
            "delta_fpga_ns": delta_ns,
            "timestamp_linux_ns": trigger_linux_ns,
        }
    )
    for ch in channels_to_acquire:
        channel_counts[ch] += 1

    event_size_bytes = samples * num_channels * 4
    chunk_size_bytes += event_size_bytes
    event += 1

    if chunk_size_bytes >= file_threshold_bytes:
        saved_file = flush_npz(
            output_dir=output_dir,
            day_time_of_first_pulse=day_time_of_first_pulse,
            file_index=file_index,
            chunk_events=chunk_events,
            chunk_meta=chunk_meta,
            global_metadata=global_metadata,
        )
        if saved_file is not None:
            print(f"📁 Archivo guardado: {saved_file}")
        file_index += 1
        chunk_events = []
        chunk_meta = []
        chunk_size_bytes = 0

    if event <= 10 or event % LOG_EVERY_EVENTS == 0:
        print(f"Evento {event}: Δt = {delta_ns / 1e3:.1f} us")

saved_file = flush_npz(
    output_dir=output_dir,
    day_time_of_first_pulse=day_time_of_first_pulse,
    file_index=file_index,
    chunk_events=chunk_events,
    chunk_meta=chunk_meta,
    global_metadata=global_metadata,
)
if saved_file is not None:
    print(f"📁 Archivo guardado: {saved_file}")

rp.rp_Release()
print("\n✅ Adquisición finalizada.")

elapsed_time = time.time() - start_time
print(f"\n⏱️ Tiempo total adquisición (Linux): {elapsed_time:.6f} s")

if elapsed_time > 0:
    print("\n📈 Tasa por canal:")
    for ch in channels_to_acquire:
        rate = channel_counts[ch] / elapsed_time
        print(f"   CH{ch}: {channel_counts[ch]} eventos, {rate:.2f} eventos/s")
