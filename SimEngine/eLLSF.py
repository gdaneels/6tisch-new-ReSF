#!/usr/bin/python
'''
\brief Implementation of the eLLSF scheduling function.

\author Glenn Daneels <glenn.daneels@uantwerpen.be>
'''

#============================ logging =========================================

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('eLLSF')
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())

#============================ imports =========================================

import random
import math

import SimEngine
import SimSettings
import Mote

from collections import OrderedDict

class eLLSF(object):
    
    DEBUG                              = 'DEBUG'
    INFO                               = 'INFO'
    WARNING                            = 'WARNING'
    ERROR                              = 'ERROR'
    
    # ELLSF_TIMESLOTS                    = [10, 11, 12, 13, 14, 15, 20, 25, 30, 40, 50, 55, 60, 70, 80, 85, 90, 95, 96, 97, 98, 99, 100]
    ELLSF_TIMESLOTS                    = [8, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    ELLSF_PERIOD                       = 101

    def __init__(self, mote):
        
        self.engine                    = SimEngine.SimEngine()
        self.settings                  = SimSettings.SimSettings()

        self.geneLLSF = random.Random()
        self.geneLLSF.seed(self.settings.seed + mote.id)

        # random.seed(self.settings.seed)
        
        # mote on which this ReSF instance is defined 
        self.mote = mote
        
        # delayed ReSF requests, the list contains full resf request payloads
        self.delayed = []
        
        for ts in self.ELLSF_TIMESLOTS:
            if ts > (self.settings.slotframeLength - 1):
                assert False
        
        self._log(
            self.INFO,
            "[eLLSF] On mote {0}, initialized a eLLSF instance.",
            (self.mote.id,)
        )
    
    def _ellsf_reservation_request(self, neighbor, numCells, dir):
        #get blocked cells from other 6top operations
        blockedCells = []
        for n in self.mote.sixtopStates.keys():
            if n != neighbor.id:
                if 'tx' in self.mote.sixtopStates[n] and len(self.mote.sixtopStates[n]['tx']['blockedCells'])>0:
                    blockedCells += self.mote.sixtopStates[n]['tx']['blockedCells']
                if 'rx' in self.mote.sixtopStates[n] and len(self.mote.sixtopStates[n]['rx']['blockedCells'])>0:
                    blockedCells += self.mote.sixtopStates[n]['rx']['blockedCells']

        #convert blocked cells into ts
        tsBlocked=[]
        if len(blockedCells) > 0:
            for c in blockedCells:
                if c[0] in self.ELLSF_TIMESLOTS: # only consider the ones in the allowed eLLSF timeslots
                    tsBlocked.append(c[0])
        
        # get currently taken timeslots (that are allowed by eLLSF)
        currentlyScheduled = []
        for ts in self.mote.schedule:
            if ts in self.ELLSF_TIMESLOTS:
                currentlyScheduled.append(ts)

        availableTimeslots = list(set(self.ELLSF_TIMESLOTS)-set(currentlyScheduled)-set(tsBlocked))

        if self.mote.ReSF is not None and self.settings.resfBufferHousekeeping == 1:
            maxASN = self.engine.asn + (self.settings.resfHousekeepingPeriod * self.settings.slotframeLength)
            resfBlockedTimeslots = self.mote.ReSF.getBlockedTimeslots(maxASN)
            if len(resfBlockedTimeslots) > 0:
                availableTimeslots = list(set(self.ELLSF_TIMESLOTS) - set(currentlyScheduled) - set(tsBlocked) - set(resfBlockedTimeslots))

        availableTimeslots = sorted(availableTimeslots)

        # 1. find all RX timeslots, indexed by neighbor
        rxTimeslots = OrderedDict()
        if neighbor is self.mote.preferredParent:
            for ts, cell in self.mote.schedule.iteritems():
                if ts in self.ELLSF_TIMESLOTS and cell['dir'] == Mote.DIR_TXRX_SHARED and cell['neighbor'] is not self.mote.preferredParent and cell['neighbor'] is not self.mote.oldPreferredParent:
                    if cell['neighbor'] in rxTimeslots:
                        rxTimeslots[cell['neighbor']].append(ts)
                    else:
                        rxTimeslots[cell['neighbor']] = [ts]
        else: # only allow reservations to preferred parent
            assert False

        # print self.ELLSF_TIMESLOTS
        # print 'On mote %d, for neighbor %d, rxTimeslots: %s' % (self.mote.id, neighbor.id, str(rxTimeslots))

        cellList = []

        # only do the rest of ellsf if you have children and RX/SHARED cells of those children
        if len(rxTimeslots) > 0:
            # 2. look for largest gap for each neighbor
            rxGap = OrderedDict()
            for n, tsList in rxTimeslots.iteritems():
                if len(tsList) > 0: # if there actually is a gap
                    self._log(
                        self.INFO,
                        "[eLLSF] neighbor: {0}, gap: {1}",
                        (n.id, str(self._ellsf_largestGapTimeslot(sorted(tsList))))
                    )
                    rxGap[n] = self._ellsf_largestGapTimeslot(sorted(tsList))

            self._log(
                self.INFO,
                "[eLLSF] Gap per neighbor: {0}.",
                (str(rxGap),)
            )

            self._log(
                self.INFO,
                "[eLLSF] Numcells: {0}.",
                (str(numCells),)
            )
                
            # 3. distribute the cells over the neighbors and search for the actual slots for each neighbor
            rxNeighbors = rxTimeslots.keys()
            self.geneLLSF.shuffle(rxNeighbors) # random shuffle them
            cellsToReserve = min(numCells, len(availableTimeslots)) # only reserve as much as we have available
            newTimeslots = OrderedDict()
            assignedTimeslots = []
            self._log(
                self.INFO,
                "[eLLSF] Numcells: {0}, availableTimeslots {1}",
                (str(numCells), str(availableTimeslots))
            )

            while cellsToReserve > 0 and len(rxTimeslots.keys()) > 0:
                for rxNeighbor in rxNeighbors:
                    if cellsToReserve > 0:
                        newTimeslot = self._ellsf_nextAvailableSlot(rxGap[rxNeighbor], assignedTimeslots, availableTimeslots)
                        assert newTimeslot is not None # this should never happen, programmed to not happen
                        if rxNeighbor not in newTimeslots:
                            newTimeslots[rxNeighbor] = [newTimeslot]
                        else:
                            newTimeslots[rxNeighbor].append(newTimeslot)
                        cellsToReserve -= 1

            # 4. make cells from timeslots
            for rxNeighbor in newTimeslots:
                for ts in newTimeslots[rxNeighbor]:
                    cellList.append((ts, self.geneLLSF.randint(0, self.settings.numChans - 1), dir))

            self._log(
                self.INFO,
                "[eLLSF] CellList: {0}.",
                (str(cellList),)
            )

        else: # do the normal random strategy
            self._log(
                self.INFO,
                "[eLLSF] Shuffle it.",
                (self.mote.id,)
            )
            self.geneLLSF.shuffle(availableTimeslots)
            cells                 = dict([(ts, self.geneLLSF.randint(0, self.settings.numChans - 1)) for ts in availableTimeslots[:min(numCells, len(availableTimeslots))]])
            cellList              = [(ts, ch, dir) for (ts, ch) in cells.iteritems()]
            cellList += [(999, 999, Mote.DIR_TXRX_SHARED)]

        return cellList

    def _ellsf_find_tx_slots(self):
        txTimeslots = []
        for ts, cell in self.mote.schedule.iteritems():
            if ts in self.ELLSF_TIMESLOTS and cell['dir'] == Mote.DIR_TXRX_SHARED and \
                    cell['neighbor'] is self.mote.preferredParent and \
                    cell['neighbor'] is not self.mote.oldPreferredParent:
                txTimeslots.append(ts)
        return txTimeslots

    def _ellsf_find_closest_to_tx(self, txslots, cellList):
        distances = []
        for t in txslots:
            for c in cellList:
                diff = t - c[0]
                # print 'diff: %d from %d - %d' % (diff, t, c[0])
                if diff > 0:
                    distances.append((c, abs(diff)))
                elif diff < 0:
                    diff = (self.settings.slotframeLength - c[0]) + t
                    distances.append((c, diff))
                else:
                    assert False
                # print 'new diff: %d from %d - %d' % (diff, t, c[0])
        sorted_distances = sorted(distances, key=lambda x: x[1]) # WATCH OUT can contain duplicates
        return sorted_distances

    def _ellsf_receive_request(self, neighbor, numCells, newDir, cellList):
        #get blocked cells from other 6top operations
        blockedCells = []
        for n in self.mote.sixtopStates.keys():
            if n!=neighbor.id:
                if 'rx' in self.mote.sixtopStates[n] and len(self.mote.sixtopStates[n]['rx']['blockedCells'])>0:
                    blockedCells+=self.mote.sixtopStates[n]['rx']['blockedCells']
                if 'tx' in self.mote.sixtopStates[n] and len(self.mote.sixtopStates[n]['tx']['blockedCells'])>0:
                    blockedCells+=self.mote.sixtopStates[n]['tx']['blockedCells']
                    
        #convert blocked cells into ts
        tsBlocked=[]
        if len(blockedCells)>0:
            for c in blockedCells:
                if c[0] in self.ELLSF_TIMESLOTS: # only consider the ones in the allowed eLLSF timeslots
                    tsBlocked.append(c[0])
                    
        currentlyScheduled = []
        for ts in self.mote.schedule:
            if ts in self.ELLSF_TIMESLOTS:
                currentlyScheduled.append(ts)
        
        # IMPORTANT for eLLSF we HAVE to keep the order
        availableTimeslots = list(set(self.ELLSF_TIMESLOTS)-set(currentlyScheduled)-set(tsBlocked))

        if self.mote.ReSF is not None and self.settings.resfBufferHousekeeping == 1:
            maxASN = self.engine.asn + (self.settings.resfHousekeepingPeriod * self.settings.slotframeLength)
            resfBlockedTimeslots = self.mote.ReSF.getBlockedTimeslots(maxASN)
            if len(resfBlockedTimeslots) > 0:
                availableTimeslots = list(set(self.ELLSF_TIMESLOTS)-set(currentlyScheduled)-set(tsBlocked) - set(resfBlockedTimeslots))

        availableTimeslots = sorted(availableTimeslots)

        # newCellList = []
        # # available timeslots on this mote
        # for (ts, ch, dir) in cellList:
        #     if len(newCellList) == numCells:
        #         break
        #     if ts in availableTimeslots:
        #         newCellList += [(ts, ch, newDir)]
        # #
        newCellList = []
        if self.mote.id == 0 or (999,999, Mote.DIR_TXRX_SHARED) not in cellList:
            if (999,999, Mote.DIR_TXRX_SHARED) in cellList:
                cellList.remove((999,999, Mote.DIR_TXRX_SHARED))
            # available timeslots on this mote
            for (ts, ch, dir) in cellList:
                if len(newCellList) == numCells:
                    break
                if ts in availableTimeslots:
                    newCellList += [(ts, ch, newDir)]
        else:
            if (999,999, Mote.DIR_TXRX_SHARED) in cellList:
                cellList.remove((999,999, Mote.DIR_TXRX_SHARED))
            tsSlots = self._ellsf_find_tx_slots()
            cellListTmp = []
            for (ts, ch, dir) in cellList:
                if ts in availableTimeslots:
                    cellListTmp.append((ts, ch, dir))
            cellList = cellListTmp
            l = self._ellsf_find_closest_to_tx(tsSlots, cellList)
            for ((ts, ch, dir), diff) in l:
                if len(newCellList) == numCells:
                    break
                if ts in availableTimeslots and (ts, ch, newDir) not in newCellList:
                    newCellList += [(ts, ch, newDir)]

        # if neighbor.id == 2 and self.mote.id == 1:
        #     # print self.ELLSF_TIMESLOTS
        #     print cellList
        #     # print availableTimeslots
        #     # print newCellList
        #     print newCellList
        #     # print self._ellsf_find_tx_slots()
        #     print self._ellsf_find_closest_to_tx(self._ellsf_find_tx_slots(), cellList)
        #     assert False

        #  if len(newCellList) < numCells it is considered still a success as long as len(newCellList) is bigger than 0
        if len(newCellList) <= 0:
            returnCode = Mote.IANA_6TOP_RC_NORES # not enough resources
        else: 
            returnCode = Mote.IANA_6TOP_RC_SUCCESS # enough resources

        #set blockCells for this 6top operation
        self.mote.sixtopStates[neighbor.id]['rx']['blockedCells'] = newCellList

        return newCellList, returnCode
    
    def _ellsf_removeCells(self):
        pass
    
    def _ellsf_nextAvailableSlot(self, gapSlot, blockedSlots, availableTimeslots):
        ''' assumption is here that availableSlots is sorted '''
        smallerTimeslot = None
        for ts in availableTimeslots:
            if gapSlot < ts and ts not in blockedSlots: # first one after gapSlot is okay
                blockedSlots.append(ts)
                return ts
            elif ts < gapSlot and ts not in blockedSlots and (smallerTimeslot is None or ts < smallerTimeslot):
                smallerTimeslot = ts
        
        if smallerTimeslot is not None:
            blockedSlots.append(smallerTimeslot)
        return smallerTimeslot
        
    
    def _ellsf_largestGapTimeslot(self, tsList):
        if len(tsList) == 1:
            return tsList[0]
        listOfTuples = [(x,y) for (x, y) in zip(tsList[1:], tsList[:-1])] 
        diff = (self.settings.slotframeLength - max(tsList)) + min(tsList) # this is the difference between the smallest value and the largest value in the previous slot frame
        largestGapTimeslot = min(tsList)
        for tp in listOfTuples:
            if tp[0] - tp[1] > diff:
                diff = tp[0] - tp[1]
                largestGapTimeslot = tp[0]
        return largestGapTimeslot 

    def _log(self,severity,template,params=()):
        
        if severity==self.DEBUG:
            if not log.isEnabledFor(logging.DEBUG):
                return
            logfunc = log.debug
        elif severity==self.INFO:
            if not log.isEnabledFor(logging.INFO):
                return
            logfunc = log.info
        elif severity==self.WARNING:
            if not log.isEnabledFor(logging.WARNING):
                return
            logfunc = log.warning
        elif severity==self.ERROR:
            if not log.isEnabledFor(logging.ERROR):
                return
            logfunc = log.error
        else:
            raise NotImplementedError()
        
        output  = []
        output += ['[ASN={0:>6} id={1:>4}] '.format(self.engine.getAsn(),self.mote.id)]
        output += [template.format(*params)]
        output  = ''.join(output)
        logfunc(output)
        