#!/usr/bin/env python
# coding: utf-8

# -----------------------------CONFIG-----------------------------------
EDGE = "NE"
H_TR = 4
H_TR_L = -0.05
READ_CH = [1, 2, 3, 4]
S_TRIG = {1: (-0.05,'n')}
COMMENTS = "fuera_de_bunker"
NREADS = 10000
VERBOSE = True

# ----------------------------------------------------------------------

# ======================================================================
#        Adquisición Multicanal de Datos en 4 Canales para Red Pitaya
# ======================================================================
# 
# Desarrollado por Ing. Mattenet Mariana 
# Departamento de Telecomunicaciones
# Instituto Balseiro - Comisión Nacional de Energía Atómica -
# Año: 2025
# 
# Descripción:
# ------------
# Este script permite la adquisición de datos en una Red Pitaya, capturando 
# señales en múltiples canales de manera simultánea con un trigger basado en 
# un umbral configurable. Los datos se almacenan en archivos HDF5 para una 
# manipulación eficiente.
# 
# Funcionalidades principales:
# ----------------------------
# - Selección de canales de adquisición (1 a 4).
# - Configuración de parámetros de adquisición:
#   * Nivel de trigger (V)
#   * Número de muestras por evento
#   * Delay de muestras
# - Cálculo automático del número máximo de eventos según el espacio disponible en SD.
# - Creación y manejo de archivos HDF5 para almacenar los datos de forma estructurada.
# - División de archivos cuando alcanzan un umbral de tamaño.
# - Configuración de la hora de adquisición (automática o manual).
# 
# Flujo del programa:
# -------------------
# 1. Configuración del entorno y selección de la hora de adquisición.
# 2. Inicialización de la FPGA y configuración del sistema de adquisición.
# 3. Selección de canales y parámetros de adquisición.
# 4. Cálculo del número de eventos posibles según el espacio disponible.
# 5. Inicio de la adquisición:
#     - Espera de eventos con trigger.
#     - Captura de datos y almacenamiento en archivos HDF5.
#     - Creación de nuevos archivos si se supera el tamaño umbral.
# 6. Finalización del proceso y liberación de la FPGA.
# 
# Formato de los archivos HDF5 generados:
# ----------------------------------------
# - Nombre del archivo: `Data_YYMMDD_HHMM_XXXX.h5`
#   (YYMMDD: año, mes, día; HHMM hora, minutos; XXXX: índice secuencial)
# - Atributos generales:
#   * Hora de inicio de adquisición
#   * Tasa de muestreo
#   * Nivel de trigger
#   * Número de muestras por evento y delay
#   * Canales utilizados
#   * Cantidad total de eventos
# - Estructura por evento:
#   /event_000001/
#     ├── channel_1 (array de muestras)
#     ├── channel_2 (array de muestras)
#     ├── channel_3 (array de muestras)
#     ├── channel_4 (array de muestras)
#     ├── timestamp (marca de tiempo del trigger)
# 
# Advertencias:
# -------------
# - Asegúrese de que la tarjeta SD tenga suficiente espacio libre (al menos 200 MB recomendados).
# - Verifique que la Red Pitaya esté correctamente conectada y configurada antes de iniciar la adquisición.
# - Si no se detectan triggers, el proceso puede quedar esperando eventos.
# - Tenga en cuenta que el rango de tensión de las entradas de la Red Pitaya depende de la configuración del
# jumper en la placa (HV: ±20 V, LV: ±1 V). Se recomienda verificar que las señales a adquirir estén dentro
# del rango adecuado antes de comenzar la adquisición.
# 
# Para más información, consulte la documentación oficial:
# https://redpitaya.readthedocs.io/en/latest/intro.html
# 
# Uso:
# ----
# Simplemente ejecute el script en Python. Se le pedirá que ingrese los parámetros necesarios.
# 
# Para más información, consulte la documentación oficial de Red Pitaya:
# https://redpitaya.readthedocs.io/en/latest/intro.html
# 
# Descripción:
# Este programa realiza la adquisición de datos en una Red Pitaya, 
# capturando señales en hasta 4 canales de manera simultánea con un trigger 
# basado en un umbral en el canal 2 (opcional). Utiliza un buffer circular de 
# tamaño 16,384 muestras y permite configurar parámetros como número de muestras 
# por evento, retraso de muestras y cantidad de eventos a capturar.
# 
# Antes de iniciar la adquisición, se deben configurar los parametros de adquisicion 
# deseados y seleccionar si la captura será continua o acotada al espacio libre en 
# la SD de la RedPitaya. Si se elige esta última opción el programa verifica el 
# espacio libre en la SD y se calcula el número máximo de eventos permitidos, asegurando 
# al menos 200 MB libres. 
# 
# Los datos adquiridos se almacenan en formato HDF5, permitiendo optimización y 
# manipulación eficiente de grandes volúmenes de datos. Si se desea trabajar con 
# adquisición de grandes volumenes de datos se puede ejecutar el programa monitor_hdf5
# que transmite los datos capturados a traves de la red y los borra de la memoria de la
# RedPitaya para liberar espacio.
# 
# Nota: El rango de tensión de las entradas de la Red Pitaya depende de la 
# configuración del jumper en la placa (HV: ±20 V, LV: ±1 V). Se recomienda 
# verificar que las señales medidas estén dentro del rango adecuado antes 
# de la adquisición. Para más información, consulte la documentación oficial:
# https://redpitaya.readthedocs.io/en/latest/intro.html
# 
# ==============================================================
# 
# # Descripción:
# Este programa realiza la adquisición de datos en una Red Pitaya, capturando señales en hasta 4 canales de manera simultánea con un trigger basado en un umbral en el canal 2 (opcional). Utiliza un buffer circular de tamaño 16384 muestras y permite configurar parámetros como número de muestras por evento, retraso de muestras y cantidad de eventos a capturar.
# 
# Antes de iniciar la adquisición, se verifica el espacio libre en la SD 
# y se calcula el número máximo de eventos permitidos, asegurando al menos 
# 200 MB libres. Los datos adquiridos se almacenan en formato HDF5, 
# permitiendo optimización y manipulación eficiente de grandes volúmenes 
# de datos. Si se desea trabajar con adquisición de grandes volúmenes de datos
# , se puede ejecutar el programa monitor_hdf5 que transmite los datos capturados a través de la red y los borra de la memoria de la RedPitaya para liberar espacio.
# 
# La adquisición se detiene si luego de 2 horas, el programa no detecta señales que disparen la adquisición configurada por el usuario.
# 
# Nota: El rango de tensión de las entradas de la Red Pitaya depende de la 
# configuración del jumper en la placa (HV: ±20 V, LV: ±1 V). Se recomienda 
# verificar que las señales medidas estén dentro del rango adecuado antes 
# de la adquisición. Para más información, consulte la documentación oficial:
# https://redpitaya.readthedocs.io/en/latest/intro.html
# #==============================================================

