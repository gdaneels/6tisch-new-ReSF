import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import collections
import datetime
import re
import copy
import math
import seaborn as sns

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
                 'm_100_p_600_': 'numMotes = 100,\nperiod = 600'}
                 # 'sf_ellsf_freq_medium_max_0_': 'eLLSF\nMAX=0', \
                 # 'sf_resf_mode_optimal_': 'Exact',\
                 # 'sf_resf_mode_sum_': 'Sum', \
                 # 'sf_resf_mode_minimaldelay_': 'Minimal Delay',\
                 # 'sf_resf_mode_random_': 'Random',\
                 # 'sf_msf_freq_short_': 'MSF\n[3s, 6s, 9s]', \
                 # 'sf_resf_freq_short_': 'ReSF\n[3s, 6s, 9s]', \
                 # 'sf_msf_freq_medium_': 'MSF\n[30s, 45s, 60s]', \
                 # 'sf_resf_freq_medium_': 'ReSF\n[30s, 45s, 60s]', \
                 # 'sf_msf_freq_long_': 'MSF\n[300s, 450s, 600s]', \
                 # 'sf_resf_freq_long_': 'ReSF\n[300s, 450s, 600s]', \
                 # 'sf_resf_freq_short_max_200_': 'ReSF\nMAX 200', \
                 # 'sf_resf_freq_short_max_250_': 'ReSF\nMAX 250', \
                 # 'sf_resf_freq_short_max_300_': 'ReSF\nMAX 300',\
                 # 'sf_resf_freq_short_max_350_': 'ReSF\nMAX 350',\
                 # 'sf_resf_freq_short_max_400_': 'ReSF\nMAX 400',\
                 # 'sf_resf_freq_short_max_10000_': 'ReSF\nUnlimited',\
                 # }
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
             'lifetime_2000mAh_openMoteCC2538': 'Lifetime (OpenMote CC2538)\n2000 mAh battery (days)', \
             'lifetime_2000mAh_openMoteB': 'Lifetime (OpenMote B)\n2000 mAh battery (days)', \
             'kbitsPerJoule_openMoteCC2538': 'kbit / Joule (OpenMote CC2538)', \
             'kbitsPerJoule_openMoteB': 'kbit / Joule (OpenMote B)', \
             'sixtopTxAddReq': '6P ADD Requests', \
             'received': 'Received packets at root', 'DAOMessaging': 'DAO Messaging', \
             'resfConvergence': 'ASN of ReSF convergence', 'latency': 'Latency (s)', 'macDrops': 'MAC drops', 'queueDrops': 'Queue drops',
             'pktGen': 'Generated Packets', 'allDrops': 'Dropped Packets'}
translateModes = {'optimal': 'Exact', 'sum': 'Sum', 'minimaldelay': 'Min. delay', 'random': 'Random', None: 'None'}
translateTraffic = {'short': 'Fast', 'medium': 'Frequent', 'long': 'Non-Frequent'}
translateReSF = {'unrestricted': 'ReSF without CA', \
                 'restricted': 'ReSF with CA', \
                 'resfone': 'New ReSF without CA', \
                 'resfrestricted': 'New ReSF with CA', \
                 'resfsf0': 'Original ReSF', \
                 'resfsf0aggressive': 'Original Aggressive ReSF',
                 'ellsfaggressive': 'Aggressive eLLSF',
                 'resfbuffer': 'ReSF - buffer',
                 'ellsf': 'eLLSF', \
                 'msf': 'MSF', \
                 None: 'None'}
translateMotes = {'100': '100\nMotes', '200': '200\nMotes', '300': '300\nMotes', None: 'None'}
metrics = ['bitperjoule', 'lifetime']
colors = ['red', 'green', 'blue', 'orange', 'yellow', 'black']

VOLTS_RADIO = 3.0
VOLTS_CPU = 1.8
#
# uC_IDLE_CONSUMPTION = 47.54
# uC_IDLE_NOT_SYNC_CONSUMPTION = 47.54
# uC_IDLE_CONSUMPTION = 0.0
# uC_IDLE_NOT_SYNC_CONSUMPTION = 0.0

# simulation values of Accurate energy paper
uC_IDLE_CONSUMPTION = 47.54
uC_IDLE_NOT_SYNC_CONSUMPTION = 47.54
uC_SLEEP_CONSUMPTION = 0.82
uC_TXDATARXACK_CONSUMPTION = 106.45
uC_TXDATA_CONSUMPTION = 83.07
uC_TXDATANOACK_CONSUMPTION = 100.32
uC_RXDATATXACK_CONSUMPTION = 107.66
uC_RXDATA_CONSUMPTION = 82.97

