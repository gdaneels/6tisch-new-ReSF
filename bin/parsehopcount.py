import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import collections
import datetime
import re
import math

# ALERT! THIS LAST _ IS VERY IMPORTANT FOR FILTERING THE CORRECT EXPERIMENTS

fileTranslate = {'m_1_p_10_': 'numMotes = 1,\nperiod = 10', \
                 'm_1_p_30_': 'numMotes = 1,\nperiod = 30', \
                 'm_1_p_60_': 'numMotes = 1,\nperiod = 60', \
                 'm_1_p_300_': 'numMotes = 1,\nperiod = 300', \
                 'm_1_p_600_': 'numMotes = 1,\nperiod = 600', \
                 'm_10_p_10_': 'numMotes = 10,\nperiod = 10', \
                 'm_10_p_30_': 'numMotes = 10,\nperiod = 30', \
                 'm_10_p_60_': 'numMotes = 10,\nperiod = 60', \
                 'm_10_p_300_': 'numMotes = 10,\nperiod = 300', \
                 'm_10_p_600_': 'numMotes = 10,\nperiod = 600', \
                 'm_50_p_10_': 'numMotes = 50,\nperiod = 10', \
                 'm_50_p_30_': 'numMotes = 50,\nperiod = 30', \
                 'm_50_p_60_': 'numMotes = 50,\nperiod = 60', \
                 'm_50_p_300_': 'numMotes = 50,\nperiod = 300', \
                 'm_50_p_600_': 'numMotes = 50,\nperiod = 600', \
                 'm_100_p_10_': 'numMotes = 100,\nperiod = 10', \
                 'm_100_p_30_': 'numMotes = 100,\nperiod = 30', \
                 'm_100_p_60_': 'numMotes = 100,\nperiod = 60', \
                 'm_100_p_300_': 'numMotes = 100,\nperiod = 300', \
                 'm_100_p_600_': 'numMotes = 100,\nperiod = 600'
                 }
fileTranslateWrite = {'m_1_p_10_': 'numMotes = 1, period = 10', \
                 'm_1_p_30_': 'numMotes = 1, period = 30', \
                 'm_1_p_60_': 'numMotes = 1, period = 60', \
                 'm_1_p_300_': 'numMotes = 1, period = 300', \
                 'm_1_p_600_': 'numMotes = 1, period = 600', \
                 'm_10_p_10_': 'numMotes = 10, period = 10', \
                 'm_10_p_30_': 'numMotes = 10, period = 30', \
                 'm_10_p_60_': 'numMotes = 10, period = 60', \
                 'm_10_p_300_': 'numMotes = 10, period = 300', \
                 'm_10_p_600_': 'numMotes = 10, period = 600', \
                 'm_50_p_10_': 'numMotes = 50, period = 10', \
                 'm_50_p_30_': 'numMotes = 50, period = 30', \
                 'm_50_p_60_': 'numMotes = 50, period = 60', \
                 'm_50_p_300_': 'numMotes = 50, period = 300', \
                 'm_50_p_600_': 'numMotes = 50, period = 600', \
                 'm_100_p_10_': 'numMotes = 100, period = 10', \
                 'm_100_p_30_': 'numMotes = 100, period = 30', \
                 'm_100_p_60_': 'numMotes = 100, period = 60', \
                 'm_100_p_300_': 'numMotes = 100, period = 300', \
                 'm_100_p_600_': 'numMotes = 100, period = 600'
                }
translate = {'lifetime_250mAh': 'Lifetime for 250 mAh battery (days)', \
             'lifetime_500mAh': 'Lifetime for 500 mAh battery (days)', \
             'lifetime_1000mAh': 'Lifetime for 1000 mAh battery (days)', \
             'lifetime_1500mAh': 'Lifetime for 1500 mAh battery (days)', \
             'lifetime_2000mAh': 'Lifetime for 2000 mAh battery (days)', \
             'kbitsPerJoule': 'kbit / Joule (kbit/J)', 'sixtopTxAddReq': '6P ADD Requests', 'received': 'Received packets at root', 'DAOMessaging': 'DAO Messaging'}

metrics = ['bitperjoule', 'lifetime']
colors = ['red', 'green', 'blue', 'orange', 'yellow', 'black']

def validate(exp_dir):
    """ Validate the experiment to be really successful."""
    error_log = '%s/error.log' % exp_dir # should be empty
    runSim_log = '%s/runSim.log' % exp_dir # should be there, should not be empty
    output_data = '%s/output_cpu0.dat' % exp_dir # should be there, should not be empty
    id_pattern = '*.id.txt' # should only be one file with this id_pattern

    import os
    if not os.path.exists(error_log) or os.path.getsize(error_log) > 0:
        print exp_dir
        raise 'Error log not there or not zero.'
    if not os.path.exists(runSim_log) or os.path.getsize(runSim_log) == 0:
        print exp_dir
        raise 'No runSim log or runSim log is empty.'
    if not os.path.exists(output_data) or os.path.getsize(output_data) == 0:
        print exp_dir
        raise 'No output data or output data is zero.'
    import fnmatch
    count_workers = fnmatch.filter(os.listdir(exp_dir), id_pattern)
    if len(count_workers) > 1:
        print exp_dir
        raise 'Multiple workers worked on this.'