import os
import time
import numpy as np
import h5py
from datetime import datetime
from zoneinfo import ZoneInfo
import rp
from rp_overlay import overlay
import pathlib
from matplotlib import pyplot as plt
import argparse

# -----------------------------PARSER-----------------------------------

parser = argparse.ArgumentParser(
            description='')
parser.add_argument('-c','--comments', default=COMMENTS)
parser.add_argument('-n','--nreads', default=NREADS, type=int)
args = parser.parse_args()

run_comment = args.comments
nreads = args.nreads

# -----------------------------FUNCIONES-----------------------------------

def generar_nombre_archivo(file_index):
    """Genera nombre de archivo secuencial."""
    return f"Data_{day_time_of_first_pulse}_{file_index:04d}.h5"

def generar_nombre_carpeta(set_time, channel, trig_lvl, comment=""):
    """
    Genera el nombre de carpeta según la hora, canal y nivel de trigger.
    Ejemplo: Data_20251029_1115_TCH1_TL-090
    """
    day_time_of_first_pulse = set_time.strftime('%Y%m%d_%H%M')
    trig_mV = int(round(trig_lvl * 1000))
    trig_str = f"{trig_mV:+04d}"  # mantiene el signo y 3 dígitos con ceros
    if comment=="":
        folder_name = f"Data_{day_time_of_first_pulse}_TCH{channel}_TL{trig_str}mV"
    else:
        folder_name = f"Data_{day_time_of_first_pulse}_TCH{channel}_TL{trig_str}mV_{comment}"
    return folder_name

