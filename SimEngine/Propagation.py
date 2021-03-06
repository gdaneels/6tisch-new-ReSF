#!/usr/bin/python
"""
\brief Wireless propagation model.

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>
\author Kazushi Muraoka <k-muraoka@eecs.berkeley.edu>
\author Nicola Accettura <nicola.accettura@eecs.berkeley.edu>
\author Xavier Vilajosana <xvilajosana@eecs.berkeley.edu>
"""

#============================ logging =========================================

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('Propagation')
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())

#============================ imports =========================================

import threading
import random
import math
from abc import ABCMeta, abstractmethod

import Topology
import SimSettings
import SimEngine
import Mote

#============================ defines =========================================

#============================ functions =======================================

def _dBmTomW(dBm):
    """ translate dBm to mW """
    return math.pow(10.0, dBm / 10.0)


def _mWTodBm(mW):
    """ translate dBm to mW """
    return 10 * math.log10(mW)

#============================ classes =========================================

class Propagation(object):

    def __new__(cls, *args, **kwargs):
        """
        This method instantiates the proper `Propagate` class given the simulator settings.
        :return: a Propagate class depending on the settings
        :rtype: PropagationFromModel | PropagationFormTrace
        """
        settings = SimSettings.SimSettings()
        if hasattr(settings, "scenario"):
            return PropagationFromTrace()
        else:
            return PropagationFromModel()


class PropagationCreator(object):
    """
    This class is a meta class, it is not mean to be instantiated.
    """

    __metaclass__ = ABCMeta

    #===== start singleton
    _instance      = None
    _init          = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PropagationCreator,cls).__new__(cls, *args, **kwargs)
        return cls._instance
    #===== end singleton

    def __init__(self):
        #===== start singleton
        # don't re-initialize an instance (needed because singleton)
        if self._init:
            return
        self._init = True
        #===== end singleton

        # store params
        self.settings                  = SimSettings.SimSettings()
        self.engine                    = SimEngine.SimEngine()

        # random.seed(self.settings.seed)

        self.genPropagation = random.Random()
        self.genPropagation.seed(self.settings.seed)

        # variables
        self.dataLock                  = threading.Lock()
        self.receivers                 = [] # motes with radios currently listening
        self.transmissions             = [] # ongoing transmissions

        # schedule propagation task
        self._schedule_propagate()

    def destroy(self):
        self._instance                 = None
        self._init                     = False

    #======================== public ==========================================

    #===== communication

    def print_random(self):
        return self.genPropagation.random()

    def startRx(self,mote,channel):
        """ add a mote as listener on a channel"""
        with self.dataLock:
            self.receivers += [{
                'mote':                mote,
                'channel':             channel,
            }]

    def startTx(self,channel,type,code,smac,dmac,srcIp,dstIp,srcRoute, payload):
        """ add a mote as using a channel for tx"""
        with self.dataLock:
            self.transmissions  += [{
                'channel':             channel,
                'type':                type,
                'code':                code,
                'smac':                smac,
                'dmac':                dmac,
                'srcIp':               srcIp,
                'dstIp':               dstIp,
                'sourceRoute':         srcRoute,
                'payload':             payload,
            }]

    @abstractmethod
    def propagate(self):
        """ Simulate the propagation of pkts in a slot. """
        raise NotImplementedError

    #======================== private =========================================

    def _schedule_propagate(self):
        with self.dataLock:
            self.engine.scheduleAtAsn(
                asn         = self.engine.getAsn()+1,# so propagation happens in next slot
                cb          = self.propagate,
                uniqueTag   = (None,'propagation'),
                priority    = 1,
            )

# ==================== Propagation From Model =================================

