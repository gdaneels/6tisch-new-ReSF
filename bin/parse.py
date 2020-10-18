import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import collections
import datetime
import re
import math

# TODO SHOULD ADD A LAST _ FOR CORRECT FILTERING!
# ALERT! THIS LAST _ IS VERY IMPORTANT FOR FILTERING THE CORRECT EXPERIMENTS

fileTranslate = {'bp_1_pp_1_mc_1': 'BE_max = 1,\nmsfCell = 1', 'bp_2_pp_1_mc_1': 'BE_max = 2,\nmsfCell = 1', 'bp_3_pp_1_mc_1': 'BE_max = 3,\nmsfCell = 1', 'bp_4_pp_1_mc_1': 'BE_max = 4,\nmsfCell = 1', \
                  'bp_1_pp_1_mc_2': 'BE_max = 1,\nmsfCell = 2', 'bp_2_pp_1_mc_2': 'BE_max = 2,\nmsfCell = 2', 'bp_3_pp_1_mc_2': 'BE_max = 3,\nmsfCell = 2', 'bp_4_pp_1_mc_2': 'BE_max = 4,\nmsfCell = 2', \
                  'bp_1_pp_1_mc_3': 'BE_max = 1,\nmsfCell = 3', 'bp_2_pp_1_mc_3': 'BE_max = 2,\nmsfCell = 3', 'bp_3_pp_1_mc_3': 'BE_max = 3,\nmsfCell = 3', 'bp_4_pp_1_mc_3': 'BE_max = 4,\nmsfCell = 3', \
                  'bp_1_pp_1_mc_5': 'BE_max = 1,\nmsfCell = 5', 'bp_2_pp_1_mc_5': 'BE_max = 2,\nmsfCell = 5', 'bp_3_pp_1_mc_5': 'BE_max = 3,\nmsfCell = 5', 'bp_4_pp_1_mc_5': 'BE_max = 4,\nmsfCell = 5'}
translate = {'hops' : 'Hop count', 'allChildren': 'Total number of children', 'lifetime': 'Lifetime (days)', 'charge': 'Charge', 'PktLatencies': 'Latency', 'PktDropsQueue': 'Dropped Packets', 'PktReceived': 'Received Packets'}
# mapping = {'hops' : 1, 'charge': 2, 'directChildren': 3, 'lifetime': 4, 'allChildren': 5, 'maxLevel': 6}
metrics = ['hopcount', 'aveChargePerCycle', 'PktArrivedToGen', 'PktNotGenerated', 'PktGen', 'PktReceived', 'PktInQueue',
           'PktDropsQueue', 'PktDropsMac', 'PktLatencies', 'pkPeriod', 'dedicatedCellConvergence', 'rplPrefParentChurn',
           'oldPrefParentRemoval', 'numberActualParentChanges', 'avgDurationParentChange', 'lifetime', 'allChildren',
           'maxLevel']
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

def get_set_rgx(experiments, rgx = ''):
    candidates = set()
    for exp in experiments:
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

def getNrMotes(datafile):
    with open(datafile) as f:
        for line in f:
            if '## numMotes =' in line:
                return int(line.split('=')[1].strip()) # num motes

def getLifetime(microCoulomb):
    mAh = float(microCoulomb) / 3600000.0 # to mAh
    numCycles = 2000.0 / mAh
    days = numCycles / 3600.0 / 24.0

    return days

def getChildrenPerNode(preferredParents):
    children = {}
    for mote, parent in preferredParents.iteritems():
        if parent != None:
            if parent not in children: # pref parent of root is None that's why I remove it
                children[parent] = [mote]
            else:
                children[parent].append(mote)
    return children

def getAllChildren(mote, childrenPerNode, firstCall=True):
    total = 0
    if not firstCall:
        total += 1
    if mote in childrenPerNode:
        for child in childrenPerNode[mote]:
            total += getAllChildren(child, childrenPerNode, firstCall=False)
    return total

def getMaxLevel(mote, childrenPerNode):
    maxlvl = 0
    if mote in childrenPerNode:
        for child in childrenPerNode[mote]:
            lvl = getMaxLevel(child, childrenPerNode)
            if lvl > maxlvl:
                maxlvl = lvl
    return maxlvl + 1