def select_trigger_source():
    """Selecciona canal y flanco del trigger."""
    ch = H_TR
    channel_letter = ["A", "B", "C", "D"][ch - 1]
    suffix = EDGE
    const_name = f"RP_TRIG_SRC_CH{channel_letter}_{suffix}"
    trigger_source = getattr(rp, const_name)
    trigger_channel = getattr(rp, f"RP_CH_{ch}")

    return trigger_source, trigger_channel, ch, suffix

# -----------------------------INICIO DEL PROGRAMA-----------------------------------

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass

set_time = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

sys_time_ns = int(datetime.now().timestamp() * 1e9)
set_time_ns = int(set_time.timestamp() * 1e9)

fpga = overlay()
rp.rp_Init()

dec = rp.RP_DEC_1
trig_dly = 0
N = 16384

acq_trig_sour, trig_channel, channel, flanco = select_trigger_source()

trig_lvl = H_TR_L

rp.rp_AcqSetTriggerSrc(acq_trig_sour)
rp.rp_AcqSetTriggerLevel(trig_channel, trig_lvl)

samples = 32
samples_delay = 8

available_channels = [1, 2, 3, 4]
channels_to_acquire = READ_CH

soft_trig = S_TRIG

num_channels = len(channels_to_acquire)
config = {'mode': 'events', 'num_events': nreads, 'duration_minutes': 0}

fs = 125e6 / dec
dt = 1 / fs
time_axis = np.linspace(0, (samples - 1) * dt, samples)

if VERBOSE:
    print(f"🔷 Frecuencia de muestreo = {fs/1e6:.2f} MHz")
    print(f"🔷 Canal de trigger: {channel}")
    print(f"🔷 Flanco = {flanco}")
    print(f"🔷 Nivel de trigger = {trig_lvl} V")
    print(f"🔷 Muestras por evento = {samples}")
    print(f"🔷 Delay de muestras = {samples_delay}")
    print(f"🔷 Canales seleccionados = {channels_to_acquire}")
    print(f"🔷 Hora del sistema: {set_time}")
    if config['mode'] == 'events':
        print(f"🔷 Eventos a adquirir: {config['num_events']}.\n")
    else:
        print(f"🔷 Adquisición durante {config['duration_minutes']} minutos.\n")

day_time_of_first_pulse = set_time.strftime('%Y%m%d_%H%M')

# --- Crear carpeta de salida ---
BASE_DIR = pathlib.Path("/home/jupyter/RedPitaya/DATOS").resolve()


# trig_mV = int(trig_lvl * 1000)
# trig_str = f"{trig_mV:+03d}"[:3]
# folder_name = f"Data_{day_time_of_first_pulse}_TCH{channel}_TL{trig_str}"

folder_name = generar_nombre_carpeta(set_time, channel, trig_lvl, run_comment)


output_dir = BASE_DIR / folder_name
output_dir.mkdir(exist_ok=True, parents=True)
os.chdir(output_dir)

# CONFIGURACIÓN DE PARTICIONAMIENTO
file_threshold_bytes = 10 * 1024 * 1024  # 10 MB
current_file_size = 0
file_index = 1
h5file = None

trigger_times = []
event = 0
start_time = time.time()
max_wait_between_triggers = 60
max_total_duration = config['duration_minutes'] * 60 if config['mode'] == 'time' else float('inf')
max_events = config['num_events'] if config['mode'] == 'events' else config['max_events']


trigger_times = []
first_trigger_ns = None