J_IDLE_CONSUMPTION = (uC_IDLE_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_IDLE_NOT_SYNC_CONSUMPTION = (uC_IDLE_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_SLEEP_CONSUMPTION = (uC_SLEEP_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_TXDATARXACK_CONSUMPTION = (uC_TXDATARXACK_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_TXDATA_CONSUMPTION = (uC_TXDATA_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_TXDATANOACK_CONSUMPTION = (uC_TXDATANOACK_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_RXDATATXACK_CONSUMPTION = (uC_RXDATATXACK_CONSUMPTION / 1000000.0) * VOLTS_RADIO
J_RXDATA_CONSUMPTION = (uC_RXDATA_CONSUMPTION / 1000000.0) * VOLTS_RADIO

VOLTS_RADIO_OPENMOTEB = 3.0
VOLTS_CPU_OPENMOTEB = 1.8
#
# uC_IDLE_CONSUMPTION = 47.54
# uC_IDLE_NOT_SYNC_CONSUMPTION = 47.54
# uC_IDLE_CONSUMPTION = 0.0
# uC_IDLE_NOT_SYNC_CONSUMPTION = 0.0

# simulation values of Accurate energy paper
uC_IDLE_CONSUMPTION_OPENMOTEB = 52.17
uC_IDLE_NOT_SYNC_CONSUMPTION_OPENMOTEB = 52.17
uC_SLEEP_CONSUMPTION_OPENMOTEB = 0.02
uC_TXDATARXACK_CONSUMPTION_OPENMOTEB = 134.04
uC_TXDATA_CONSUMPTION_OPENMOTEB = 106.7
uC_TXDATANOACK_CONSUMPTION_OPENMOTEB = 125.89
uC_RXDATATXACK_CONSUMPTION_OPENMOTEB = 137.72
uC_RXDATA_CONSUMPTION_OPENMOTEB = 107.84

J_IDLE_CONSUMPTION_OPENMOTEB = (uC_IDLE_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_IDLE_NOT_SYNC_CONSUMPTION_OPENMOTEB = (uC_IDLE_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_SLEEP_CONSUMPTION_OPENMOTEB = (uC_SLEEP_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_TXDATARXACK_CONSUMPTION_OPENMOTEB = (uC_TXDATARXACK_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_TXDATA_CONSUMPTION_OPENMOTEB = (uC_TXDATA_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_TXDATANOACK_CONSUMPTION_OPENMOTEB = (uC_TXDATANOACK_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_RXDATATXACK_CONSUMPTION_OPENMOTEB = (uC_RXDATATXACK_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB
J_RXDATA_CONSUMPTION_OPENMOTEB = (uC_RXDATA_CONSUMPTION_OPENMOTEB / 1000000.0) * VOLTS_RADIO_OPENMOTEB

SLOTDURATION = 0.015 # ms
SLOTFRAME_LENGTH = 101 # slots
APPLICATION_SIZE_BITS = 104 * 8 # bits

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

def getExperimentName(exp):
    if exp in fileTranslate:
        return fileTranslate[exp]
    return exp

def getLabelName(name):
    if name in translate:
        return translate[name]
    return name

def parseresults(dataDir, parameter, data):
    resfConvergenceDatafiles = []
    print data
    cmd = "find {0} -ipath *{1}*/output_cpu0.dat".format(dataDir, parameter)
    listFiles = os.popen(cmd).read().split("\n")[:-1] # for some reason, there is a trailing whitespace in the list, remove it
    print "Processing %d file(s) in %s." % (len(listFiles), str(dataDir))
    for datafile in listFiles:
        validate(os.path.dirname(datafile))

        nrIdle = {}
        nrIdleNotSync = {}
        nrSleep = {}
        nrTxDataRxAck = {}
        nrTxData = {}
        nrTxDataNoAck = {}
        nrTxDataRxNack = {}
        nrRxDataTxAck = {}
        nrRxData = {}
        pktReceived = {}
        pktLatencies = {}
        pktDropsMac = {}
        pktDropsQueue = {}
        pktGen = {}
        pktArrivedToGen = {}
        sixtopTxAddReq = {}
        sixtopTxAddResp = {}
        sixtopTxDelReq = {}
        sixtopTxDelResp = {}
        activeDAO = {}
        initiatedDAO = {}
        receivedDAO = {}
        resfConvergence = {}
        # get all the data
        with open(datafile, 'r') as inF:
            for line in inF:
                if '#nrIdle' in line and not '#nrIdleNotSync' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrIdle[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#nrIdleNotSync' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrIdleNotSync[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#nrSleep' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrSleep[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#nrTxDataRxAck' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrTxDataRxAck[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#nrTxData' in line and not '#nrTxDataNoAck' in line and not '#nrTxDataRxAck' in line and not '#nrTxDataRxNack' in line:
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrTxData[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#nrTxDataNoAck' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrTxDataNoAck[int(mote.split("@")[0])] = float(mote.split("@")[1])
                    # print 'Got charge.'
                if '#nrTxDataRxNack' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        nrTxDataRxNack[int(mote.split("@")[0])] = float(mote.split("@")[1])
                if '#nrRxDataTxAck' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        nrRxDataTxAck[int(mote.split("@")[0])] = float(mote.split("@")[1])
                if '#nrRxData' in line.strip() and not '#nrRxDataTxAck' in line:
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        nrRxData[int(mote.split("@")[0])] = float(mote.split("@")[1])
                if '#PktReceived' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktReceived[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktReceived[int(mote.split("@")[0])] = None
                    # print 'Got hopcount.'
                if '#sixtopTxAddReq' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        sixtopTxAddReq[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#sixtopTxAddResp' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        sixtopTxAddResp[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#sixtopTxDelReq' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        sixtopTxDelReq[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#sixtopTxDelResp' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        sixtopTxDelResp[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#activeDAO' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        activeDAO[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#initiatedDAO' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        initiatedDAO[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#receivedDAO' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        receivedDAO[int(mote.split("@")[0])] = int(mote.split("@")[1])
                if '#PktLatencies' in line.strip():
                    lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                    for mote in lineList:
                        if mote.split("@")[1] != 'None':
                            pktLatencies[int(mote.split("@")[0])] = float(mote.split("@")[1])
                        else:
                            pktLatencies[int(mote.split("@")[0])] = None
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
                if '#PktGen' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktGen[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktGen[int(mote.split("@")[0])] = None
                if '#PktArrivedToGen' in line.strip():
                    lineList = line.strip().split(' ')[2:] # first two are information, drop them
                    for mote in lineList:
                        if '@' in mote:
                            if mote.split("@")[1] != 'None':
                                pktArrivedToGen[int(mote.split("@")[0])] = float(mote.split("@")[1])
                            else:
                                pktArrivedToGen[int(mote.split("@")[0])] = None
                # if '#resfConvergence' in line.strip():
                #     lineList = line.strip().split(' ')[2:]  # first two are information, drop them
                #     for mote in lineList:
                #         resfConvergence[int(mote.split("@")[0])] = int(mote.split("@")[1])
                        # if resfConvergence[int(mote.split("@")[0])] > 500000:
                        #     resfConvergenceDatafiles.append(datafile)
                        #     resfConvergenceDatafiles = list(set(resfConvergenceDatafiles))

        if datafile not in data:
            data[datafile] = [] # make a list of (id, hopcount, consumption) per node per datafile

        numMotes = getNrMotes(datafile)

        # summarize the data
        for mote in range(0, numMotes):
            # if mote not in resfConvergence: # if it does not have resf convergence, put to -1, this will be not included in the calculations
            #     resfConvergence[mote] = -1
            data[datafile].append({'mote': mote, 'nrIdle': nrIdle[mote],
                                   'nrIdleNotSync': nrIdleNotSync[mote], 'nrSleep': nrSleep[mote],
                                   'nrTxDataRxAck': nrTxDataRxAck[mote], 'nrTxDataNoAck': nrTxDataNoAck[mote],
                                   'nrTxDataRxNack': nrTxDataRxNack[mote],
                                   'nrTxData': nrTxData[mote], 'nrRxDataTxAck': nrRxDataTxAck[mote],
                                   'nrRxData': nrRxData[mote], 'pktReceived': pktReceived[mote], 'pktLatencies': pktLatencies[mote],
                                   'sixtopTxAddReq': sixtopTxAddReq[mote], 'sixtopTxAddResp': sixtopTxAddResp[mote],
                                   'sixtopTxDelReq': sixtopTxDelReq[mote], 'sixtopTxDelResp': sixtopTxDelResp[mote],
                                   'activeDAO': activeDAO[mote], 'initiatedDAO': initiatedDAO[mote], 'receivedDAO': receivedDAO[mote],
                                   'pktDropsMac': pktDropsMac[mote], 'pktDropsQueue': pktDropsQueue[mote], 'pktGen': pktGen[mote],
                                   'pktArrivedToGen': pktArrivedToGen[mote]})
                                   # 'resfConvergence': resfConvergence[mote]})

        if data[datafile][0]['mote'] != 0: # should be root node
            assert False
        # print datafile

    # period = float(list(detectInName('p', listFiles[0]))[0])
    print listFiles
    cycles = float(list(detectInName('cycles', listFiles[0]))[0])
    for df in listFiles:
        # p = float(list(detectInName('p', df))[0])
        c = float(list(detectInName('cycles', df))[0])
        if c != cycles:
            # print '%.4f vs %.4f' % (p, period)
            print '%.4f vs %.4f' % (c, cycles)
            raise 'Different cycles!'

    # print len(resfConvergenceDatafiles)
    # print resfConvergenceDatafiles

    return cycles

# Calculate the bits per Joule per iteration.
def calculateBitsPerJoulePerIteration(data, moteType, exp):
    results = []
    for iteration in data:
        nrIdle = 0
        nrIdleNotSync = 0
        nrSleep = 0
        nrTxDataRxAck = 0
        nrTxDataNoAck = 0
        nrTxData = 0
        nrRxDataTxAck = 0
        nrRxData = 0
        nrReceived = 0

        for moteList in data[iteration]:
            if moteList['mote'] != 0:
                nrIdle += moteList['nrIdle']
                nrIdleNotSync += moteList['nrIdleNotSync']
                nrSleep += moteList['nrSleep']
                nrTxDataRxAck += moteList['nrTxDataRxAck']
                nrTxData += moteList['nrTxData']
                nrTxDataNoAck += moteList['nrTxDataNoAck']
                nrRxDataTxAck += moteList['nrRxDataTxAck']
                nrRxData += moteList['nrRxData']
            if moteList['mote'] == 0:
                nrReceived += moteList['pktReceived']

        totalConsumption = 0.0
        if moteType == 'OpenMoteCC2538':
            totalConsumption += nrIdle * J_IDLE_CONSUMPTION
            totalConsumption += nrIdleNotSync * J_IDLE_NOT_SYNC_CONSUMPTION
            totalConsumption += nrSleep * J_SLEEP_CONSUMPTION
            totalConsumption += nrTxDataRxAck * J_TXDATARXACK_CONSUMPTION
            totalConsumption += nrTxData * J_TXDATA_CONSUMPTION
            totalConsumption += nrTxDataNoAck * J_TXDATANOACK_CONSUMPTION
            totalConsumption += nrRxDataTxAck * J_RXDATATXACK_CONSUMPTION
            totalConsumption += nrRxData * J_RXDATA_CONSUMPTION
        elif moteType == 'OpenMoteB':
            totalConsumption += nrIdle * J_IDLE_CONSUMPTION_OPENMOTEB
            totalConsumption += nrIdleNotSync * J_IDLE_NOT_SYNC_CONSUMPTION_OPENMOTEB
            totalConsumption += nrSleep * J_SLEEP_CONSUMPTION_OPENMOTEB
            totalConsumption += nrTxDataRxAck * J_TXDATARXACK_CONSUMPTION_OPENMOTEB
            totalConsumption += nrTxData * J_TXDATA_CONSUMPTION_OPENMOTEB
            totalConsumption += nrTxDataNoAck * J_TXDATANOACK_CONSUMPTION_OPENMOTEB
            totalConsumption += nrRxDataTxAck * J_RXDATATXACK_CONSUMPTION_OPENMOTEB
            totalConsumption += nrRxData * J_RXDATA_CONSUMPTION_OPENMOTEB

        # to kbit
        results.append({'exp': getExperimentName(exp), 'val': (((APPLICATION_SIZE_BITS * (nrReceived)) / (float(totalConsumption))) / 1000.0), 'iteration': iteration})

    return results

# Get all the numbers of received packets per iteration.
def calculateReceived(data, exp, nrMotes=None, sfMode=None, freq=None):
    results = []
    for iteration in data:
        result = {'exp': getExperimentName(exp), 'val': None, 'iteration': iteration, 'motes': translateMotes[nrMotes], 'sfMode': translateReSF[sfMode], 'freq': translateTraffic[freq]}
        nrReceived = 0
        for moteList in data[iteration]:
            if moteList['mote'] == 0:
                nrReceived += moteList['pktReceived']
                break
        result['val'] = nrReceived
        results.append(copy.deepcopy(result))
    return results

def calculatePktGen(data, exp, nrMotes=None, sfMode=None, freq=None):
    results = []
    for iteration in data:
        result = {'exp': getExperimentName(exp), 'val': None, 'iteration': iteration, 'motes': translateMotes[nrMotes], 'sfMode': translateReSF[sfMode], 'freq': translateTraffic[freq]}
        nrPktGen = 0
        for moteList in data[iteration]:
            if moteList['mote'] != 0 and moteList['pktGen'] is not None:
                nrPktGen += moteList['pktGen']
        result['val'] = nrPktGen
        results.append(copy.deepcopy(result))
    return results

def calculatePktArrivedToGen(data, exp, nrMotes=None, sfMode=None, freq=None):
    results = []
    for iteration in data:
        result = {'exp': getExperimentName(exp), 'val': None, 'iteration': iteration, 'motes': translateMotes[nrMotes], 'sfMode': translateReSF[sfMode], 'freq': translateTraffic[freq]}
        nrPktArrivedToGen = 0
        for moteList in data[iteration]:
            if moteList['mote'] != 0 and moteList['pktArrivedToGen'] is not None:
                nrPktArrivedToGen += moteList['pktArrivedToGen']
        result['val'] = nrPktArrivedToGen
        results.append(copy.deepcopy(result))
    return results

# Get all charges of all motes.
def calculateChargePerMote(data, moteType, exp, freq=None, sfMode=None):
    results = []
    for iteration in data:
        for moteList in data[iteration]:
            # do not do this for root, only for source nodes
            if moteList['mote'] != 0:
                totalCharge = 0
                if moteType == 'OpenMoteCC2538':
                    totalCharge += moteList['nrIdle'] * uC_IDLE_CONSUMPTION
                    totalCharge += moteList['nrIdleNotSync'] * uC_IDLE_NOT_SYNC_CONSUMPTION
                    totalCharge += moteList['nrSleep'] * uC_SLEEP_CONSUMPTION
                    totalCharge += moteList['nrTxDataRxAck'] * uC_TXDATARXACK_CONSUMPTION
                    totalCharge += moteList['nrTxData'] * uC_TXDATA_CONSUMPTION
                    totalCharge += moteList['nrTxDataNoAck'] * uC_TXDATANOACK_CONSUMPTION
                    totalCharge += moteList['nrRxDataTxAck'] * uC_RXDATATXACK_CONSUMPTION
                    totalCharge += moteList['nrRxData'] * uC_RXDATA_CONSUMPTION
                elif moteType == 'OpenMoteB':
                    totalCharge += moteList['nrIdle'] * uC_IDLE_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrIdleNotSync'] * uC_IDLE_NOT_SYNC_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrSleep'] * uC_SLEEP_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrTxDataRxAck'] * uC_TXDATARXACK_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrTxData'] * uC_TXDATA_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrTxDataNoAck'] * uC_TXDATANOACK_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrRxDataTxAck'] * uC_RXDATATXACK_CONSUMPTION_OPENMOTEB
                    totalCharge += moteList['nrRxData'] * uC_RXDATA_CONSUMPTION_OPENMOTEB
                # this is the total charge for the whole length of the experiment
                results.append({'exp': getExperimentName(exp), 'val': totalCharge, 'iteration': iteration, 'mote': moteList['mote'], 'sfMode': translateReSF[sfMode], 'freq': translateTraffic[freq]})
    return results

# Calculate the lifetimes of all charges of all motes in all iterations.
def calculateLifetime(chargePerMoteDF, batterySize, cycles, exp, freq=None, sfMode=None):
    results = []
    for index, row in chargePerMoteDF.iterrows():
        # total mAh of whole experimetn
        mAh = (row['val']) / 3600000.0  # uC / 3600000 = mAh
        # get length experiment:
        numCycles = cycles
        # convert numCycles to seconds
        lengthSeconds = (numCycles) * SLOTDURATION * SLOTFRAME_LENGTH
        # number of seconds you could do with this battery
        batterySeconds = float(batterySize) / (mAh / float(lengthSeconds))
        # convert to days
        days = batterySeconds / 3600.0 / 24.0
        # days = moteCharge
        results.append({'exp': getExperimentName(exp), 'val': days, 'iteration': row['iteration'], 'mote': row['mote'], 'sfMode': row['sfMode'], 'freq': row['freq']})
    return results

# Calculate the sum per state of all motes.
def calculateStateFrequency(data, exp):
    results = []
    for iteration in data:
        for moteList in data[iteration]:
            if moteList['mote'] != 0:
                totalFrequency = 0
                # do not do this for root, only for source nodes
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrIdle'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrIdle'})
                totalFrequency += moteList['nrIdle']
                # print 'nrIdle %d' % moteList['nrIdle']
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrIdleNotSync'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrIdleNotSync'})
                totalFrequency += moteList['nrIdleNotSync']
                # print 'nrIdleNotSync %d' % moteList['nrIdleNotSync']
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrSleep'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrSleep'})
                totalFrequency += moteList['nrSleep']
                # print 'nrSleep %d' % moteList['nrSleep']
                results.append({'exp': getExperimentName(exp), 'val': (moteList['nrTxDataRxAck'] - moteList['nrTxDataRxNack']), 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrTxDataRxAck'})
                totalFrequency += (moteList['nrTxDataRxAck'] - moteList['nrTxDataRxNack'])
                # print 'nrTxDataRxAck %d' % (moteList['nrTxDataRxAck'] - moteList['nrTxDataRxNack'])
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrTxDataRxNack'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrTxDataRxNack'})
                totalFrequency += moteList['nrTxDataRxNack']
                # print 'nrTxDataRxNack %d' % moteList['nrTxDataRxNack']
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrTxDataNoAck'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrTxDataNoAck'})
                totalFrequency += moteList['nrTxDataNoAck']
                # print 'nrTxDataNoAck %d' % moteList['nrTxDataNoAck']
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrRxDataTxAck'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrRxDataTxAck'})
                totalFrequency += moteList['nrRxDataTxAck']
                # print 'nrRxDataTxAck %d' % moteList['nrRxDataTxAck']
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrTxData'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrTxData'})
                totalFrequency += moteList['nrTxData']
                # print 'nrTxData %d' % moteList['nrTxData']
                results.append({'exp': getExperimentName(exp), 'val': moteList['nrRxData'], 'iteration': iteration, 'mote': moteList['mote'], 'state': 'nrRxData'})
                totalFrequency += moteList['nrRxData']
                # print 'nrRxData %d' % moteList['nrRxData']
                # print 'Mote %d, total number of time slots: %d' % (moteList['mote'], totalFrequency)

    return results

# Get all charges of all motes.
def calculateLatency(data, exp, frequency=None, mode=None, sfMode=None):
    results = []
    for iteration in data:
        for moteList in data[iteration]:
            # do not do this for root, only for source nodes
            if moteList['mote'] != 0 and moteList['pktLatencies'] != None:
                results.append({'exp': getExperimentName(exp), 'val': moteList['pktLatencies'] * SLOTDURATION, 'iteration': iteration, 'mote': moteList['mote'], 'freq': translateTraffic[frequency], 'modeC': translateModes[mode], 'sfMode': translateReSF[sfMode]})
    return results

def calculateMACDrops(data, exp, frequency=None, mode=None):
    results = []
    for iteration in data:
        for moteList in data[iteration]:
            # do not do this for root, only for source nodes
            if moteList['mote'] != 0 and moteList['pktDropsMac'] != None:
                results.append({'exp': getExperimentName(exp), 'val': moteList['pktDropsMac'], 'iteration': iteration, 'mote': moteList['mote'], 'freq': translateTraffic[frequency], 'modeC': translateModes[mode]})
    return results

def calculateQueueDrops(data, exp, frequency=None, mode=None):
    results = []
    for iteration in data:
        for moteList in data[iteration]:
            # do not do this for root, only for source nodes
            if moteList['mote'] != 0 and moteList['pktDropsQueue'] != None:
                results.append({'exp': getExperimentName(exp), 'val': moteList['pktDropsQueue'], 'iteration': iteration, 'mote': moteList['mote'], 'freq': translateTraffic[frequency], 'modeC': translateModes[mode]})
    return results

def calculateAllDrops(data, exp, frequency=None, mode=None, sfMode=None):
    results = []
    for iteration in data:
        allDrops = 0
        for moteList in data[iteration]:
            # do not do this for root, only for source nodes
            if moteList['mote'] != 0:
                qDrops = moteList['pktDropsQueue']
                if qDrops is None:
                    qDrops = 0
                qMAC = moteList['pktDropsMac']
                if qMAC is None:
                    qMAC = 0
                allDrops += (qDrops + qMAC)
        results.append({'exp': getExperimentName(exp), 'val': allDrops, 'iteration': iteration, 'freq': translateTraffic[frequency], 'modeC': translateModes[mode], 'sfMode': translateReSF[sfMode]})
    return results

# def calculateDAOPerNetwork(data):
#     output = {}
#     output['activeDAO'] = []
#     output['initiatedDAO'] = []
#     output['receivedDAO'] = []
#
#     outputMeanFinal = {}
#     outputMean = {'activeDAO': [], 'initiatedDAO': [], 'receivedDAO': []}
#     outputStd = {'activeDAO': [], 'initiatedDAO': [], 'receivedDAO': []}
#
#     for iteration in data:
#         # reset for this experiment
#         output['activeDAO'] = []
#         output['initiatedDAO'] = []
#         output['receivedDAO'] = []
#
#         for moteList in data[iteration]:
#             if moteList['mote'] != 0:
#                 # do not do this for root, only for source nodes
#                 output['activeDAO'].append(moteList['activeDAO'])
#                 output['initiatedDAO'].append(moteList['initiatedDAO'])
#             else:
#                 output['receivedDAO'].append(moteList['receivedDAO'])
#
#         # take the average per network
#         outputMean['activeDAO'].append(np.mean(output['activeDAO']))
#         outputMean['initiatedDAO'].append(np.mean(output['initiatedDAO']))
#         outputMean['receivedDAO'].append(np.mean(output['receivedDAO']))
#
#     # take the average of the average per network
#     outputMeanFinal['activeDAO'] = np.mean(outputMean['activeDAO'])
#     outputMeanFinal['initiatedDAO'] = np.mean(outputMean['initiatedDAO'])
#     outputMeanFinal['receivedDAO'] = np.mean(outputMean['receivedDAO'])
#     # take the std of the average per network
#     outputStd['activeDAO'] = np.std(outputMean['activeDAO'])
#     outputStd['initiatedDAO'] = np.std(outputMean['initiatedDAO'])
#     outputStd['receivedDAO'] = np.std(outputMean['receivedDAO'])
#
#     # return outputMeanFinal, outputStd
#     return outputMeanFinal

def calculateDAO(data, exp):
    results = []
    for iteration in data:
        # reset for this experiment
        for moteList in data[iteration]:
            if moteList['mote'] != 0:
                # do not do this for root, only for source nodes
                results.append({'exp': getExperimentName(exp), 'val': moteList['activeDAO'], 'iteration': iteration, 'mote': moteList['mote'], 'type': 'activeDAO'})
                results.append({'exp': getExperimentName(exp), 'val': moteList['initiatedDAO'], 'iteration': iteration, 'mote': moteList['mote'], 'type': 'initiatedDAO'})
    return results

def calculateDAOReceived(data, exp):
    results = []
    for iteration in data:
        # reset for this experiment
        for moteList in data[iteration]:
            if moteList['mote'] == 0:
                results.append({'exp': getExperimentName(exp), 'val': moteList['receivedDAO'], 'iteration': iteration, 'type': 'receivedDAO'})
    return results

def calculateSixTopMessaging(data, exp):
    results = []
    for iteration in data:
        for moteList in data[iteration]:
            if moteList['mote'] != 0:
                results.append({'exp': getExperimentName(exp), 'val': moteList['sixtopTxAddReq'], 'iteration': iteration, 'mote': moteList['mote'], 'type': 'sixtopTxAddReq'})
                results.append({'exp': getExperimentName(exp), 'val': moteList['sixtopTxAddResp'], 'iteration': iteration, 'mote': moteList['mote'], 'type': 'sixtopTxAddResp'})
                results.append({'exp': getExperimentName(exp), 'val': moteList['sixtopTxDelReq'], 'iteration': iteration, 'mote': moteList['mote'], 'type': 'sixtopTxDelReq'})
                results.append({'exp': getExperimentName(exp), 'val': moteList['sixtopTxDelResp'], 'iteration': iteration, 'mote': moteList['mote'], 'type': 'sixtopTxDelResp'})
    return results


# def calculateReSFConvergence(data):
#     resfConvergence = []
#
#     for iteration in data:
#         for moteList in data[iteration]:
#             if moteList['mote'] != 0 and moteList['resfConvergence'] != -1:
#                 # do not do this for root, only for source nodes
#                 resfConvergence.append(moteList['resfConvergence'])
#
#     return resfConvergence

# def plotBoxplot(metric, data, outputDir=''):
#     global mapping
#     global colors
#     fig = plt.figure(figsize=(5,2.7))
#     ax = fig.add_subplot(111)
#     # ax.tick_params(axis='both', which='major', labelsize=10)
#     # ax.tick_params(axis='both', which='minor', labelsize=6)
#     boxplots = []
#     y_xticks = []
#     for exp, dat in sorted(data.items(), key=lambda x: x[0]):
#         boxplots.append(dat)
#         # print fileTranslate
#         if exp in fileTranslate:
#             y_xticks.append(fileTranslate[exp])
#         else:
#             y_xticks.append(exp)
#
#     boxplotsMeans = []
#     for dat in boxplots:
#         iqr = np.percentile(dat, 75) - np.percentile(dat, 25)
#         datMean = []
#         for elem in dat:
#             if elem >= (np.percentile(dat, 25) - iqr * 1.5) and elem <= (np.percentile(dat, 75) + iqr * 1.5):
#                 datMean.append(elem)
#         boxplotsMeans.append(np.mean(datMean))
#
#     print boxplotsMeans
#
#     ax.boxplot(boxplots, showfliers=True, showmeans=True, meanline=False)
#     ax.plot(range(1, len(boxplotsMeans) + 1), boxplotsMeans, 'go', markersize=5)
#     ax.set_ylabel(translate[metric], fontsize=8)
#     ax.set_xticklabels(y_xticks, fontsize=4)
#     plt.tight_layout()
#     name = '{0}/boxplot-{1}-{2}.pdf'.format(outputDir, metric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
#     plt.savefig(name)
#     plt.close()

# def plotBoxplot(metric, data, outputDir=''):
#     global mapping
#     global colors
#     fig = plt.figure(figsize=(5,2.7))
#     ax = fig.add_subplot(111)
#     # ax.tick_params(axis='both', which='major', labelsize=10)
#     # ax.tick_params(axis='both', which='minor', labelsize=6)
#     boxplots = []
#     y_xticks = []
#     for exp, dat in sorted(data.items(), key=lambda x: x[0]):
#         boxplots.append(dat)
#         # print fileTranslate
#         if exp in fileTranslate:
#             y_xticks.append(fileTranslate[exp])
#         else:
#             y_xticks.append(exp)
#
#     boxplotsMeans = []
#     for dat in boxplots:
#         iqr = np.percentile(dat, 75) - np.percentile(dat, 25)
#         datMean = []
#         for elem in dat:
#             if elem >= (np.percentile(dat, 25) - iqr * 1.5) and elem <= (np.percentile(dat, 75) + iqr * 1.5):
#                 datMean.append(elem)
#         boxplotsMeans.append(np.mean(datMean))
#
#     print boxplotsMeans
#
#     ax.boxplot(boxplots, showfliers=True, showmeans=True, meanline=False)
#     ax.plot(range(1, len(boxplotsMeans) + 1), boxplotsMeans, 'go', markersize=5)
#     ax.set_ylabel(translate[metric], fontsize=8)
#     ax.set_xticklabels(y_xticks, fontsize=4)
#     plt.tight_layout()
#     name = '{0}/boxplot-{1}-{2}.pdf'.format(outputDir, metric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
#     plt.savefig(name)
#     plt.close()

def plotBoxplotSeaborn(metric, data, sorter, outputDir=''):
    sns.set_style('white')
    pal = sns.color_palette('colorblind')

    global mapping
    global colors
    boxplots = []

    data.exp = data.exp.astype("category")
    data.exp.cat.set_categories(sorter, inplace=True)
    data = data.sort_values(["exp"])

    meanDataframe = data.groupby(['exp'])['val'].mean().reset_index()
    meanDataframe.exp = meanDataframe.exp.astype("category")
    meanDataframe.exp.cat.set_categories(sorter, inplace=True)
    meanDataframe = meanDataframe.sort_values(["exp"])

    # results = []
    # boxplotsMeans = []
    # for dat in boxplots:
    #     iqr = np.percentile(dat, 75) - np.percentile(dat, 25)
    #     datMean = []
    #     for elem in dat:
    #         if elem >= (np.percentile(dat, 25) - iqr * 1.5) and elem <= (np.percentile(dat, 75) + iqr * 1.5):
    #             datMean.append(elem)
    #     boxplotsMeans.append(np.mean(datMean))
    #     # result = {'exp': }


    axBoxplot = sns.boxplot(x='exp', y='val', data=data, palette=pal, width=0.3, showfliers=False, showmeans=False)
    ax = sns.scatterplot(x='exp', y='val', data=meanDataframe, palette=pal, marker='x', size=3, linewidth=2, color='#303030')
    axBoxplot.tick_params(labelsize=8)
    ax.legend_.remove()
    ax.set_xlabel('')
    axBoxplot.set_xlabel('')
    sns.despine()
    name = '{0}/boxplot-{1}-{2}.eps'.format(outputDir, metric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.ylabel(getLabelName(metric))
    # plt.legend(loc='upper left')
    plt.tight_layout()
    plt.savefig(name)
    plt.close()

def plotMultipleBoxplotSeaborn(metric, data, sorter, outputDir='', xsplit=None, hue=None, xlabel=None):
    plt.figure(figsize=(6, 3))
    sns.set_style('white')
    pal = sns.color_palette('colorblind')

    global mapping
    global colors
    boxplots = []

    data.exp = data.exp.astype("category")
    data.exp.cat.set_categories(sorter, inplace=True)
    data = data.sort_values(["exp"])

    print metric
    meanDataframe = data.groupby(['exp'])['val'].mean().reset_index()
    print meanDataframe
    # meanDataframe.exp = meanDataframe.exp.astype("category")
    # meanDataframe.exp.cat.set_categories(sorter, inplace=True)
    # meanDataframe = meanDataframe.sort_values(["exp"])

    # results = []
    # boxplotsMeans = []
    # for dat in boxplots:
    #     iqr = np.percentile(dat, 75) - np.percentile(dat, 25)
    #     datMean = []
    #     for elem in dat:
    #         if elem >= (np.percentile(dat, 25) - iqr * 1.5) and elem <= (np.percentile(dat, 75) + iqr * 1.5):
    #             datMean.append(elem)
    #     boxplotsMeans.append(np.mean(datMean))
    #     # result = {'exp': }


    axBoxplot = sns.boxplot(x=xsplit, y='val', data=data, palette=pal, width=0.7, linewidth=1, showfliers=False, showmeans=True, hue=hue, meanprops=dict(marker='x', markersize=3, linewidth=2, markeredgecolor="#303030"))
    # ax = sns.scatterplot(x=xsplit, y='val', data=meanDataframe, palette=pal, marker='x', size=3, linewidth=2, color='#303030', hue='exp')
    axBoxplot.tick_params(labelsize=10)
    axBoxplot.set(ylim=(0,None))
    # ax.legend_.remove()
    # ax.set_xlabel('')
    axBoxplot.set_xlabel('')
    sns.despine(ax=axBoxplot)
    name = '{0}/multiple-boxplot-{1}-{2}.eps'.format(outputDir, metric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.ylabel(getLabelName(metric))
    plt.xlabel(xlabel)
    # plt.legend(loc='upper left')
    axBoxplot.legend(loc='best', frameon=False)
    plt.tight_layout()
    plt.savefig(name)
    plt.close()

def plotMultipleBoxplotSeaborn2(metric, data, outputDir='', xsplit=None):
    sns.set_style('white')
    pal = sns.color_palette('colorblind')

    global mapping
    global colors
    boxplots = []

    boxplotsMeans = []
    for dat in boxplots:
        iqr = np.percentile(dat, 75) - np.percentile(dat, 25)
        datMean = []
        for elem in dat:
            if elem >= (np.percentile(dat, 25) - iqr * 1.5) and elem <= (np.percentile(dat, 75) + iqr * 1.5):
                datMean.append(elem)
        boxplotsMeans.append(np.mean(datMean))

    print boxplotsMeans

    sns.boxplot(x=xsplit, y='val', data=data, palette=pal, hue='exp', width=0.3)
    sns.despine()
    name = '{0}/boxplot-{1}-{2}.pdf'.format(outputDir, metric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.ylabel(getLabelName(metric))
    # plt.legend(loc='upper left')
    plt.savefig(name)
    plt.close()

def plotBarsSeaborn(yMetric, data, outputDir='', xsplit=None):
    global mapping
    global colors

    sns.barplot(x=xsplit, y='val', data=data, hue='exp')
    plt.tight_layout()
    name = '{0}/bars-{1}-{2}.pdf'.format(outputDir, yMetric, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    plt.savefig(name)
    plt.close()

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
    resultType = str(sys.argv[1])
    resultTypes = ['resfModes', 'collisionAvoidance', 'normal', 'sporadic', 'other']
    if resultType not in resultTypes:
        assert False

    outputDir = 'plots-%s' % datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    outputDirAll = '%s/individual' % outputDir
    outputDirPerIteration = '%s/network' % outputDir
    try:
        os.makedirs(outputDir)
        os.makedirs(outputDirAll)
        os.makedirs(outputDirPerIteration)
    except OSError:
        if not os.path.isdir(outputDir):
            raise

    dataDir = str(sys.argv[2])

    # aggregated over all motes
    lifetime2000OpenMoteCC2538 = pd.DataFrame()
    lifetime2000OpenMoteB = pd.DataFrame()
    stateFrequency = pd.DataFrame()
    stateFrequencySum = pd.DataFrame()
    sixtopMessaging = pd.DataFrame()
    DAOMessaging = pd.DataFrame()
    DAOReceived = pd.DataFrame()
    chargePerMoteOpenMoteCC2538 = pd.DataFrame()
    chargePerMoteOpenMoteB = pd.DataFrame()
    latency = pd.DataFrame()
    macDrops = pd.DataFrame()
    queueDrops = pd.DataFrame()
    pktGenerated = pd.DataFrame()
    pktArrivedToGenerated = pd.DataFrame()
    allDrops = pd.DataFrame()

    # per iteration
    received = pd.DataFrame()
    bitsPerJouleOpenMoteCC2538 = pd.DataFrame()
    bitsPerJouleOpenMoteB = pd.DataFrame()

    sorter = []
    sorterMode = []

    for ix in range(3, len(sys.argv)):
        freq = None
        mode = None
        sfMode = None
        nrMotes = None

        rgx = '[_\/]+%s_([A-Za-z0-9]+)_' % 'freq'
        freq = list(get_set_rgx([sys.argv[ix]], rgx))[0]
        if freq is None:
            print 'Variable \'freq\' is None.'
        if resultType == 'resfModes':
            rgx = '[_\/]+%s_([A-Za-z0-9]+)_' % 'mode'
            mode = list(get_set_rgx([sys.argv[ix]], rgx))[0]
            if mode is None:
                print 'Variable \'mode\' is None.'
        elif resultType == 'collisionAvoidance':
            rgx = '^%s_([A-Za-z0-9]+)_' % 'sf'
            sfMode = list(get_set_rgx([sys.argv[ix]], rgx))[0]
            if sfMode is None:
                print 'Variable \'sfMode\' is None.'
            elif sfMode == 'resfrestricted':
                sfMode = 'restricted'
            elif sfMode == 'resfone':
                sfMode = 'unrestricted'
            else:
                sfMode = None
        elif resultType == 'normal' or resultType == 'sporidac':
            rgx = '^%s_([A-Za-z0-9]+)_' % 'sf'
            sfMode = list(get_set_rgx([sys.argv[ix]], rgx))[0]
            if sfMode is None:
                print 'Variable \'sfMode\' is None.'
        else:
            assert False

        sorter.append(getExperimentName(sys.argv[ix]))
        # if translateModes[mode] not in sorterMode:
        #     sorterMode.append(translateModes[mode])
        data[sys.argv[ix]] = {}
        cycles = parseresults(dataDir, sys.argv[ix], data[sys.argv[ix]])

        # aggregated over all motes
        chargePerMoteOpenMoteCC2538 = chargePerMoteOpenMoteCC2538.append((calculateChargePerMote(data[sys.argv[ix]], 'OpenMoteCC2538', sys.argv[ix], freq=freq, sfMode=sfMode)))
        lifetime2000OpenMoteCC2538 = lifetime2000OpenMoteCC2538.append(calculateLifetime(chargePerMoteOpenMoteCC2538, 2000, cycles, sys.argv[ix], freq=freq, sfMode=sfMode))
        chargePerMoteOpenMoteB = chargePerMoteOpenMoteB.append((calculateChargePerMote(data[sys.argv[ix]], 'OpenMoteB', sys.argv[ix], freq=freq, sfMode=sfMode)))
        lifetime2000OpenMoteB = lifetime2000OpenMoteB.append(calculateLifetime(chargePerMoteOpenMoteB, 2000, cycles, sys.argv[ix], freq=freq, sfMode=sfMode))
        stateFrequency = stateFrequency.append(calculateStateFrequency(data[sys.argv[ix]], sys.argv[ix]))
        sixtopMessaging = sixtopMessaging.append(calculateSixTopMessaging(data[sys.argv[ix]], sys.argv[ix]))
        DAOMessaging = DAOMessaging.append(calculateDAO(data[sys.argv[ix]], sys.argv[ix]))
        latency = latency.append(calculateLatency(data[sys.argv[ix]], sys.argv[ix], frequency=freq, mode=mode, sfMode=sfMode))
        macDrops = macDrops.append(calculateMACDrops(data[sys.argv[ix]], sys.argv[ix], frequency=freq, mode=mode))
        queueDrops = queueDrops.append(calculateQueueDrops(data[sys.argv[ix]], sys.argv[ix], frequency=freq, mode=mode))
        allDrops = allDrops.append(calculateAllDrops(data[sys.argv[ix]], sys.argv[ix], frequency=freq, mode=mode, sfMode=sfMode))

        # aggregated per network
        bitsPerJouleOpenMoteCC2538 = bitsPerJouleOpenMoteCC2538.append(calculateBitsPerJoulePerIteration(data[sys.argv[ix]], 'OpenMoteCC2538', sys.argv[ix]))
        bitsPerJouleOpenMoteB = bitsPerJouleOpenMoteB.append(calculateBitsPerJoulePerIteration(data[sys.argv[ix]], 'OpenMoteB', sys.argv[ix]))
        received = received.append(calculateReceived(data[sys.argv[ix]], sys.argv[ix], nrMotes=nrMotes, sfMode=sfMode, freq=freq))
        pktArrivedToGenerated = pktArrivedToGenerated.append(calculatePktArrivedToGen(data[sys.argv[ix]], sys.argv[ix], nrMotes=nrMotes, sfMode=sfMode, freq=freq))
        pktGenerated = pktGenerated.append(calculatePktGen(data[sys.argv[ix]], sys.argv[ix], nrMotes=nrMotes, sfMode=sfMode, freq=freq))
        DAOReceived = DAOReceived.append(calculateDAOReceived(data[sys.argv[ix]], sys.argv[ix]))

    # aggregated over all motes
    plotBoxplotSeaborn('lifetime_2000mAh_openMoteCC2538', lifetime2000OpenMoteCC2538, sorter, outputDir=outputDirAll)
    plotBoxplotSeaborn('lifetime_2000mAh_openMoteB', lifetime2000OpenMoteB, sorter, outputDir=outputDirAll)
    plotBoxplotSeaborn('sixtopMessaging', sixtopMessaging, sorter, outputDir=outputDirAll)
    stateFrequencySum = stateFrequency.groupby(['exp', 'state'])['val'].sum().reset_index() # sum all the same states per experiment
    # stateFrequencySum = stateFrequencySum[stateFrequencySum.state != 'nrIdle'] # remove the idle states
    # stateFrequencySum = stateFrequencySum[stateFrequencySum.state != 'nrSleep'] # remove the sleep states
    plotBarsSeaborn('StateFrequency', stateFrequencySum, outputDir=outputDirAll, xsplit='state')
    # plotMultipleBoxplotSeaborn('StateFrequency', stateFrequencySum, outputDir=outputDirAll, xsplit='state')

    sixtopMessagingMean = sixtopMessaging.groupby(['exp', 'type'])['val'].sum().reset_index() # sum all the same states per experiment
    plotBarsSeaborn('SixTopMessaging', sixtopMessagingMean, outputDir=outputDirAll, xsplit='type')
    plotBoxplotSeaborn('latency', latency, sorter, outputDir=outputDirAll)
    #
    # # aggregatd per iteration
    plotBoxplotSeaborn('DAOMessagingReceived', DAOReceived, sorter, outputDir=outputDirPerIteration)
    DAOMessaging = DAOMessaging.groupby(['exp', 'iteration', 'type'])['val'].mean().reset_index() # WATCH OUT: you can not just do the mean here because of the received DAOs
    # plotMultipleBoxplotSeaborn('DAOMessaging', DAOMessaging, outputDir=outputDirPerIteration, xsplit='type')
    plotBoxplotSeaborn('kbitsPerJoule_openMoteCC2538', bitsPerJouleOpenMoteCC2538, sorter, outputDir=outputDirPerIteration)
    plotBoxplotSeaborn('kbitsPerJoule_openMoteB', bitsPerJouleOpenMoteB, sorter, outputDir=outputDirPerIteration)
    plotBoxplotSeaborn('received', received, sorter, outputDir=outputDirPerIteration)
    plotBoxplotSeaborn('pktGen', pktGenerated, sorter, outputDir=outputDirPerIteration)
    plotBoxplotSeaborn('allDrops', allDrops, sorter, outputDir=outputDirPerIteration)

    # lifetime2000OpenMoteCC2538PerIteration = lifetime2000OpenMoteCC2538.groupby(['exp', 'iteration'])['val'].mean().reset_index() # take the mean of all motes in the same iteration
    # plotBoxplotSeaborn('lifetime_2000mAh_openMoteCC2538', lifetime2000OpenMoteCC2538PerIteration, sorter, outputDir=outputDirPerIteration)
    # lifetime2000OpenMoteBPerIteration = lifetime2000OpenMoteB.groupby(['exp', 'iteration'])['val'].mean().reset_index() # take the mean of all motes in the same iteration
    # plotBoxplotSeaborn('lifetime_2000mAh_openMoteB', lifetime2000OpenMoteBPerIteration, sorter, outputDir=outputDirPerIteration)
    # macDropsPerIteration = macDrops.groupby(['exp', 'freq', 'iteration'])['val'].sum().reset_index()
    # plotBoxplotSeaborn('macDrops', macDropsPerIteration, sorter, outputDir=outputDirPerIteration)
    # queueDropsPerIteration = queueDrops.groupby(['exp', 'freq', 'iteration'])['val'].sum().reset_index()
    # plotBoxplotSeaborn('queueDrops', queueDropsPerIteration, sorter, outputDir=outputDirPerIteration)

    # plotMultipleBoxplotSeaborn('latency', latencyPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='modeC')
    # plotMultipleBoxplotSeaborn('received', received, sorter, outputDir=outputDirPerIteration, xsplit='motes', hue='sfmode')
    # plotBars('DAOMessaging', DAOMessaging, None, outputDir=outputDir)

    if resultType == 'resfModes':
        latencyPerIteration = latency.groupby(['exp', 'freq', 'modeC', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('latency', latencyPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='modeC', xlabel='Traffic')
    elif resultType == 'collisionAvoidance':
        latencyPerIteration = latency[latency.sfMode != 'None'] # remove the idle states
        latencyPerIteration = latency.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('latency', latencyPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        pktGenPerIteration = pktGenerated.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('pktGen', pktGenPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        receivedPerIteration = received.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('received', receivedPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        allDropsPerIteration = allDrops.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('allDrops', allDropsPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        lifetime2000OpenMoteCC2538PerIteration = lifetime2000OpenMoteCC2538.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('lifetime_2000mAh_openMoteCC2538', lifetime2000OpenMoteCC2538PerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        lifetime2000OpenMoteBPerIteration = lifetime2000OpenMoteB.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('lifetime_2000mAh_openMoteB', lifetime2000OpenMoteBPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
    elif resultType == 'normal' or resultType == 'sporadic':
        latencyPerIteration = latency[latency.sfMode != 'None'] # remove the idle states
        latencyPerIteration = latency.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('latency', latencyPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode', xlabel='Traffic')
        pktGenPerIteration = pktGenerated.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('pktGen', pktGenPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        pktArrivedToGenPerIteration = pktArrivedToGenerated.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('pktArrivedToGen', pktArrivedToGenPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        receivedPerIteration = received.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('received', receivedPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        allDropsPerIteration = allDrops.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('allDrops', allDropsPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        lifetime2000OpenMoteCC2538PerIteration = lifetime2000OpenMoteCC2538.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('lifetime_2000mAh_openMoteCC2538', lifetime2000OpenMoteCC2538PerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
        lifetime2000OpenMoteBPerIteration = lifetime2000OpenMoteB.groupby(['exp', 'freq', 'sfMode', 'iteration'])['val'].mean().reset_index()
        plotMultipleBoxplotSeaborn('lifetime_2000mAh_openMoteB', lifetime2000OpenMoteBPerIteration, sorter, outputDir=outputDirPerIteration, xsplit='freq', hue='sfMode')
    elif resultType == 'other':
        assert False