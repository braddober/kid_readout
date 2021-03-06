import numpy as np
import netCDF4
import types
import bisect
import warnings
from collections import OrderedDict
from kid_readout.utils.roach_utils import ntone_power_correction


class TimestreamGroup(object):
    def __init__(self,ncgroup):
        keys = ncgroup.variables.keys()
        keys.remove('data')
        keys.remove('dt')
        keys.remove('fs')
        keys.remove('tone')
        keys.remove('nsamp')
        for key in keys:
            setattr(self,key,ncgroup.variables[key][:])
        required_keys = ['wavenorm', 'sweep_index']
        for key in required_keys:
            if key not in keys:
                setattr(self,key,None)
#        self.epoch = ncgroup.variables['epoch'][:]
        self.tonebin = ncgroup.variables['tone'][:]
        self.tone_nsamp = ncgroup.variables['nsamp'][:]
#        self.fftbin = ncgroup.variables['fftbin'][:]
#        self.nfft = ncgroup.variables['nfft'][:]
#        self.dt = ncgroup.variables['dt'][:] # the dt property is actually misleading at this point, so leaving it out
        self.adc_sampling_freq = ncgroup.variables['fs'][:]
        self.measurement_freq = self.adc_sampling_freq*self.tonebin/(1.0*self.tone_nsamp)
        self.sample_rate = self.adc_sampling_freq*1e6/(2*self.nfft)
#        if ncgroup.variables.has_key('wavenorm'):
#            self.wavenorm = ncgroup.variables['wavenorm'][:]
#        else:
#            self.wavenorm = None
#        if ncgroup.variables.has_key('sweep_index'):
#            self.sweep_index = ncgroup.variables['sweep_index'][:]
#        else:
#            self.sweep_index = None
            
        self._data = ncgroup.variables['data']
        self.num_data_samples = self._data.shape[1]
        self.data_len_seconds = self.num_data_samples/self.sample_rate
        self._datacache = None
        
    @property
    def data(self):
        if self._datacache is None:
            if self.wavenorm is None:
                wavenorm = 1.0
                warnings.warn("wave normalization not found, time series will not match sweep")
            else:
                wavenorm = self.wavenorm[:,None]
            self._datacache = self._data[:].view(self._data.datatype.name)*wavenorm
        return self._datacache
    
    def get_data_index(self,index):
        if self._datacache is None:
            if self.wavenorm is None:
                wavenorm = 1.0
                warnings.warn("wave normalization not found, time series will not match sweep")
            else:
                wavenorm = self.wavenorm[index]            
            return self._data[index].view(self._data.datatype.name)*wavenorm
        else:
            return self._datacache[index]
        
class SweepGroup(object):
    def __init__(self,ncgroup):
        self.frequency = ncgroup.variables['frequency'][:]
        self.s21 = ncgroup.variables['s21'][:].view(ncgroup.variables['s21'].datatype.name)
        self.index = ncgroup.variables['index'][:]
        self.timestream_group = TimestreamGroup(ncgroup.groups['datablocks'])
        self.start_epoch = self.timestream_group.epoch.min()
        self.end_epoch = self.timestream_group.epoch.max()
    
    @property
    def errors(self):
        if self.timestream_group.wavenorm is None:
            wavenorm = 1
        else:
            wavenorm = self.timestream_group.wavenorm[0]
        real_err = self.timestream_group.data.real.std(1)
        imag_err = self.timestream_group.data.imag.std(1)
        nsamp = self.timestream_group.data.shape[1]
        return (real_err + 1j*imag_err)/np.sqrt(nsamp)

    def select_by_index(self,index):
        mask = self.index == index
        freq,s21,errors = self.frequency[mask], self.s21[mask], self.errors[mask]
        order = freq.argsort()
        return freq[order], s21[order], errors[order]
    
    def select_by_frequency(self,freq):
        findex = np.argmin(abs(self.frequency - freq))
        index = self.index[findex]
        return self.select_by_index(index)
    
class ReadoutNetCDF(object):
    def __init__(self,filename):
        self.filename = filename
        self.ncroot = netCDF4.Dataset(filename,mode='r')
        hwgroup = self.ncroot.groups['hw_state']
        self.hardware_state_epoch = hwgroup.variables['epoch'][:]
        self.adc_atten = hwgroup.variables['adc_atten'][:]
        self.dac_atten = hwgroup.variables['dac_atten'][:]
        if hwgroup.variables.has_key('ntones'):
            self.num_tones = hwgroup.variables['ntones'][:]
        else:
            self.num_tones = None
        try:
            self.gitinfo = self.ncroot.gitinfo
        except AttributeError:
            self.gitinfo = ''
            
        self.sweeps_dict = OrderedDict()
        self.timestreams_dict = OrderedDict()
        for name,group in self.ncroot.groups['sweeps'].groups.items():
            self.sweeps_dict[name] = SweepGroup(group)
            self.__setattr__(name,self.sweeps_dict[name])
        self.sweeps = self.sweeps_dict.values()
        for name,group in self.ncroot.groups['timestreams'].groups.items():
            self.timestreams_dict[name] = TimestreamGroup(group)
            self.__setattr__(name,self.timestreams_dict[name])
        self.timestreams = self.timestreams_dict.values()
    def close(self):
        self.ncroot.close()
        
    def get_effective_dac_atten_at(self,epoch):
        index = bisect.bisect_left(self.hardware_state_epoch, epoch) # find the index of the epoch immediately preceding the desired epoch
        dac_atten = self.dac_atten[index]
        if self.num_tones is not None:
            ntones = self.num_tones[index]
        else:
            ntones = 1
            warnings.warn("ntones parameter not found in data file %s, assuming 1. The effective power level may be wrong" % self.filename)
        total = dac_atten + ntone_power_correction(ntones)
        return dac_atten, total
    