#!/usr/bin/env python
# coding: utf-8

# -----------------------------CONFIG-----------------------------------
EDGE = "NE"
H_TR = 1
H_TR_L = -0.01
READ_CH = [1]
S_TRIG = {}
EXPTIME = 10 #minutos
AVGTIME = 2 #segundos
MAXFREQ = 70 #número de cuentas por segundo que llenan el indicador
VERBOSE = True

# ----------------------------------------------------------------------

import time
import numpy as np
import rp
from rp_overlay import overlay
import argparse

# -----------------------------PARSER-----------------------------------

parser = argparse.ArgumentParser(
            description='')
parser.add_argument('--trigger', default=H_TR_L, type=float)
parser.add_argument('--avg', default=AVGTIME, type=int)
parser.add_argument('--time', default=EXPTIME, type=int)
parser.add_argument('--max', default=MAXFREQ, type=float)
#parser.add_argument("--verbose", action="store_true",help="increase output verbosity")
args = parser.parse_args()

# -----------------------------FUNCIONES-----------------------------------

def select_trigger_source():
    """Selecciona canal y flanco del trigger."""
    ch = H_TR
    channel_letter = ["A", "B", "C", "D"][ch - 1]
    suffix = EDGE
    const_name = f"RP_TRIG_SRC_CH{channel_letter}_{suffix}"
    trigger_source = getattr(rp, const_name)
    trigger_channel = getattr(rp, f"RP_CH_{ch}")
    return trigger_source, trigger_channel, ch, suffix

def led_flash(n=10):
    for i in range(n):
        rp.rp_LEDSetState(127)
        time.sleep(0.05)
        rp.rp_LEDSetState(0)
        time.sleep(0.05)
    return 0

def led_blink(t=0.01):
    rp.rp_DpinSetState(rp.RP_LED0, rp.RP_HIGH)
    time.sleep(t)
    rp.rp_DpinSetState(rp.RP_LED0, rp.RP_LOW)
    return 0

def led_power(lv=1):
    lv = int(lv)
    if lv in [1,2,3,4,5,6,7]:
        led = 2**(lv+1)-2
        rp.rp_LEDSetState(2**lv-2)
    elif lv > 7:
        led = 2**8-2
        rp.rp_LEDSetState(led)
    elif lv < 1:
        rp.rp_LEDSetState(0)
    return 0

# -----------------------------INICIO DEL PROGRAMA-----------------------------------
fpga = overlay()
rp.rp_Init()

dec = rp.RP_DEC_1
trig_dly = 0
N = 16384

acq_trig_sour, trig_channel, channel, flanco = select_trigger_source()

trig_lvl = args.trigger
exptime = args.time
avgtime = args.avg
maxfreq = args.max

rp.rp_AcqSetTriggerSrc(acq_trig_sour)
rp.rp_AcqSetTriggerLevel(trig_channel, trig_lvl)

samples = 32
samples_delay = 8

start_time = time.time()

led_flash()

trigcount = 0
checkpoint_time = time.time()

while True:
    elapsed_total = time.time() - start_time
 
    if (elapsed_total >= exptime*60):
        break

    if time.time() > (checkpoint_time + avgtime):
        cps = trigcount/avgtime 
        led_power(lv=cps*8/maxfreq)
        if VERBOSE: print(f"Eventos por segundo: {(cps * 100 // 1) / 100}  ", end='\r')
        checkpoint_time = time.time()
        trigcount = 0

    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(acq_trig_sour)

    while True:
        if rp.rp_AcqGetTriggerState()[1] == rp.RP_TRIG_STATE_TRIGGERED:
            trigcount += 1
            led_blink()
            break

        #time.sleep(0.001)

    
    rp.rp_AcqStop()
    
rp.rp_Release()
