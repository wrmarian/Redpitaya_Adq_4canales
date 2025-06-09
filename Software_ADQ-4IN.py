#!/usr/bin/env python
# coding: utf-8

# ==============================================================
#        Adquisición de Datos en 4 Canales para Red Pitaya
# ==============================================================
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
# - Nombre del archivo: `XXXX_Data_DDMMYYYY_HHMM.h5`
#   (XXXX: índice secuencial, DDMMYYYY_HHMM: fecha/hora del primer evento)
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

# In[1]:


# ==============================================================
#        Adquisición de Datos en 4 Canales para Red Pitaya
# ==============================================================
#
# Desarrollado por Ing. Mattenet Mariana 
# Departamento de Telecomunicaciones
# Instituto Balseiro - Comisión Nacional de Energía Atómica -
# Año: 2025
#
# Descripción:
# Este programa realiza la adquisición de datos en una Red Pitaya, 
# capturando señales en hasta 4 canales de manera simultánea con un trigger 
# basado en un umbral en el canal 2 (opcional). Utiliza un buffer circular de 
# tamaño 16,384 muestras y permite configurar parámetros como número de muestras 
# por evento, retraso de muestras y cantidad de eventos a capturar.
#
# Antes de iniciar la adquisición, se verifica el espacio libre en la SD 
# y se calcula el número máximo de eventos permitidos, asegurando al menos 
# 200 MB libres. Los datos adquiridos se almacenan en formato HDF5, 
# permitiendo optimización y manipulación eficiente de grandes volúmenes 
# de datos. Si se desea trabajar con adquisición de grandes volumenes de datos
# se puede ejecutar el programa monitor_hdf5 que transmite los datos capturados a 
# traves de la red y los borra de la memoria de la RedPitaya para liberar espacio.
#
# Nota: El rango de tensión de las entradas de la Red Pitaya depende de la 
# configuración del jumper en la placa (HV: ±20 V, LV: ±1 V). Se recomienda 
# verificar que las señales medidas estén dentro del rango adecuado antes 
# de la adquisición. Para más información, consulte la documentación oficial:
# https://redpitaya.readthedocs.io/en/latest/intro.html
#
# ==============================================================


# In[2]:


import os
import time
import numpy as np
import h5py
from datetime import datetime
from zoneinfo import ZoneInfo
import rp
from rp_overlay import overlay
from matplotlib import pyplot as plt

# -----------------------------FUNCIONES-----------------------------------

def get_free_space_mb(path="/"):
    """Obtiene el espacio libre en la SD en MB."""
    statvfs = os.statvfs(path)
    free_space = statvfs.f_bavail * statvfs.f_frsize  
    return free_space / (1024 * 1024)

def interpolate_params(channels):
    """Interpola los parámetros F y P (en KB) en función de la cantidad de canales (para 32 muestras)."""
    if channels <= 1:
        return 2.68, 1.59
    elif channels >= 4:
        return 5.10, 2.30
    else:
        F = 2.68 + (5.10 - 2.68) * (channels - 1) / (4 - 1)
        P = 1.59 + (2.30 - 1.59) * (channels - 1) / (4 - 1)
        return F, P

def estimate_file_size(channels, samples, events):
    """Estima el tamaño del archivo (en KB) en función de los eventos."""
    data_payload = (channels * samples * 4) / 1024.0  
    F, P = interpolate_params(channels)
    total_size = F + (events - 1) * (data_payload + P)
    return total_size