def getNrMotes(datafile):
    with open(datafile) as f:
        for line in f:
            if '## numMotes =' in line:
                return int(line.split('=')[1].strip()) # num motes

def get_set_rgx(experiments, rgx = ''):
    candidates = set()
    for exp in experiments:
        print exp
        regex_result = re.search(rgx, exp, re.IGNORECASE)
        if regex_result is not None:
            candidates.add(regex_result.group(1))
        else:
            raise 'No %s indicator in experiment dir.' % rgx
    return candidates

def detectInName(search_parameter, exp_dir):
    cmd = "find {0} -ipath *{1}*/output_cpu0.dat".format(exp_dir, search_parameter)
    listFiles = os.popen(cmd).read().split("\n")[:-1] # for some reason, there is a trailing whitespace in the list, remove it
    rgx = '[_\/]+%s_([A-Za-z0-9]+)_' % search_parameter
    candidates = get_set_rgx(listFiles, rgx)
    return candidates

def parseresults(dataDir, parameter, data):
    cmd = "find {0} -ipath *{1}*/output_cpu0.dat".format(dataDir, parameter)
    listFiles = os.popen(cmd).read().split("\n")[:-1] # for some reason, there is a trailing whitespace in the list, remove it
    print "Processing %d file(s) in %s." % (len(listFiles), str(dataDir))
    for datafile in listFiles:
        validate(os.path.dirname(datafile))

        prefParent = {}

        # get all the data
        with open(datafile, 'r') as inF:
            for line in inF:
                if '#prefParent' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if int(mote.split("@")[0]) != 0:
                            prefParent[int(mote.split("@")[0])] = float(mote.split("@")[1])
                        else:
                            prefParent[int(mote.split("@")[0])] = -1
                    # print 'Got charge.'

        if datafile not in data:
            data[datafile] = [] # make a list of (id, hopcount, consumption) per node per datafile

        numMotes = getNrMotes(datafile)

        # summarize the data
        for mote in range(0, numMotes):
            data[datafile].append({'mote': mote, 'prefParent': prefParent[mote]})

        if data[datafile][0]['mote'] != 0: # should be root node
            assert False
        # print datafile

    # period = float(list(detectInName('p', listFiles[0]))[0])
    cycles = float(list(detectInName('cycles', listFiles[0]))[0])
    for df in listFiles:
        # p = float(list(detectInName('p', df))[0])
        c = float(list(detectInName('cycles', df))[0])
        if c != cycles:
            # print '%.4f vs %.4f' % (p, period)
            print '%.4f vs %.4f' % (c, cycles)
            raise 'Different cycles!'

    return cycles

def checkPrefParent(data):
    # get all the scheduling functions
    sfs = data.keys()
    # get all the experiments
    exps = data[sfs[0]].keys()

    expsdiff = set()

    for exp in exps:
        listOfPreferredParents = []
        for sf in sfs:
            exp_tmp = exp.replace(sfs[0], sf)
            # get all the preferred parents in this experiment, for this SF
            for moteResults in data[sf][exp_tmp]:
                motePrefParent = '%d_%d' % (moteResults['mote'], moteResults['prefParent'])
                if sf != sfs[0]: # if we know we are handling the first SF, than we need to fill in that list first
                    if motePrefParent not in listOfPreferredParents:
                        print 'The experiment file:'
                        print exp
                        raise 'Found a experiment with different preferred parents!'
                        expsdiff.add(exp)
                else:
                    listOfPreferredParents.append(motePrefParent)

    print expsdiff
    print len(expsdiff)

def writeData(metric, data):
    print translate[metric]
    for exp, dat in sorted(data.items(), key=lambda x: x[0]):
        if exp in fileTranslateWrite:
            print '{exp}: {data}'.format(exp=fileTranslateWrite[exp],data=np.mean(dat))
        else:
            print '{exp}: {data}'.format(exp=exp, data=np.mean(dat))

def getMetricY(metric):
    if metric == 'all':
        return metrics
    else:
        return [metric]

if __name__ == '__main__':
    data = collections.OrderedDict()

    # make the output directory
    outputDir = 'plots-%s' % datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    try:
        os.makedirs(outputDir)
    except OSError:
        if not os.path.isdir(outputDir):
            raise

    # data directory
    dataDir = str(sys.argv[1])

    prefParent = collections.OrderedDict()
    for ix in range(2, len(sys.argv)):
        data[sys.argv[ix]] = {}
        cycles = parseresults(dataDir, sys.argv[ix], data[sys.argv[ix]])

    # check if the pref parent check or not
    checkPrefParent(data)