while True:
    elapsed_total = time.time() - start_time
    if config['mode'] == 'events' and event >= max_events:
        break
    if config['mode'] == 'time' and (elapsed_total >= max_total_duration or event >= max_events):
        break

    if VERBOSE:
        print(f"Progreso: {event + 1}/{max_events}  ", end='\r')



    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(acq_trig_sour)
    wait_start = time.time()
    triggered = False

    while True:
        if rp.rp_AcqGetTriggerState()[1] == rp.RP_TRIG_STATE_TRIGGERED:
            triggered = True
            break
        if (time.time() - wait_start) >= max_wait_between_triggers:
            if VERBOSE:
                print("No se detectaron triggers durante el tiempo máximo de espera. Finalizando...")
            triggered = False
            break
        if config['mode'] == 'time' and (time.time() - start_time) >= max_total_duration:
            triggered = False
            break
        time.sleep(0.001)
    # print (triggered)
    # print(not(triggered))

    if not triggered:
        rp.rp_AcqStop()
        break

    # # Inicializar el tiempo del trigger relativo a 0 ns para mostrar en pantalla
    # first_trigger_ns = None
    # trigger_times = []
    
    # Tiempo relativo al primer trigger 
    trigger_time_ns = time.time_ns()
    trigger_times.append(trigger_time_ns)
    
    if first_trigger_ns is None:
        first_trigger_ns = trigger_time_ns
        relative_ns = 0
    else:
        relative_ns = trigger_time_ns - first_trigger_ns
    
    # imprimir en ns (o elegir unidad legible si preferís)

    if h5file is None:
        current_filename = generar_nombre_archivo(file_index)
        h5file = h5py.File(current_filename, "w")
        # --- metadatos iniciales ---
        h5file.attrs.update({
            'set_time': set_time_ns,
            'sys_time': sys_time_ns,
            'decimation': dec,
            'trigger_level': trig_lvl,
            'trigger_channel': channel,
            'trigger_flank': flanco,
            'trigger_delay': trig_dly,
            'soft_trigger': [key for key in soft_trig],
            'soft_trigger_edge': [key[1] for key in soft_trig.values()],
            'soft_trigger_lv':[key[0] for key in soft_trig.values()],
            'samples_per_event': samples,
            'samples_delay': samples_delay,
            'channels': np.array(channels_to_acquire),
            'sampling_rate': fs,
            'mode': config['mode']
        })
        if config['mode'] == "time":
            h5file.attrs['duration_minutes'] = config['duration_minutes']
        else:
            h5file.attrs['num_events'] = config['num_events']

    time.sleep(samples / (125e6 / dec))

    fbuffers = {ch: rp.fBuffer(N) for ch in channels_to_acquire}
    data = {}
    soft_pass_flag = True
    for ch in channels_to_acquire:
        rp.rp_AcqGetOldestDataV(getattr(rp, f'RP_CH_{ch}'), N, fbuffers[ch])
        data[f'channel_{ch}'] = np.array([
            fbuffers[ch][i + N // 2 - samples_delay] for i in range(samples)
        ], dtype=np.float32)
        if ch in soft_trig:
            match soft_trig[ch][1]:
                case 'n':
                    if np.min(data[f'channel_{ch}']) > soft_trig[ch][0]:
                        soft_pass_flag=False
                        break
                case 'p':
                    if np.max(data[f'channel_{ch}']) < soft_trig[ch][0]:
                        soft_pass_flag=False
                        break
                
    # --- Control real de tamaño ---
    if h5file is not None:
        current_file_size = os.path.getsize(h5file.filename)
    event_size_bytes = samples * num_channels * 4

    if h5file is not None and (current_file_size + event_size_bytes >= file_threshold_bytes):
        h5file.close()
        file_index += 1
        current_filename = generar_nombre_archivo(file_index)
        h5file = h5py.File(current_filename, "w")
        h5file.attrs.update({
            'set_time': set_time_ns,
            'sys_time': sys_time_ns,
            'decimation': dec,
            'trigger_level': trig_lvl,
            'trigger_channel': channel,
            'trigger_flank': flanco,
            'trigger_delay': trig_dly,
            'soft_trigger': [key for key in soft_trig],
            'soft_trigger_edge': [key[1] for key in soft_trig.values()],
            'soft_trigger_lv':[key[0] for key in soft_trig.values()],
            'samples_per_event': samples,
            'samples_delay': samples_delay,
            'channels': np.array(channels_to_acquire),
            'sampling_rate': fs,
            'mode': config['mode']
        })
        if config['mode'] == "time":
            h5file.attrs['duration_minutes'] = config['duration_minutes']
        else:
            h5file.attrs['num_events'] = config['num_events']

    # --- Guardar evento ---
    if soft_pass_flag:
        group = h5file.create_group(f"event_{event + 1:06d}")
        group.attrs['timestamp'] = trigger_time_ns
        for ch in channels_to_acquire:
            group.create_dataset(f"channel_{ch}", data=data[f'channel_{ch}'])
        event += 1
    else:
        pass
        
    rp.rp_AcqStop()
    

# Finalización
if h5file is not None:
    h5file.close()
rp.rp_Release()

if trigger_times:
    elapsed_time = (trigger_times[-1] - trigger_times[0]) / 1e9
    if VERBOSE:
        print(f"\nAdquisición finalizada. Tiempo entre primer y último trigger: {elapsed_time:.6f} s")