def get_max_events(samples, channels):
    """Calcula el número máximo de eventos que se pueden almacenar, solicitando al usuario el número deseado."""
    print("\n\n=================================================================")
    print("\033[1m   Configuración de almacenamiento de datos\033[0m")
    print("=================================================================\n")
    free_space = get_free_space_mb()
    available_space_mb = free_space - 200  # Dejamos 200 MB libres
    if available_space_mb <= 0:
        print("⚠️ No hay suficiente espacio libre en la SD. Libera espacio antes de continuar.")
        exit()
    available_space_kb = available_space_mb * 1024
    per_event_size = estimate_file_size(channels, samples, 1)
    F, _ = interpolate_params(channels)
    max_events = int((available_space_kb) // per_event_size)
    default_events = 10
    try:
        print(f"\nℹ️ Usted puede almacenar en la memoria SD de la Redpitaya un máximo de {max_events} eventos")
        user_input = input(f"🔴 ¿Cuántos eventos deseas guardar? (Máximo: {max_events}, 'Enter' usa {default_events}): ").strip()
        num_events = int(user_input) if user_input else default_events
    except ValueError:
        print("⚠️ Entrada inválida. Se guardarán 10 eventos por defecto.")
        num_events = default_events
    est_size = estimate_file_size(channels, samples, num_events)
    print(f"🔷 Espacio disponible (dejando 200 MB libres): {available_space_mb:.2f} MB")
    print(f"🔷 Máximo de eventos que se pueden guardar: {max_events}")
    print(f"🔷 Tamaño estimado para {num_events} eventos: {est_size:.2f} KB")
    return min(num_events, max_events)

def select_channels(available_channels=[1, 2, 3, 4]):
    """Permite al usuario seleccionar qué canales capturar."""
    user_input = input("🔴 Ingresa los canales a capturar (Ej: 1,2,3,4 o 1 2 3 4). 'Enter' usa todos: ")
    if user_input.strip() == "":
        return available_channels
    try:
        channels = [int(ch) for ch in user_input.replace(",", " ").split() if ch.strip().isdigit()]
        channels = [ch for ch in channels if ch in available_channels]
        return channels if channels else available_channels
    except:
        print("⚠️ Error en la entrada, usando todos los canales.")
        return available_channels

def get_user_input(prompt, default_value, cast_type=float):
    """Obtiene un valor del usuario, usando un valor por defecto si no se ingresa nada."""
    user_input = input(f"{prompt} ('Enter' usa {default_value}): ").strip()
    try:
        return cast_type(user_input) if user_input else default_value
    except ValueError:
        print("⚠️ Entrada inválida, usando valor por defecto.")
        return default_value

def create_custom_time():
    """Permite crear una fecha/hora personalizada."""
    while True:
        try:
            day = int(input("📅 Ingresa el día (1-31): "))
            if not 1 <= day <= 31:
                raise ValueError("Día inválido, debe estar entre 1 y 31.")
            month = int(input("📅 Ingresa el mes (1-12): "))
            if not 1 <= month <= 12:
                raise ValueError("Mes inválido, debe estar entre 1 y 12.")
            year = int(input("📅 Ingresa el año (ej.: 2025): "))
            hour = int(input("🕒 Ingresa la hora (0-23): "))
            if not 0 <= hour < 24:
                raise ValueError("Hora inválida, debe estar entre 0 y 23.")
            minute = int(input("🕒 Ingresa los minutos (0-59): "))
            if not 0 <= minute < 60:
                raise ValueError("Minutos inválidos, deben estar entre 0 y 59.")
            return datetime(year, month, day, hour, minute, 0)
        except ValueError as e:
            print(f"❌ Error: {e}. Intenta de nuevo.")

def generar_nombre_archivo(file_index):
    """Genera un nombre de archivo usando el timestamp del primer pulso y un índice secuencial."""
    return f"{file_index:04d}_Data_{day_time_of_first_pulse}.h5"

# -----------------------------INICIO DEL PROGRAMA-----------------------------------

print("=================================================================")
print("\033[1m          Adquisición de datos para Red Pitaya\033[0m")
print("=================================================================\n")

# Cambiar al directorio del script (si se ejecuta como script, __file__ está definido)
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # En entornos interactivos (__file__ no está definido)
    pass

# ⏳ Configuración de tiempo
set_time = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
print(f"\033[1m     Hora del sistema: {set_time}\033[0m\n")
time_option = input(f"🔴 ¿Desea utilizar la hora del sistema o establecer una personalizada? (S = sistema, C = custom): ").strip().lower()
if time_option == 'c':
    set_time = create_custom_time()
    print(f"ℹ️ Hora utilizada: {set_time}\n")
sys_time_ns = int(datetime.now().timestamp() * 1e9)
set_time_ns = int(set_time.timestamp() * 1e9)

# Definir day_time_of_first_pulse usando la hora seleccionada
day_time_of_first_pulse = set_time.strftime('%d%m%Y_%H%M')

# 🟢 Inicializar FPGA
print("\n🟢 INICIANDO FPGA...\n")
fpga = overlay()
rp.rp_Init()

# Configuración de adquisición
dec = rp.RP_DEC_1
trig_dly = 0
acq_trig_sour = rp.RP_TRIG_SRC_CHB_NE
N = 16384

# Pedir al usuario configurar trig_lvl, muestras y delay

print("\n\n=================================================================")
print("\033[1m   Configuración de los parametros de adquisición\033[0m")
print("=================================================================\n")
trig_lvl = get_user_input("\n🔴 Ingrese el nivel de trigger [V]", 0.01)
# print(f"ℹ️ Trigger: {trig_lvl} V")
samples = get_user_input("🔴 Ingrese el número de muestras por evento", 32, int)
# print("ℹ️ Muestras por evento:", samples)
samples_delay = get_user_input("🔴 Ingrese el delay de muestras", 8, int)
# print(f"ℹ️ Delay de muestras: {samples_delay}")

# Seleccionar canales
available_channels = [1, 2, 3, 4]
channels_to_acquire = select_channels(available_channels)
# print("ℹ️ Canales seleccionados:", channels_to_acquire)

num_channels = len(channels_to_acquire)
num_events = get_max_events(samples, num_channels)

# Definir frecuencia de muestreo (fs) y construir el eje de tiempo
fs = 125e6 / dec
dt = 1 / fs
time_axis = np.linspace(0, (samples - 1) * dt, samples)

# Mostrar parámetros de adquisición
print("\n\n=================================================================")
print("\033[1m PARÁMETROS DE ADQUISICIÓN SELECCIONADOS\033[0m")
print("=================================================================\n")
print(f"\n🔷 Frecuencia de muestreo = {fs/1e6:.2f} MHz")
print(f"🔷 Nivel de trigger = {trig_lvl} V")
print(f"🔷 Muestras por evento = {samples}")
print(f"🔷 Delay de muestras = {samples_delay}")
print(f"🔷 Eventos a capturar = {num_events}")
print(f"🔷 Canales seleccionados = {channels_to_acquire}")
print(f"🔷 Hora utilizada: {set_time}\n")
# print("=================================================================\n")

# CONFIGURACIÓN DE PARTICIONAMIENTO DE ARCHIVOS
file_threshold_bytes = 0.02 * 1024 * 1024  # Umbral (1 MB)
current_file_size = 0
file_index = 1
current_filename = generar_nombre_archivo(file_index)

# Abrir el archivo y escribir metadata global
h5file = h5py.File(current_filename, "w")
h5file.attrs['set_time'] = set_time_ns
h5file.attrs['sys_time'] = sys_time_ns
h5file.attrs['decimation'] = dec
h5file.attrs['trigger_level'] = trig_lvl
h5file.attrs['trigger_delay'] = trig_dly
h5file.attrs['samples_per_event'] = samples
h5file.attrs['samples_delay'] = samples_delay
h5file.attrs['channels'] = np.array(channels_to_acquire)
h5file.attrs['num_events'] = num_events
h5file.attrs['sampling_rate'] = fs

# INICIO DE LA ADQUISICIÓN
trigger_times = []
# print("\n=================================================================")
print("\033[1m🟢 INICIANDO ADQUISICIÓN...\033[0m\n")
print(f"📁 Archivo creado: {current_filename}\n")
for event in range(num_events):
    print(f"🟡 Ciclo {event + 1}/{num_events}")

    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(acq_trig_sour)
    while rp.rp_AcqGetTriggerState()[1] != rp.RP_TRIG_STATE_TRIGGERED:
        time.sleep(0.001)
    trigger_time_ns = time.time_ns()
    trigger_times.append(trigger_time_ns)
    print(f"🔺 Trigger detectado en {trigger_time_ns} ns")

    time.sleep(samples / (125e6/dec))  

    fbuffers = {ch: rp.fBuffer(N) for ch in channels_to_acquire}
    data = {}    
    for ch in channels_to_acquire:
        rp.rp_AcqGetOldestDataV(getattr(rp, f'RP_CH_{ch}'), N, fbuffers[ch])
        data[f'channel_{ch}'] = np.array([fbuffers[ch][i + N//2 - samples_delay] for i in range(samples)], dtype=np.float32)

    event_size_bytes = samples * num_channels * 4  
    if current_file_size + event_size_bytes > file_threshold_bytes:
        h5file.close()
        file_index += 1
        current_filename = generar_nombre_archivo(file_index)
        h5file = h5py.File(current_filename, "w")
        h5file.attrs['set_time'] = set_time_ns
        h5file.attrs['sys_time'] = sys_time_ns
        h5file.attrs['decimation'] = dec
        h5file.attrs['trigger_level'] = trig_lvl
        h5file.attrs['trigger_delay'] = trig_dly
        h5file.attrs['samples_per_event'] = samples
        h5file.attrs['samples_delay'] = samples_delay
        h5file.attrs['channels'] = np.array(channels_to_acquire)
        h5file.attrs['num_events'] = num_events
        h5file.attrs['sampling_rate'] = fs
        current_file_size = 0
        print(f"\n📁 Se creó un nuevo archivo: {current_filename}\n")

    group = h5file.create_group(f"event_{event+1:06d}")
    group.attrs['timestamp'] = trigger_time_ns
    for ch in channels_to_acquire:
        group.create_dataset(f"channel_{ch}", data=data[f'channel_{ch}'])

    current_file_size += event_size_bytes
    rp.rp_AcqStop()

h5file.close()
rp.rp_Release()

print("\n✅ Adquisición completada.")

if trigger_times:
    elapsed_time = (trigger_times[-1] - trigger_times[0]) / 1e9
    print(f"\n⏱️ Tiempo transcurrido entre el primer y el último trigger: {elapsed_time:.6f} segundos")
else:
    print("⚠️ No se detectaron triggers.")


# In[ ]:




