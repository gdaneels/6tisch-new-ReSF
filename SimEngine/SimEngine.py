#!/usr/bin/python
"""
\brief Discrete-event simulation engine.

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>
\author Kazushi Muraoka <k-muraoka@eecs.berkeley.edu>
\author Nicola Accettura <nicola.accettura@eecs.berkeley.edu>
\author Xavier Vilajosana <xvilajosana@eecs.berkeley.edu>
"""

#============================ logging =========================================

import random
import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('SimEngine')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

#============================ imports =========================================

import threading

import Propagation
import Topology
import Mote
import SimSettings
import ReSFEngine
import numpy as np
import math
import copy

#============================ defines =========================================

#============================ body ============================================

class SimEngine(threading.Thread):

    #===== start singleton
    _instance      = None
    _init          = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SimEngine,cls).__new__(cls, *args, **kwargs)
        return cls._instance
    #===== end singleton

    def __init__(self, cpuID=None, runNum=None, failIfNotInit=False):

        if failIfNotInit and not self._init:
            raise EnvironmentError('SimEngine singleton not initialized.')

        #===== start singleton
        if self._init:
            return
        self._init = True
        #===== end singleton

        # store params
        self.cpuID                          = cpuID
        self.runNum                         = runNum

        self.rect1 = (0.0, 0.9, 3.0, 1.1)
        self.rect2 = (2.0, 1.9, 5.0, 2.1)
        self.rect3 = (0.0, 2.9, 3.0, 3.1)
        self.rect4 = (2.0, 3.9, 5.0, 4.1)

        # self.originX = 2.5 # in km
        # self.originY = 4.7 # in km
        # self.targetX = 4.5 # in km
        # self.targetY = 4.6 # in km

        # first one is the origin
        self.targets = [(4.6, 4.6), (0.9, 3.95), (4.6, 2.95), (0.9, 1.95), (4.6, 0.95)]
        # self.targets = [(1.0, 3.7), (4.0, 2.7), (1.0, 1.7), (4.5, 0.5)]
        # self.targets = [(4.0, 2.7), (1.0, 1.7), (4.5, 0.5)]
        self.targetType = {}

        self.targetRadius = 0.100 # in km
        self.targetPos = {} # dict: mote -> (x, y) relative to workingTargetX
        self.targetIndex = {}
        self.margin = 0.02
        self.goalDistanceFromTarget = 0.01

        # local variables
        self.dataLock                       = threading.RLock()
        self.pauseSem                       = threading.Semaphore(0)
        self.simPaused                      = False
        self.goOn                           = True
        self.asn                            = 0
        self.startCb                        = []
        self.endCb                          = []
        self.events                         = []
        self.settings                       = SimSettings.SimSettings()
        random.seed(self.settings.seed)
        np.random.seed(self.settings.seed)
        self.genMobility = random.Random()
        self.genMobility.seed(self.settings.seed)
        self.propagation                    = Propagation.Propagation()
        self.ReSFEngine                     = None
        if self.settings.sf == 'resf':
            self.ReSFEngine                 = ReSFEngine.ReSFEngine()
        self.motes                          = [Mote.Mote(id) for id in range(self.settings.numMotes)]
        self.topology                       = Topology.Topology(self.motes)
        self.topology.createTopology()

        # Not valid values. Will be set by the last mote that converged.
        self.asnInitExperiment = 999999999
        self.asnEndExperiment = 999999999

        self.dedicatedCellConvergence = 99999999

        # # boot all motes
        # for i in range(len(self.motes)):
        #     self.motes[i].boot()

        self.motes[0].boot()

        # initialize parent class
        threading.Thread.__init__(self)
        self.name                           = 'SimEngine'

    def destroy(self):
        # destroy the propagation singleton
        self.propagation.destroy()

        # destroy my own instance
        self._instance                      = None
        self._init                          = False

    #======================== thread ==========================================

    def getTrafficPeriod(self):
        pick = -1.0
        trafficAverage = self.settings.pkPeriod
        trafficStd = trafficAverage / 4
        while pick <= 0.0:
            pick = np.random.normal(trafficAverage, trafficStd, None)
            if pick < trafficAverage:
                pick = math.ceil(pick)
            else:
                pick = math.floor(pick)
        return pick

    def run(self):
        """ event driven simulator, this thread manages the events """

        # log
        log.info("thread {0} starting".format(self.name))

        # schedule the endOfSimulation event if we are not simulating the join process
        if not self.settings.withJoin:
            if not self.settings.convergeFirst:
                self.scheduleAtAsn(
                    asn         = self.settings.slotframeLength*self.settings.numCyclesPerRun,
                    cb          = self._actionEndSim,
                    uniqueTag   = (None,'_actionEndSim'),
                )
            else:
                self.scheduleAtAsn(
                    asn         = self.settings.slotframeLength*self.settings.maxToConverge,
                    cb          = self._actionEndSim,
                    uniqueTag   = (None,'_actionEndSim'),
                )

        if self.settings.trafficGenerator == 'pick':
            periods = None
            if self.settings.trafficFrequency == 'short':
                periods = [200, 400, 600] # 3s, 6s, 9s
            elif self.settings.trafficFrequency == 'medium':
                periods = [2000, 3000, 4000] # 30s, 45s, 60s
            elif self.settings.trafficFrequency == 'long':
                periods = [20000, 30000, 40000] # 5 min (300s), 7.5 min (450s), 10 min (600s)

            # periods = [200, 500, 1000, 3000, 6000, 12000]
            # periods = [200, 400, 600, 800, 1000]
            # periods = [200]
            # slotduration = 0.015, [3.0, 7.5, 15.0, 45.0, 90.0, 180.0] seconds
            # slotduration = 0.010, [2.0, 5.0, 10.0, 30.0, 60.0, 120.0] seconds
            for m in self.motes:
                if m.id > 0:
                    m.startApp = random.randint(0, 6000)
                    m.pkPeriod = periods[random.randint(0, len(periods)-1)] * float(self.settings.slotDuration)
                    log.info("Mote {0}, theoretical start delay = {1}, period = {2}.".format(m.id, m.startApp, m.pkPeriod))

            sporadics = [4000, 6000, 8000]
            for m in self.motes:
                if m.id > 0:
                    m.sporadic = sporadics[random.randint(0, len(sporadics)-1)] * float(self.settings.slotDuration)
                    m.sporadicStart = random.randint(0, 2000)
                    log.info("Mote {0}, sporadic sending first = {1}.".format(m.id, m.sporadic))
        elif self.settings.trafficGenerator == 'normal':
            for m in self.motes:
                if m.id > 0:
                    m.startApp = random.randint(0, 6000)
                    m.pkPeriod = self.getTrafficPeriod()
                    log.info("Mote {0},  theoretical start delay = {1}, period = {2}.".format(m.id, m.startApp, m.pkPeriod))
        else:
            assert False


        if self.settings.mobilityModel == 'RPGM':
            for m in range(0, self.settings.numMotes):
                self.targetPos[m] = (
                self.targets[1][0] + self.genMobility.uniform((-1.0 * self.targetRadius) + 0.005, self.targetRadius - 0.005),
                self.targets[1][1] + self.genMobility.uniform((-1.0 * self.targetRadius) + 0.005, self.targetRadius - 0.005))
                self.targetIndex[m] = 1
                self.targetType[m] = 'up'

        # call the start callbacks
        for cb in self.startCb:
            cb()

        # for m in self.motes:
        #     log.info(
        #         "[topology] shortest mote to {0} is {1}.".format(m.id, m.closestNeighbor.id),
        #     )

        # consume events until self.goOn is False
        while self.goOn:

            with self.dataLock:

                # abort simulation when no more events
                if not self.events:
                    log.info("end of simulation at ASN={0}".format(self.asn))
                    break

                # make sure we are in the future
                (a, b, cb, c) = self.events[0]
                if c[1] != '_actionPauseSim':
                    assert self.events[0][0] >= self.asn

                # update the current ASN
                self.asn = self.events[0][0]

                # if self.asn == 10000:
                #     self._actionPauseSim()

                interval = 4
                newCycle = int(self.getAsn() / self.settings.slotframeLength)
                index = newCycle / interval
                if newCycle % interval == 0 and index < len(self.motes) and self.motes[index].isJoined == False:
                    self.motes[index].boot()
                    log.info("Booting node {0}".format(index))

                if self.asn % self.settings.slotframeLength == 0:
                    # rdm = self.propagation.print_random()
                    # log.info("topology random={0}".format(rdm))
                    log.info("[6top] ----------- SLOTFRAME BEGIN -----------")

                # only start moving when the experiment started, there is a mobility model and do it at the beginning of every cycle
                if self.asn > self.asnInitExperiment and self.settings.mobilityModel != 'none' and self.asn % self.settings.slotframeLength == 0:
                    if self.settings.mobilityModel == 'RWM': # random walk model
                        for m in self.motes:
                            if m.id != 0:
                                m.updateLocation()
                    elif self.settings.mobilityModel == 'RPGM':
                        for m in self.motes:
                            m.updateLocation()
                    self.topology.updateTopology()
                    for m in self.motes:
                        m._tsch_updateMinimalCells() # update the neighbors of the minimal cells

                if self.settings.sf == 'resf':
                    self.ReSFEngine.action()

                # call callbacks at this ASN
                while True:
                    if self.events[0][0]!=self.asn:
                        break
                    (_,_,cb,_) = self.events.pop(0)
                    cb()

        # call the end callbacks
        for cb in self.endCb:
            cb()

        # log
        log.info("thread {0} ends".format(self.name))

    #======================== public ==========================================

    # called when there is dedicated cell or ReSF convergence
    def startSending(self):

        if self.settings.sf == 'resf':
            # this is called when ReSF reservations all arrived at root

            assert self.dedicatedCellConvergence != 99999999
            # offset until the end of the cycle where the dedicated cell convergence happened, just as we do with the other SFs
            offset = self.settings.slotframeLength - (self.dedicatedCellConvergence % self.settings.slotframeLength)

            for m in self.motes:
                if m.id > 0:
                    delay = (offset + m.startApp)
                    log.info("Current ASN: {0}".format(self.asn))
                    log.info("Mote {0} would theoretically (convergence + offset + delay start) start at ASN {1}, period of {2}.".format(m.id, self.dedicatedCellConvergence + delay, m.pkPeriod))

                    startTransmission = self.dedicatedCellConvergence + delay
                    while startTransmission <= self.asn:
                        startTransmission += int(m.pkPeriod / float(self.settings.slotDuration))
                    log.info("Mote {0}, will start at ASN {1}, period of {2}.".format(m.id, startTransmission,
                                                                                      int(m.pkPeriod / float(
                                                                                          self.settings.slotDuration))))

                    # delay *= float(self.settings.slotDuration)
                    # schedule the transmission of the first packet
                    self.scheduleAtAsn(
                        asn=startTransmission,
                        cb=m._app_action_sendSinglePacket,
                        uniqueTag=(m.id, '_app_action_sendSinglePacket'),
                        priority=2,
                    )
                    if self.settings.sporadicTraffic == 1:
                        self.scheduleAtAsn(
                            asn=startTransmission + m.sporadicStart,
                            cb=m._app_action_sendSporadicPacket,
                            uniqueTag=(m.id, '_app_action_sendSporadicPacket'),
                            priority=2,
                        )
        else:
            # offset until the end of the current cycle
            offset = self.settings.slotframeLength - (self.asn % self.settings.slotframeLength)
            for m in self.motes:
                if m.id > 0:
                    delay = (offset + m.startApp)
                    log.info("Mote {0}, will start at ASN {1}, period of {2}.".format(m.id, self.getAsn()+delay, m.pkPeriod))
                    delay *= float(self.settings.slotDuration)
                    # schedule the transmission of the first packet
                    self.scheduleIn(
                        delay=delay,
                        cb=m._app_action_sendSinglePacket,
                        uniqueTag=(m.id, '_app_action_sendSinglePacket'),
                        priority=2,
                    )
                    if self.settings.sporadicTraffic == 1:
                        self.scheduleIn(
                            delay=delay + (m.sporadicStart*float(self.settings.slotDuration)),
                            cb=m._app_action_sendSporadicPacket,
                            uniqueTag=(m.id, '_app_action_sendSporadicPacket'),
                            priority=2,
                        )


    def checkValidPosition(self, xcoord, ycoord, countSquare=True, placement=False):
        '''
        Checks if a given postition is valid when moving
        '''

        margin = self.margin
        if placement:
            margin = 0.02

        inSquare = False  # total area
        insideObstacle1 = False  # rectangle 1
        insideObstacle2 = False  # rectangle 2
        insideObstacle3 = False  # rectangle 1
        insideObstacle4 = False  # rectangle 2
        if countSquare:
            if (xcoord < self.settings.squareSide and ycoord < self.settings.squareSide) and (
                    xcoord > 0 and ycoord > 0):
                inSquare = True
        else:
            inSquare = True

        if (xcoord < (self.rect1[2] + margin)) and (ycoord > (self.rect1[1] - margin) and (ycoord < (self.rect1[3] + margin))):
            insideObstacle1 = True
        if (xcoord > (self.rect2[0] - margin)) and (ycoord > (self.rect2[1] - margin) and (ycoord < (self.rect2[3] + margin))):
            insideObstacle2 = True
        if (xcoord < (self.rect3[2] + margin)) and (ycoord > (self.rect3[1] - margin) and (ycoord < (self.rect3[3] + margin))):
            insideObstacle3 = True
        if (xcoord > (self.rect4[0] - margin)) and (ycoord > (self.rect4[1] - margin) and (ycoord < (self.rect4[3] + margin))):
            insideObstacle4 = True

        if inSquare and not insideObstacle1 and not insideObstacle2 and not insideObstacle3 and not insideObstacle4:
            return True
        else:
            return False

    #=== scheduling

    def scheduleAtStart(self,cb):
        with self.dataLock:
            self.startCb    += [cb]

    def scheduleIn(self,delay,cb,uniqueTag=None,priority=0,exceptCurrentASN=True):
        """ used to generate events. Puts an event to the queue """

        with self.dataLock:
            asn = int(self.asn+(float(delay)/float(self.settings.slotDuration)))

            self.scheduleAtAsn(asn,cb,uniqueTag,priority,exceptCurrentASN)

    def scheduleAtAsn(self,asn,cb,uniqueTag=None,priority=0,exceptCurrentASN=True):
        """ schedule an event at specific ASN """

        # make sure we are scheduling in the future
        assert asn>self.asn

        # remove all events with same uniqueTag (the event will be rescheduled)
        if uniqueTag:
            self.removeEvent(uniqueTag,exceptCurrentASN)

        with self.dataLock:

            # find correct index in schedule
            i = 0
            while i<len(self.events) and (self.events[i][0]<asn or (self.events[i][0]==asn and self.events[i][1]<=priority)):
                i +=1

            # add to schedule
            self.events.insert(i,(asn,priority,cb,uniqueTag))

    def removeEvent(self,uniqueTag,exceptCurrentASN=True):
        with self.dataLock:
            i = 0
            while i<len(self.events):
                if self.events[i][3]==uniqueTag and not (exceptCurrentASN and self.events[i][0]==self.asn):
                    self.events.pop(i)
                    if uniqueTag[0] == 3 and uniqueTag[1] == '_msf_action_parent_change_retransmission':
                        self.motes[3]._log(
                            Mote.INFO,
                            '[6top] Actual retransmission event is being removed...',
                        )
                    if uniqueTag[0] == 3 and uniqueTag[1] == '_msf_action_parent_change_removal':
                        self.motes[3]._log(
                            Mote.INFO,
                            '[6top] Actual removal event is being removed...',
                        )
                else:
                    i += 1

    def scheduleAtEnd(self,cb):
        with self.dataLock:
            self.endCb      += [cb]

    # === misc

    #delay in asn
    def terminateSimulation(self,delay):
        self.asnEndExperiment = self.asn + delay
        self.scheduleAtAsn(
                asn         = self.asn+delay,
                cb          = self._actionEndSim,
                uniqueTag   = (None,'_actionEndSim'),
        )

    #=== play/pause

    def play(self):
        self._actionResumeSim()

    def pauseAtAsn(self,asn):
        if not self.simPaused:
            self.scheduleAtAsn(
                asn         = asn,
                cb          = self._actionPauseSim,
                uniqueTag   = ('SimEngine','_actionPauseSim'),
            )

    #=== getters/setters

    def getAsn(self):
        return self.asn

    #======================== private =========================================

    def _actionPauseSim(self):
        if not self.simPaused:
            self.simPaused = True
            self.pauseSem.acquire()

    def _actionResumeSim(self):
        if self.simPaused:
            self.simPaused = False
            self.pauseSem.release()

    def _actionEndSim(self):
        with self.dataLock:
            self.goOn = False
