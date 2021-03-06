import time
import datetime
import numpy as np
import os
import glob

_timecache = []
_tempcache = []
_lastupdate = -1

def get_all_temperature_data(logdir = '/home/heather/SRS'):
    logs = glob.glob(os.path.join(logdir,'201*.txt'))
    logs.sort()
    times = []
    temps = []
    for log in logs:
        t0,temp0 = parse_srs_log(log)
        if len(t0) == 0:
            t0,temp0 = parse_srs_log(log,sensor=1)
        times = times + t0.tolist()
        temps = temps + temp0.tolist()
    return times,temps
        
def get_temperature_at(epoch):
    global _timecache, _tempcache, _lastupdate
    if time.time() - _lastupdate > 20*60:
        _timecache, _tempcache = get_all_temperature_data()
        _lastupdate = time.time()
        print "get_temperature_at: updated cache"
    if len(_tempcache) == 0:
        return 0
    temp = np.interp(epoch,_timecache,_tempcache)
    return temp

def convtime(tstr):
    return time.mktime(time.strptime(tstr,'%Y%m%d-%H%M%S'))
def get_load_log(fname):
    try:
        tdata = np.genfromtxt(fname,delimiter=',',converters={0:convtime},skiprows=1,invalid_raise=False)
        dt = [datetime.datetime.fromtimestamp(x) for x in tdata[:,0]]
    except:
        from pandas import read_table
        df = read_table(fname,sep='[ ,]+',skiprows=1,converters={0:convtime},header=None)
        dt = [datetime.datetime.fromtimestamp(x) for x in df[0]]
        tdata = np.zeros((len(df),15))
        tdata[:,0] = np.array(df[0])
        tdata[:,1] = np.array(df[1])
        tdata[:,2] = np.array(df[2])
        tdata[:,11] = np.array(df[9])
        tdata[:,12] = np.array(df[10])
        tdata[:,13] = np.array(df[11])
        tdata[:,14] = np.array(df[12])


#    if tdata[0] is np.nan: # special case for earlier files, at least 2014-02
#        tdata = np.genfromtxt(fname,delimiter=' ',converters={3:convtime},skiprows=1,invalid_raise=False)
#        dt = [datetime.datetime.fromtimestamp(x) for x in tdata[:,3]]
#    else:

    return dt,tdata

def parse_srs_log(fname,sensor=2):
    """
    Parse log file created by Heather's SRS logger
    *fname* : file name of log
    *sensor* : which sensor to extract (right now 2 corresponds to the package thermometer)
    returns numpy arrays of unix times and the temperature values
    """
    fh = open(fname,'r')
    lines = fh.readlines()
    fh.close()
    temps = []
    times = []
    for line in lines:
        parts = line.split(' ')
        try:
            if len(parts) == 15:
                try:
                    times.append(time.mktime(time.strptime(parts[0].strip(),'%Y%m%d-%H%M%S,')))
                except:
                    times.append(time.mktime(time.strptime(parts[0].strip(),'%Y%m%d-%H%M%S')))
                temps.append(float(parts[11].strip().strip(',')))
                continue
            if len(parts) >9:
                times.append(time.mktime(time.strptime(parts[0].strip(),'%Y%m%d-%H%M%S')))
                temps.append(float(parts[9]))
                continue
            if int(parts[0]) != sensor:
                continue
            if len(parts) < 4:
                continue
            temps.append(float(parts[2]))
            times.append(time.mktime(time.strptime(parts[3].strip(),'%Y%m%d-%H%M%S')))
        except ValueError,e:
            pass
            #print "failed to parse",repr(line),"skipping",str(e)
    return np.array(times),np.array(temps)


class SRSLogFile(object):
    """
    Usage example: log_file[1].R returns an array of resistances for
    channel 1.
    """

    class Channel(object):

        def __init__(self, time, R, T):
            self.time = time
            self.R = R
            self.T = T

    def __init__(self, filename):
        self._channels = {}
        channels, resistances, temperatures, times = np.loadtxt(filename,
                                                                unpack=True,
                                                                converters={3: self.convert_timestamp})
        for channel in np.unique(channels.astype('int')):
            mask = (channels == channel)
            self._channels[channel] = self.Channel(times[mask],
                                                   resistances[mask],
                                                   temperatures[mask])

    def __getitem__(self, item):
        return self._channels[item]

    def convert_timestamp(self, timestamp):
        return time.mktime(time.strptime(timestamp.strip(),'%Y%m%d-%H%M%S'))
