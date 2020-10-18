import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import collections
import datetime
import re

metrics = {'received': 'Received packets at root', \
           'arrivedToGenerate': 'Total number of packets that were allowed to be generated', \
           'generated': 'Total number of packets generated', \
           'latency': 'Average latency per network', \
           'inQueue': 'Total number of packets in queue', \
           'queueDropped': 'Total number of packets dropped by queue problems', \
           'macDropped': 'Total number of packets dropped by MAC problems', \
           'hops': 'TOTAL number of hops taken by all data'
           }

# modes = ['same-axis', 'diff-axis']

def validate(exp_dir):
    """ Validate the experiment to be really successful."""
    error_log = '%s/error.log' % exp_dir  # should be empty
    runSim_log = '%s/runSim.log' % exp_dir  # should be there, should not be empty
    output_data = '%s/output_cpu0.dat' % exp_dir  # should be there, should not be empty
    id_pattern = '*.id.txt'  # should only be one file with this id_pattern

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
                return int(line.split('=')[1].strip())  # num motes


def get_set_rgx(experiments, rgx=''):
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
    listFiles = os.popen(cmd).read().split("\n")[
                :-1]  # for some reason, there is a trailing whitespace in the list, remove it
    rgx = '[_\/]+%s_([A-Za-z0-9]+)_' % search_parameter
    candidates = get_set_rgx(listFiles, rgx)
    return candidates


