import numpy as np
import bisect

import scipy.signal

import fftfilt

lpf = scipy.signal.firwin(256,1/256.)

class DataBlock():
    def __init__(self, data, tone, fftbin, 
                     nsamp, nfft, wavenorm, t0 = 0, fs = 512e6,
                     sweep_index = 0, mmw_source_freq=0.0, mmw_source_modulation_freq=0.0,
                     zbd_power_dbm=0.0, zbd_voltage=0.0):
        self.data = data
        self.tone = tone
        self.fftbin = fftbin
        self.nsamp = nsamp
        self.nfft = nfft
        self.wavenorm = wavenorm
        self.dt = 1/(fs/nfft)
        self.fs = fs
        self.t0 = t0
        self.sweep_index = sweep_index
        self.mmw_source_freq = mmw_source_freq
        self.mmw_source_modulation_freq = mmw_source_modulation_freq
        self.zbd_voltage = zbd_voltage
        self.zbd_power_dbm = zbd_power_dbm
        self._mean = None
        self._std = None
        self._lpf_data = None
        
    def mean(self):
        if self._mean is None:
            if self._lpf_data is None:
                self._lpf_data = fftfilt.fftfilt(lpf,self.data)[len(lpf):]*self.wavenorm
            self._mean = self._lpf_data.mean(0,dtype='complex')
        return self._mean
    def std(self):
        if self._std is None:
            if self._lpf_data is None:
                self._lpf_data = fftfilt.fftfilt(lpf,self.data)[len(lpf):]*self.wavenorm
            self._std = self._lpf_data.std(0)
        return self._std
        
class SweepData():
    def __init__(self,sweep_id=1):
        self.sweep_id = sweep_id
        self.blocks = []
        self._freqs = []
        self._sweep_indexes = []
    def add_block(self,block):
        f = (block.fs*block.tone)/block.nsamp
        idx = bisect.bisect(self._freqs, f)
        self._freqs.insert(idx,f)
        self._sweep_indexes.insert(idx,block.sweep_index)
        self.blocks.insert(idx,block)
        
    def select_index(self,index):
        msk = self.sweep_indexes == index
        freqs = self.freqs[msk]
        data = self.data[msk]
        errors = self.errors[msk]
        return freqs,data,errors

    def select_by_freq(self,freq):
        didx = np.argmin(abs(freq-self.freqs))
        idx = self._sweep_indexes[didx]
        return self.select_index(idx)
    
    @property
    def freqs(self):
        return np.array(self._freqs)
    @property
    def data(self):
        return np.array([x.mean() for x in self.blocks])
    @property
    def sweep_indexes(self):
        return np.array(self._sweep_indexes)
    @property
    def errors(self):
        return np.array([x.std() for x in self.blocks])
