# Adquisición de Datos en 4 Canales con Red Pitaya

Este proyecto implementa un sistema de adquisición de datos multicanal basado en la Red Pitaya modelo STEMlab 125-14-4IN, diseñado para la detección de coincidencias de rayos cósmicos mediante señales captadas por hasta cuatro entradas analógicas.

El sistema ha sido desarrollado en Python y permite configurar de forma flexible los parámetros de adquisición, almacenar los datos en archivos HDF5 y operar tanto en modo local como en modo continuo con transferencia en red.

---

## 📌 Características principales

- Adquisición multicanal (1 a 4 canales).
- Trigger configurable (nivel de umbral y canal).
- Selección del número de eventos, muestras por evento y delay relativo al trigger.
- Estimación automática del número máximo de eventos según espacio disponible.
- Almacenamiento en archivos HDF5 estructurados y rotación automática al superar tamaño límite.
- Opción de hora de adquisición automática o manual.
- Visualización de eventos con gráficos superpuestos por canal.
- Modo continuo con transferencia de datos por red.

---

## 🖥️ Requisitos

- **Red Pitaya 125-14-4IN** con sistema operativo oficial versión 2.00+
- Python 3 (instalado por defecto)
- Librerías Python: `numpy`, `h5py`, `matplotlib`, `os`, `time`, `zoneinfo`

Instalación de dependencias (si fuera necesario):

```bash
pip3 install numpy h5py matplotlib
```

---

## 🚀 Ejecución

### 1. Subir el archivo

Desde tu PC:

```bash
scp Software_ADQ-4IN.py root@<ip_redpitaya>:/root/
```

o vía navegador en:  
`http://rp-xxxxxx.local/jlab` → Upload → `/RedPitaya/`

### 2. Conectarse por SSH

```bash
ssh root@<ip_redpitaya>
cd /root/
python3 Software_ADQ-4IN.py
```

---

## 🗂️ Estructura de archivos HDF5

Cada archivo generado sigue la forma:

```
XXXX_Data_DDMMYYYY_HHMM.h5
```

### Contenido:

- Atributos globales: hora, trigger, delay, tasa de muestreo, etc.
- Grupos por evento: `/event_000001/`, `/event_000002/`, ...
- Datasets por canal: `channel_1`, `channel_2`, ...
- Timestamp por evento

---

## ⚠️ Advertencias

- Verificar que haya al menos 200 MB libres en la SD.
- Asegurarse de que las señales de entrada estén dentro del rango permitido según la configuración del jumper:
  - HV: ±20 V
  - LV: ±1 V
- En caso de no detectarse triggers, el programa quedará esperando indefinidamente.

---

## 🔬 Aplicaciones

- Experimentos educativos en física.
- Estudios de coincidencias en rayos cósmicos.
- Prototipado de sistemas de adquisición para señales rápidas.

---

## 👩‍💻 Autora

**Ing. Mariana Mattenet**  
Departamento de Telecomunicaciones  
Instituto Balseiro – CNEA  
📧 mariana.mattenet@ib.edu.ar

---

## 📄 Licencia

Este proyecto se encuentra bajo la licencia MIT. Ver archivo `LICENSE`.

---

## 🔗 Referencias

- [Red Pitaya Docs](https://redpitaya.readthedocs.io/en/latest/)
- [Página oficial de Red Pitaya](https://redpitaya.com/)