class PropagationFromModel(PropagationCreator):
    def propagate(self):
        """ Simulate the propagation of pkts in a slot. """

        with self.dataLock:

            asn   = self.engine.getAsn()
            ts    = asn % self.settings.slotframeLength

            arrivalTime = {}

            # store arrival times of transmitted packets
            for transmission in self.transmissions:
                arrivalTime[transmission['smac']] = transmission['smac'].clock_getOffsetToDagRoot()

            for transmission in self.transmissions:

                i           = 0 # index of a receiver
                isACKed     = False
                isNACKed    = False

                while i<len(self.receivers):

                    if self.receivers[i]['channel']==transmission['channel']:
                        # this receiver is listening on the right channel

                        if self.receivers[i]['mote'] in transmission['dmac']:
                            # this packet is destined for this mote

                            if not self.settings.noInterference:

                                #================ with interference ===========

                                # other transmissions on the same channel?
                                interferers = [t['smac'] for t in self.transmissions if (t!=transmission) and (t['channel']==transmission['channel'])]

                                interferenceFlag = 0
                                for itfr in interferers:
                                    if self.receivers[i]['mote'].getRSSI(itfr)>self.receivers[i]['mote'].minRssi:
                                        interferenceFlag = 1

                                transmission['smac'].schedule[ts]['debug_interference'] += [interferenceFlag] # debug only

                                if interferenceFlag:
                                    transmission['smac'].stats_incrementRadioStats('probableCollisions')
                                if transmission['smac'].schedule[ts]['dir'] == Mote.DIR_TXRX_SHARED:
                                    if interferenceFlag:
                                        transmission['smac'].stats_sharedCellCollisionSignal()
                                    else:
                                        transmission['smac'].stats_sharedCellSuccessSignal()

                                lockOn = transmission['smac']
                                for itfr in interferers:
                                    if arrivalTime[itfr] < arrivalTime[lockOn] and self.receivers[i]['mote'].getRSSI(itfr)>self.receivers[i]['mote'].minRssi:
                                        # lock on interference
                                        lockOn = itfr

                                if lockOn == transmission['smac']:
                                    # mote locked in the current signal

                                    transmission['smac'].schedule[ts]['debug_lockInterference'] += [0] # debug only

                                    # calculate pdr, including interference
                                    sinr  = self._computeSINR(transmission['smac'],self.receivers[i]['mote'],interferers)
                                    pdr   = self._computePdrFromSINR(sinr, self.receivers[i]['mote'])

                                    # pick a random number
                                    failure = self.genPropagation.random()
                                    if pdr>=failure:
                                        # packet is received correctly
                                        # this mote is delivered the packet
                                        # print '---------'
                                        # print 'ok - pdr %.4f - receiver %d - failure %.4f - smac.id %d' % (pdr, self.receivers[i]['mote'].id, failure, transmission['smac'].id)
                                        isACKed, isNACKed = self.receivers[i]['mote'].radio_rxDone(
                                            type       = transmission['type'],
                                            code       = transmission['code'],
                                            smac       = transmission['smac'],
                                            dmac       = transmission['dmac'],
                                            srcIp      = transmission['srcIp'],
                                            dstIp      = transmission['dstIp'],
                                            srcRoute   = transmission['sourceRoute'],
                                            payload    = transmission['payload']
                                        )
                                        # this mote stops listening
                                        del self.receivers[i]

                                    else:
                                        # print '---------'
                                        # print 'not ok - pdr %.4f - receiver %d - failure %.4f - smac.id %d' % (pdr, self.receivers[i]['mote'].id, failure, transmission['smac'].id)
                                        # packet is NOT received correctly
                                        self.receivers[i]['mote'].radio_rxDone()
                                        del self.receivers[i]

                                else:
                                    # mote locked in an interfering signal

                                    # for debug
                                    transmission['smac'].schedule[ts]['debug_lockInterference'] += [1]

                                    # receive the interference as if it's a desired packet
                                    interferers.remove(lockOn)
                                    pseudo_interferers = interferers + [transmission['smac']]

                                    # calculate SINR where locked interference and other signals are considered S and I+N respectively
                                    pseudo_sinr  = self._computeSINR(lockOn,self.receivers[i]['mote'],pseudo_interferers)
                                    pseudo_pdr   = self._computePdrFromSINR(pseudo_sinr, self.receivers[i]['mote'])

                                    # pick a random number
                                    failure = self.genPropagation.random()
                                    if pseudo_pdr>=failure and self.receivers[i]['mote'].radio_isSync():
                                        # success to receive the interference and realize collision
                                        self.receivers[i]['mote'].schedule[ts]['rxDetectedCollision'] = True

                                    # desired packet is not received
                                    self.receivers[i]['mote'].radio_rxDone()
                                    del self.receivers[i]

                            else:

                                #================ without interference ========

                                interferers = []

                                transmission['smac'].schedule[ts]['debug_interference']     += [0] # for debug only
                                transmission['smac'].schedule[ts]['debug_lockInterference'] += [0] # for debug only

                                # calculate pdr with no interference
                                sinr  = self._computeSINR(transmission['smac'],self.receivers[i]['mote'],interferers)
                                pdr   = self._computePdrFromSINR(sinr, self.receivers[i]['mote'])

                                # pick a random number
                                failure = self.genPropagation.random()

                                if pdr>=failure:
                                    # packet is received correctly

                                    # this mote is delivered the packet
                                    isACKed, isNACKed = self.receivers[i]['mote'].radio_rxDone(
                                        type       = transmission['type'],
                                        code       = transmission['code'],
                                        smac       = transmission['smac'],
                                        dmac       = transmission['dmac'],
                                        srcIp      = transmission['srcIp'],
                                        dstIp      = transmission['dstIp'],
                                        srcRoute   = transmission['sourceRoute'],
                                        payload    = transmission['payload']
                                    )

                                    # this mote stops listening
                                    del self.receivers[i]

                                else:
                                    # packet is NOT received correctly
                                    self.receivers[i]['mote'].radio_rxDone()
                                    del self.receivers[i]

                        else:
                            # this packet is NOT destined for this mote

                            # move to the next receiver
                            i += 1

                    else:
                        # this receiver is NOT listening on the right channel

                        # move to the next receiver
                        i += 1

                # indicate to source packet was sent
                transmission['smac'].radio_txDone(isACKed, isNACKed)

            # remaining receivers that does not receive a desired packet
            for r in self.receivers:

                if not self.settings.noInterference:

                    #================ with interference ===========

                    interferers = [t['smac'] for t in self.transmissions if t['dmac']!=r['mote'] and t['channel']==r['channel']]

                    lockOn = None
                    for itfr in interferers:

                        if not lockOn:
                            if r['mote'].getRSSI(itfr)>r['mote'].minRssi:
                                lockOn = itfr
                        else:
                            if r['mote'].getRSSI(itfr)>r['mote'].minRssi and arrivalTime[itfr]<arrivalTime[lockOn]:
                                lockOn = itfr

                    if lockOn:
                        # pdr calculation

                        # receive the interference as if it's a desired packet
                        interferers.remove(lockOn)

                        # calculate SINR where locked interference and other signals are considered S and I+N respectively
                        pseudo_sinr  = self._computeSINR(lockOn,r['mote'],interferers)
                        pseudo_pdr   = self._computePdrFromSINR(pseudo_sinr,r['mote'])

                        # pick a random number
                        failure = self.genPropagation.random()
                        if pseudo_pdr>=failure and r['mote'].radio_isSync():
                            # success to receive the interference and realize collision
                            r['mote'].schedule[ts]['rxDetectedCollision'] = True

                # desired packet is not received
                r['mote'].radio_rxDone()

            # clear all outstanding transmissions
            self.transmissions              = []
            self.receivers                  = []

        self._schedule_propagate()

    # ======================== static =========================================

    @staticmethod
    def _computeSINR(source, destination, interferers):
        """ compute SINR  """

        noise = _dBmTomW(destination.noisepower)
        # S = RSSI - N
        signal = _dBmTomW(source.getRSSI(destination)) - noise
        if signal < 0.0:
            # RSSI has not to be below noise level. If this happens, return very low SINR (-10.0dB)
            return -10.0

        totalInterference = 0.0
        for interferer in interferers:
            # I = RSSI - N
            interference = _dBmTomW(interferer.getRSSI(destination)) - noise
            if interference < 0.0:
                # RSSI has not to be below noise level. If this happens, set interference 0.0
                interference = 0.0
            totalInterference += interference

        sinr = signal / (totalInterference + noise)

        return _mWTodBm(sinr)

    @staticmethod
    def _computePdrFromSINR(sinr, destination):
        """ compute PDR from SINR """

        equivalentRSSI = _mWTodBm(
            _dBmTomW(sinr + destination.noisepower) +
            _dBmTomW(destination.noisepower)
        )

        pdr = Topology.Topology.rssiToPdr(equivalentRSSI)

        return pdr

# ==================== Propagation From Trace =================================

class PropagationFromTrace(PropagationCreator):
    def propagate(self):
        """ Simulate the propagation of pkts in a slot. """
        raise NotImplementedError
