import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import collections
import datetime
import re

translate = {'received': 'Received packets at root', 'arrivedToGenerate': 'Total number of packet generated', \
             'latency': 'Average latency per network'}

modes = ['same-axis', 'diff-axis']

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
        pktLatencies = {}

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
                if '#PktLatencies' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktLatencies[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktLatencies[int(mote.split("@")[0])] = None

        if datafile not in data:
            data[datafile] = []  # make a list of (id, hopcount, consumption) per node per datafile

        numMotes = getNrMotes(datafile)

        # summarize the data
        for mote in range(0, numMotes):
            data[datafile].append({'mote': mote, 'pktReceived': pktReceived[mote], 'pktArrivedToGen': pktArrivedToGen[mote], 'pktLatencies': pktLatencies[mote]})

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

def calculateLatency(data):
    outputDictionary = {}
    for iteration in data:
        latencies = []
        for moteList in data[iteration]:
            if moteList['pktLatencies'] is not None:
                latencies.append(moteList['pktLatencies'])
        outputDictionary[iteration] = np.mean(latencies)

    return outputDictionary

def plotIt(xData, metricOneData, metricTwoData, metricOneName, metricTwoName, outputDirectory, axesMode):

    xData = sorted(xData)
    metricOneKeys = [key for (key, value) in sorted(metricOneData.items())]
    metricOneData = [value for (key, value) in sorted(metricOneData.items())]
    metricTwoKeys = [key for (key, value) in sorted(metricTwoData.items())]
    metricTwoData = [value for (key, value) in sorted(metricTwoData.items())]

    if axesMode == 'same-axis':
        maxValue = max(metricOneData)
        if maxValue < max(metricTwoData):
            maxValue = metricTwoData

    if xData != metricOneKeys != metricTwoKeys:
        raise Exception('Experiment iterations do not match up.')

    xData = [str(list(detectInName('seed', x))[0]) for x in xData]

    fig, ax1 = plt.subplots()
    ax1.tick_params(axis='x', rotation=90)
    ax1.set_xlabel('Experiment iteration (seed number)')
    ax1.set_ylabel(metricOneName, color='red')
    ax1.plot(xData, metricOneData, color='red')
    #

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    ax2.set_ylabel(metricTwoName, color='blue')  # we already handled the x-label with ax1
    ax2.plot(xData, metricTwoData, color='blue')
    # ax2.tick_params(axis='y', labelcolor='blue')

    if axesMode == 'same-axis':
        ax1.set_ylim(0, maxValue)
        ax2.set_ylim(0, maxValue)

    fig.tight_layout()
    name = '{outputDirectory}/comparison-{metricOne}-{metricTwo}.pdf'.format(outputDirectory=outputDirectory, metricOne=metricOneName, metricTwo=metricTwoName)
    plt.savefig(name)
    plt.close()

if __name__ == '__main__':
    try:
        data = collections.OrderedDict()

        dataDirectory = str(sys.argv[1])
        experimentName = str(sys.argv[2])
        axesMode = str(sys.argv[3])
        metricOne = str(sys.argv[4])
        metricTwo = str(sys.argv[5])

        if axesMode not in modes:
            raise Exception('Wrong mode selected!')
        if metricOne not in translate.keys():
            raise Exception('Metric 1 is unknown.')
        if metricTwo not in translate.keys():
            raise Exception('Metric 1 is unknown.')

        outputDirectory = 'plots-{expName}-{metricOne}-{metricTwo}-{mode}-{timestamp}'.format(expName=experimentName,
                                                                                              metricOne=metricOne,
                                                                                              metricTwo=metricTwo,
                                                                                              mode=axesMode,
                                                                                              timestamp=datetime.datetime.now().strftime(
                                                                                                  '%Y-%m-%d-%H-%M-%S'))
        # make the output directory
        os.makedirs(outputDirectory)

        # prepare the data
        data[experimentName] = {}
        calculatedData = {}
        calculatedData['cycles'], calculatedData['iterations'] = parseresults(dataDirectory, experimentName, data[experimentName])
        calculatedData['received'] = calculateReceived(data[experimentName])
        calculatedData['arrivedToGenerate'] = calculateArrivedToGenerate(data[experimentName])
        calculatedData['latency'] = calculateLatency(data[experimentName])

        plotIt(calculatedData['iterations'], calculatedData[metricOne], calculatedData[metricTwo], metricOneName=metricOne, metricTwoName=metricTwo, axesMode=axesMode, outputDirectory=outputDirectory)

    except Exception as exception:
        print exception
