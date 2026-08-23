import numpy as np

def mean_amplitude_spectrum(traces,dt_s):
    x=traces-np.mean(traces,axis=1,keepdims=True)
    amp=np.mean(np.abs(np.fft.rfft(x,axis=1)),axis=0)
    freq=np.fft.rfftfreq(traces.shape[1],d=dt_s)
    peak=float(np.max(amp)) if amp.size else 0.0
    if peak>0: amp=amp/peak
    return freq,amp