def parseresults(dataDir, parameter, data):
    print data
    cmd = "find {0} -ipath *{1}*/output_cpu0.dat".format(dataDir, parameter)
    listFiles = os.popen(cmd).read().split("\n")[:-1]  # for some reason, there is a trailing whitespace in the list, remove it
    print "Processing %d file(s) in %s." % (len(listFiles), str(dataDir))
    for datafile in listFiles:
        validate(os.path.dirname(datafile))

        pktReceived = {}
        pktArrivedToGen = {}
        pktGen = {}
        pktLatencies = {}
        pktInQueue = {}
        pktDropsMac = {}
        pktDropsQueue = {}
        hopcount = {}

        # get all the data
        with open(datafile, 'r') as inF:
            for line in inF:
                if '#PktReceived' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktReceived[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktReceived[int(mote.split("@")[0])] = None
                if '#PktArrivedToGen' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktArrivedToGen[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktArrivedToGen[int(mote.split("@")[0])] = None
                if '#PktGen' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktGen[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktGen[int(mote.split("@")[0])] = None
                if '#PktLatencies' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktLatencies[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktLatencies[int(mote.split("@")[0])] = None
                if '#PktInQueue' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktInQueue[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktInQueue[int(mote.split("@")[0])] = None
                if '#PktDropsMac' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktDropsMac[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktDropsMac[int(mote.split("@")[0])] = None
                if '#PktDropsQueue' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktDropsQueue[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktDropsQueue[int(mote.split("@")[0])] = None
                if '#hopcount' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        hopcount[int(mote.split("@")[0])] = int(mote.split("@")[1])

        if datafile not in data:
            data[datafile] = []  # make a list of (id, hopcount, consumption) per node per datafile

        numMotes = getNrMotes(datafile)

        # summarize the data
        for mote in range(0, numMotes):
            data[datafile].append({'mote': mote, \
                                   'pktReceived': pktReceived[mote], \
                                   'pktArrivedToGen': pktArrivedToGen[mote], \
                                   'pktGen': pktGen[mote], \
                                   'pktLatencies': pktLatencies[mote], \
                                   'pktInQueue': pktInQueue[mote], \
                                   'pktDropsQueue': pktDropsQueue[mote], \
                                   'pktDropsMac': pktDropsMac[mote], \
                                   'hopcount': hopcount[mote]})

        if data[datafile][0]['mote'] != 0:  # should be root node
            assert False

    cycles = float(list(detectInName('cycles', listFiles[0]))[0])
    for df in listFiles:
        c = float(list(detectInName('cycles', df))[0])
        if c != cycles:
            print '%.4f vs %.4f' % (c, cycles)
            raise 'Different cycles!'

    return cycles, listFiles

def calculateReceived(data):
    outputDictionary = {}
    for iteration in data:
        nrReceived = 0
        for moteList in data[iteration]:
            if moteList['mote'] == 0:
                nrReceived += moteList['pktReceived']
                break
        outputDictionary[iteration] = nrReceived

    return outputDictionary

def calculateArrivedToGenerate(data):
    outputDictionary = {}
    for iteration in data:
        nrGenerated = 0
        for moteList in data[iteration]:
            if moteList['mote'] != 0:
                nrGenerated += moteList['pktArrivedToGen']
        outputDictionary[iteration] = nrGenerated

    return outputDictionary

def calculateGenerate(data):
    outputDictionary = {}
    for iteration in data:
        nrGenerated = 0
        for moteList in data[iteration]:
            if moteList['mote'] != 0:
                nrGenerated += moteList['pktGen']
        outputDictionary[iteration] = nrGenerated

    return outputDictionary

def calculateInQueue(data):
    outputDictionary = {}
    for iteration in data:
        inQueue = 0
        for moteList in data[iteration]:
            if moteList['pktInQueue'] is not None:
                inQueue += moteList['pktInQueue']
        outputDictionary[iteration] = inQueue

    return outputDictionary

def calculateDropsQueue(data):
    outputDictionary = {}
    for iteration in data:
        dropsQueue = 0
        for moteList in data[iteration]:
            if moteList['pktDropsQueue'] is not None:
                dropsQueue += moteList['pktDropsQueue']
        outputDictionary[iteration] = dropsQueue

    return outputDictionary

def calculateDropsMac(data):
    outputDictionary = {}
    for iteration in data:
        dropsMac = 0
        for moteList in data[iteration]:
            if moteList['pktDropsMac'] is not None:
                dropsMac += moteList['pktDropsMac']
        outputDictionary[iteration] = dropsMac

    return outputDictionary

def calculateLatency(data):
    outputDictionary = {}
    for iteration in data:
        latencies = []
        for moteList in data[iteration]:
            if moteList['pktLatencies'] is not None:
                latencies.append(moteList['pktLatencies'])
        outputDictionary[iteration] = np.mean(latencies)

    return outputDictionary

def calculateHops(data):
    outputDictionary = {}
    for iteration in data:
        hopcount = 0
        for moteList in data[iteration]:
            if moteList['hopcount'] is not None:
                hopcount += moteList['hopcount']
        outputDictionary[iteration] = hopcount

    return outputDictionary

def plotIt(xData, data, metric, outputDirectory):
    # the experiment iteration files
    xData = sorted([str(list(detectInName('seed', x))[0]) for x in xData])
    fig, ax = plt.subplots()
    colors = ['red', 'green', 'blue', 'orange', 'yellow', 'black']
    colorIndex = 0
    for experiment in data:
        # should also contain the experiment iteration files in the same order
        yKeys = sorted([str(list(detectInName('seed', key))[0]) for (key, value) in sorted(data[experiment].items())])
        if xData != yKeys: # so, this should be the same
            print xData
            print yKeys
            raise Exception('Experiment iterations do not match up.')

        yData = [value for (key, value) in sorted(data[experiment].items())]
        ax.plot(xData, yData, label=experiment, color=colors[colorIndex])
        ax.axhline(y=np.mean(yData), color=colors[colorIndex], linestyle='-', alpha=0.5)
        colorIndex += 1

    ax.tick_params(axis='x', rotation=90)
    ax.set(xlabel='Experiment iterations (seed numbers)', ylabel=metric)
    ax.legend()

    fig.tight_layout()
    name = '{outputDirectory}/comparison-{metric}.pdf'.format(outputDirectory=outputDirectory, metric=metric)
    plt.savefig(name)
    plt.close()

if __name__ == '__main__':
    # try:
    data = collections.OrderedDict()

    dataDirectory = str(sys.argv[1])

    outputDirectory = 'plots-comparison-experiments-{timestamp}'.format(timestamp=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    # make the output directory
    os.makedirs(outputDirectory)

    # initialize the data holders
    calculatedData = {}
    calculatedData['cycles'] = {}
    calculatedData['iterations'] = {}
    calculatedData['received'] = {}
    calculatedData['arrivedToGenerate'] = {}
    calculatedData['generated'] = {}
    calculatedData['latency'] = {}
    calculatedData['inQueue'] = {}
    calculatedData['queueDropped'] = {}
    calculatedData['macDropped'] = {}
    calculatedData['hops'] = {}

    for ix in range(2, len(sys.argv)):
        # prepare the data
        data[sys.argv[ix]] = {}
        calculatedData['cycles'][sys.argv[ix]], calculatedData['iterations'][sys.argv[ix]] = parseresults(dataDirectory, sys.argv[ix], data[sys.argv[ix]])
        calculatedData['received'][sys.argv[ix]] = calculateReceived(data[sys.argv[ix]])
        calculatedData['arrivedToGenerate'][sys.argv[ix]] = calculateArrivedToGenerate(data[sys.argv[ix]])
        calculatedData['generated'][sys.argv[ix]] = calculateGenerate(data[sys.argv[ix]])
        calculatedData['latency'][sys.argv[ix]] = calculateLatency(data[sys.argv[ix]])
        calculatedData['inQueue'][sys.argv[ix]] = calculateInQueue(data[sys.argv[ix]])
        calculatedData['queueDropped'][sys.argv[ix]] = calculateDropsQueue(data[sys.argv[ix]])
        calculatedData['macDropped'][sys.argv[ix]] = calculateDropsMac(data[sys.argv[ix]])
        calculatedData['hops'][sys.argv[ix]] = calculateHops(data[sys.argv[ix]])

    for metric in metrics.keys():
        # plot it
        # for the iterations file, take the iteration files of the first experiment
        plotIt(calculatedData['iterations'][sys.argv[2]], calculatedData[metric], metric=metric, outputDirectory=outputDirectory)

    # except Exception as exception:
    #     print exception