def parseresults(dataDir, parameter, data):
    cmd = "find {0} -ipath *{1}*/output_cpu0.dat".format(dataDir, parameter)
    listFiles = os.popen(cmd).read().split("\n")[:-1] # for some reason, there is a trailing whitespace in the list, remove it
    print "Processing %d file(s) in %s." % (len(listFiles), str(dataDir))
    for datafile in listFiles:
        validate(os.path.dirname(datafile))

        charge = {}
        hopcnt = {}
        children = {} # direct children
        prefParents = {} # preferredParents
        pktArrivedToGen = {}
        pktNotGenerated = {}
        pktGen = {}
        pktReceived = {}
        pktInQueue = {}
        pktLatencies = {}
        pktDropsMac = {}
        pktDropsQueue = {}
        pkPeriod = {}
        convergence = {}
        rplPrefParentChurn = {}
        oldPrefParentRemoval = {}
        numberActualParentChanges = {}
        avgDurationParentChange = {}

        # get all the data
        with open(datafile, 'r') as inF:
            for line in inF:
                if '#aveChargePerCycle' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        charge[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#hopcount' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        hopcnt[int(mote.split("@")[0])] = int(mote.split("@")[1])
                    # print 'Got hopcount.'
                if '#prefParent' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                prefParents[int(mote.split("@")[0])] = int(mote.split("@")[1])
                            else:
                                prefParents[int(mote.split("@")[0])] = None
                    # print 'Got pref parent.'
                if '#PktArrivedToGen' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktArrivedToGen[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktArrivedToGen[int(mote.split("@")[0])] = None
                if '#PktNotGenerated' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktNotGenerated[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktNotGenerated[int(mote.split("@")[0])] = None
                if '#PktGen' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktGen[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktGen[int(mote.split("@")[0])] = None
                if '#PktReceived' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktReceived[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktReceived[int(mote.split("@")[0])] = None
                if '#PktInQueue' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktInQueue[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktInQueue[int(mote.split("@")[0])] = None
                if '#PktDropsMac' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktDropsMac[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktDropsMac[int(mote.split("@")[0])] = None
                if '#PktDropsQueue' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktDropsQueue[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktDropsQueue[int(mote.split("@")[0])] = None
                if '#PktLatencies' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktLatencies[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktLatencies[int(mote.split("@")[0])] = None
                if '#pkPeriod' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pkPeriod[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pkPeriod[int(mote.split("@")[0])] = None
                if '#dedicatedCellConvergence' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                convergence[int(mote.split("@")[0])] = int(mote.split("@")[1])
                            else:
                                convergence[int(mote.split("@")[0])] = None
                if '#children' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        children[int(mote.split("@")[0])] = int(mote.split("@")[1])
                    # print 'Got children.'
                if '#rplPrefParentChurn' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        rplPrefParentChurn[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#oldPrefParentRemoval' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        oldPrefParentRemoval[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#numberActualParentChanges' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        numberActualParentChanges[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#avgDurationParentChange' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                avgDurationParentChange[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                avgDurationParentChange[int(mote.split("@")[0])] = None
                    # print 'Got children.'

        childrenPerNode = getChildrenPerNode(prefParents)
        # print childrenPerNode

        if datafile not in data:
            data[datafile] = [] # make a list of (id, hopcount, consumption) per node per datafile

        numMotes = getNrMotes(datafile)

        totalGenerated = 0
        # summarize the data
        for mote in range(0, numMotes):
            if mote == 0:
                pktLatencies[mote] = None
                convergence[mote] = None
            if mote not in pktLatencies:
                pktLatencies[mote] = None
            if pktGen[mote] != None and pktGen[mote] > 0:
                totalGenerated += pktGen[mote]
            # data[datafile].append((mote, hopcnt[mote], charge[mote], children[mote], getLifetime(charge[mote]), getAllChildren(mote, childrenPerNode, firstCall=True), getMaxLevel(mote, childrenPerNode)-1))
            data[datafile].append({'mote': mote, 'hopcount': hopcnt[mote],
                                   'aveChargePerCycle': charge[mote], 'PktGen': pktGen[mote],
                                   'PktArrivedToGen': pktArrivedToGen[mote], 'PktNotGenerated': pktNotGenerated[mote],
                                   'PktReceived': pktReceived[mote], 'PktInQueue': pktInQueue[mote],
                                   'PktDropsMac': pktDropsMac[mote], 'PktDropsQueue': pktDropsQueue[mote],
                                   'PktLatencies': pktLatencies[mote], 'pkPeriod': pkPeriod[mote],
                                   'dedicatedCellConvergence': convergence[mote], 'children': children[mote],
                                   'rplPrefParentChurn': rplPrefParentChurn[mote],
                                   'oldPrefParentRemoval': oldPrefParentRemoval[mote],
                                   'numberActualParentChanges': numberActualParentChanges[mote],
                                   'avgDurationParentChange': avgDurationParentChange[mote],
                                   'lifetime': getLifetime(charge[mote]),
                                   'allChildren': getAllChildren(mote, childrenPerNode, firstCall=True),
                                   'maxLevel': getMaxLevel(mote, childrenPerNode) - 1,
                                   'throughput': None,
                                   })

        # RECALCULATE THROUGHPUT
        if data[datafile][0]['mote'] != 0: # should be root node
            assert False
        print datafile
        # data[datafile][0]['throughput'] = float(data[datafile][0]['PktReceived']) / totalGenerated
        # print data[datafile]

def plotScatter(xMetric, yMetric, data):
    global mapping
    global colors
    plt.figure(figsize=(5,2.7))
    colorIx = 0
    errorfiles = []
    zerofiles = []
    for exp in data:
        x = []
        y = []
        for datafile in data[exp]:
            for mote in data[exp][datafile]:
                if mote[xMetric] != None and mote[yMetric] != None:
                    x.append(mote[xMetric])
                    y.append(mote[yMetric])
                else:
                    if mote['mote'] == 0: # is the root node
                        zerofiles.append(datafile)
                    elif yMetric != 'PktReceived' and yMetric != 'avgDurationParentChange': # for pktReceived it is normal that there are None values for the other nodes than the root
                        errorfiles.append(datafile)
        # print y
        avg = np.mean(y)
        std = np.std(y)
        lbl = exp
        if exp in fileTranslate:
            lbl = fileTranslate[exp]
        color = colors[colorIx]
        plt.fill_between((min(x),max(x)), avg-std, avg+std, alpha=0.05, color=color)
        plt.plot((min(x),max(x)), (avg,avg), linestyle="--", color=color, alpha=0.5)
        plt.scatter(x, y, s=10, color=color, label=lbl, alpha=0.5)
        colorIx += 1

    xMetric_translated, yMetric_translated = xMetric, yMetric
    if xMetric in translate:
        xMetric_translated = translate[xMetric]
    if yMetric in translate:
        yMetric_translated = translate[yMetric]
    plt.xlabel(xMetric_translated)
    plt.ylabel(yMetric_translated)
    # ticks = [tick for tick in plt.gca().get_yticks() if tick >=0]
    # plt.gca().set_yticks(ticks)
    # ticks = [tick for tick in plt.gca().get_xticks() if tick >=0]
    # plt.gca().set_xticks(ticks)
    plt.legend(loc='best',fontsize=8)
    plt.tight_layout()
    name = 'scatter-{0}-{1}-{2}.pdf'.format(xMetric, yMetric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.savefig(name)
    plt.close()

    print '%d error files.' % len(set(errorfiles))
    print '%d zero files.' % len(set(zerofiles))
    # print set(zerofiles)

def plotBars(yMetric, data, outputDir=''):
    global mapping
    global colors
    fig = plt.figure(figsize=(5,2.7))
    ax = fig.add_subplot(111)
    errorfiles = []
    zerofiles = []
    y_bars = []
    y_std = []
    y_xticks = []
    for exp in data:
        y = []
        for datafile in data[exp]:
            for mote in data[exp][datafile]:
                if mote[yMetric] != None:
                    y.append(mote[yMetric])
                else:
                    if mote['mote'] == 0: # is the root node
                        zerofiles.append(datafile)
                    elif yMetric != 'PktReceived' and yMetric != 'avgDurationParentChange': # for pktReceived it is normal that there are None values for the other nodes than the root
                        errorfiles.append(datafile)
        mean = np.mean(y)
        stderr = np.std(y) / math.sqrt(float(len(y)))
        if yMetric == 'PktLatencies':
            mean /= 100.0
            stderr /= 100.0
            print 'exp %s: mean %.4f std %.4f' % (exp, mean, stderr)
            # print errorfiles
        if yMetric == 'PktArrivedToGen':
            print 'PktArrivedToGen: exp %s: mean %.4f std %.4f' % (exp, mean, stderr)
        if yMetric == 'PktReceived':
            print 'PktReceived: exp %s: mean %.4f std %.4f' % (exp, mean, stderr)
        if yMetric == 'lifetime':
            print 'lifetime: exp %s: mean %.4f std %.4f' % (exp, mean, stderr)
            print errorfiles
        if yMetric == 'aveChargePerCycle':
            print 'aveChargePerCycle: exp %s: mean %.4f std %.4f' % (exp, mean, stderr)
            print errorfiles
        y_bars.append(mean)
        y_std.append(stderr)

        if exp in fileTranslate:
            exp = fileTranslate[exp]
        y_xticks.append(exp)

    ind = np.arange(len(data))
    width = 0.27
    ax.bar(ind+width, y_bars, yerr=y_std)

    yMetric_translated = yMetric
    if yMetric in translate:
        yMetric_translated = translate[yMetric]
    ax.set_ylabel(yMetric_translated)
    ax.set_xticks(ind+width)
    ax.set_xticklabels(y_xticks)
    plt.tick_params(axis='x', which='major', labelsize=3.5)
    plt.tick_params(axis='x', which='minor', labelsize=3.5)
    plt.tight_layout()
    name = '{0}/bars-{1}-{2}.pdf'.format(outputDir, yMetric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.savefig(name)
    plt.close()

    print '%d error files.' % len(set(errorfiles))
    # print set(errorfiles)
    print '%d zero files.' % len(set(zerofiles))
    # print set(zerofiles)

def plotBoxplot(yMetric, data, outputDir=''):
    global mapping
    global colors
    fig = plt.figure(figsize=(5,2.7))
    ax = fig.add_subplot(111)
    errorfiles = []
    zerofiles = []
    y_bars = []
    y_xticks = []
    allavgs = []
    allv = []
    for exp in data:
        y = []
        tmpavgs = []
        for datafile in data[exp]:
            tmpavg = []
            for mote in data[exp][datafile]:
                if mote[yMetric] != None:
                    y.append(mote[yMetric])
                    tmpavg.append(mote[yMetric])
                else:
                    if mote['mote'] == 0: # is the root node
                        zerofiles.append(datafile)
                    elif yMetric != 'PktReceived' and yMetric != 'avgDurationParentChange': # for pktReceived it is normal that there are None values for the other nodes than the root
                        errorfiles.append(datafile)
            tmpavgs.append(np.mean(tmpavg))
            allv.append(np.mean(tmpavg))
        print exp
        print np.mean(tmpavgs)
        allavgs.append(np.mean(tmpavgs))
        y_bars.append(y)
        y_xticks.append(exp)

    print 'upper avg:'
    print np.mean(allavgs)
    print np.std(allavgs)

    print np.mean(allv)
    print np.std(allv)

    ax.boxplot(y_bars, showfliers=False, showmeans=True, meanline=True)

    yMetric_translated = yMetric
    if yMetric in translate:
        yMetric_translated = translate[yMetric]
    ax.set_ylabel(yMetric_translated)
    ax.set_xticklabels(y_xticks)
    # plt.ylim(0, 10000)
    plt.tight_layout()
    name = '{0}/boxplot-{1}-{2}.pdf'.format(outputDir, yMetric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.savefig(name)
    plt.close()

    print '%d error files.' % len(set(errorfiles))
    if len(errorfiles) > 0:
        print set(errorfiles)
    print '%d zero files.' % len(set(zerofiles))
    # print set(zerofiles)

def getMetricY(metric):
    if metric == 'all':
        return metrics
    else:
        return [metric]

if __name__ == '__main__':
    data = collections.OrderedDict()
    plotType = str(sys.argv[1])

    outputDir = 'plots-%s' % datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    try:
        os.makedirs(outputDir)
    except OSError:
        if not os.path.isdir(outputDir):
            raise

    if plotType == 'scatter':
        metricX = str(sys.argv[2])
        metricY = str(sys.argv[3])
        dataDir = str(sys.argv[4])

        for ix in range(5, len(sys.argv)):
            data[sys.argv[ix]] = {}
            parseresults(dataDir, sys.argv[ix], data[sys.argv[ix]])

        plotScatter(metricX, metricY, data)
    elif plotType == 'bars':
        metricsY = getMetricY(str(sys.argv[2]))
        dataDir = str(sys.argv[3])

        for ix in range(4, len(sys.argv)):
            data[sys.argv[ix]] = {}
            parseresults(dataDir, sys.argv[ix], data[sys.argv[ix]])
        for metric in metricsY:
            print 'Plotting %s metric...' % metric
            plotBars(metric, data, outputDir=outputDir)

    elif plotType == 'boxplot':
        metricsY = getMetricY(str(sys.argv[2]))
        dataDir = str(sys.argv[3])

        for ix in range(4, len(sys.argv)):
            data[sys.argv[ix]] = {}
            parseresults(dataDir, sys.argv[ix], data[sys.argv[ix]])
        for metric in metricsY:
            print 'Plotting %s metric...' % metric
            plotBoxplot(metric, data, outputDir=outputDir)
    else:
        raise 'Wrong plot type!'