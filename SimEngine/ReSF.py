#!/usr/bin/python
'''
\brief Implementation of the ReSF scheduling function.

\author Glenn Daneels <glenn.daneels@uantwerpen.be>
'''

#============================ logging =========================================

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('ReSF')
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())

#============================ imports =========================================

import copy
import random
import math
from fractions import gcd

import SimEngine
import SimSettings
import Solver
import Mote
import ReSFEngine

from collections import OrderedDict
from collections import namedtuple

IDOriginator = namedtuple("IDOriginator", ["unique_id", "neighbor"])

RESF_PREFPARENT = 'RESF_PREFPARENT'
RESF_THISPARENT = 'RESF_THISPARENT'

class ReSF(object):
    
    DEBUG                              = 'DEBUG'
    INFO                               = 'INFO'
    WARNING                            = 'WARNING'
    ERROR                              = 'ERROR'
    
    RESF_NEW                           = 'RESF_NEW'
    RESF_UPDATE                        = 'RESF_UPDATE'
    RESF_OUTDATED                      = 'RESF_OUTDATED'
    RESF_DUPLICATE                     = 'RESF_DUPLICATE'

    RESF_FOUND                         = 'RESF_FOUND'
    RESF_NOT_FOUND                     = 'RESF_NOT_FOUND'

    MAX_RESERVATIONS                   = 64
    MAX_ALLOWED_RESERVATIONS           = 4

    MAX_BADLINK_DELETES                = 1 # putting it to 0 means you will not retry

    def __init__(self, mote):

        # mote on which this ReSF instance is defined
        self.mote = mote

        self.engine                    = SimEngine.SimEngine()
        self.settings                  = SimSettings.SimSettings()
        self.genReSF = random.Random()
        self.genReSF.seed(self.settings.seed + self.mote.id)
        random.seed(self.settings.seed + self.mote.id)
        
        self.txTuples = OrderedDict()
        self.rxTuples = OrderedDict()
        self.txBlockedTuples = OrderedDict()
        self.rxBlockedTuples = OrderedDict()

        self.txDeleteTuples = OrderedDict()

        # keeps track per neighbor node how many ReSF DELETE messages were delayed because of a bad link
        self.badLinkDeletes = {}

        # delayed ReSF requests, the list contains full resf request payloads
        self.delayed = []

        # list of ReSF converged motes, managed by the root node? Did its reservation arrive at the root?
        self.resf_converged = []
        # used for SimStats statistics convergence
        self.resfReachedRoot = {}

        # max number of periods for when a cell is not used by a child, the reservation is removed
        self.keepAliveMAX = 30
        # keep alive dictionary: mapping the unique id to the usage of the reservation
        self.keepAlive = {}

        self._log(
            self.INFO,
            "[ReSF] On mote {0}, initialized a ReSF instance.",
            (self.mote.id,)
        )
        
        # ReSF reservation tuple
        self.tuple = {}

        # var indicates if extra backup cells are already allocated
        self.allocated = {}

        self.giveReSFPriority = False

        self.avgQueue = []

        ### statistics ###
        # number of cells this node wants to allocate more
        self.toAllocateCells = 0
        # number of cells that were actually added to the schedule
        self.haveAllocatedCells = 0

        self.ReSFEngine                     = None
        if self.settings.sf == 'resf':
            self.ReSFEngine                 = ReSFEngine.ReSFEngine()
    
    def _app_action_ReSFReservation(self):
        
        self._log(
            self.DEBUG,
            "[app - ReSF] On mote {0}, preparing a new ReSF reservation.",
            (self.mote.id,)
        )
        
        # check delayed reservation requests, remove the ones which refer to the same uniqueId
        # self.delayed = [reservation for reservation in self.delayed if self.engine.ReSFEngine.tuples[self.mote.id]['uniqueId'] != reservation['uniqueId']]
        
        # calulcate list of reservations based on original tuple
        reservationList = self._resf_calc_request(self.engine.ReSFEngine.tuples[self.mote.id])
        # print reservationList
        # print self.engine.ReSFEngine.tuples[self.mote.id]
        # assert False
        # required resf cells to reserve on the link to the parent
        reqNrCells = self._resf_calcReqNrCells()

        self._resf_reservationRequest(self.engine.ReSFEngine.tuples[self.mote.id]['uniqueId'], reservationList, reqNrCells, copy.deepcopy(self.engine.ReSFEngine.tuples[self.mote.id]))

    def _resf_reservationRequest(self, uniqueId, reservationList, reqNrCells, reservationBase):
        # build ReSF payload
        payload = {}
        payload['uniqueId'] = uniqueId
        payload['reservationList'] = reservationList
        payload['reqNrCells'] = reqNrCells
        payload['timestamp'] = reservationList[0]['timestamp'] # you can take whatever timestamp, they should all be the same

        # for delayed requests, they can use this field to restart their calculation of the necessary reservations
        payload['reservationBase'] = reservationBase

        timeout = self.mote._msf_get_sixtop_timeout(self.mote.preferredParent)

        # this block checks if there we are trying to send out an old reservation
        # for neighbor, rList in self.txTuples.iteritems():
        #     for reservation in rList:
        #         if payload['uniqueId'] == reservation['uniqueId'] and payload['timestamp'] <= reservation['timestamp']:
        #             assert False
        
        # this block will remove all other reservations that are in the delayed list
        # if a newer one is found, assert
        self.tmpDelayed = []
        for t in self.delayed: # tuple of (type, resf)
            if t[0] == 'add':
                if payload['uniqueId'] != t[1]['uniqueId']:
                    self.tmpDelayed.append(('add', t[1]))
                # elif payload['uniqueId'] == t[1]['uniqueId'] and payload['timestamp'] <= t[1]['timestamp']:
                #     # if we find a reservation that newer which is already in the delayed list, assert because that is weird
                #     assert False
            elif t[0] == 'delete': # just re-add deletes
                self.tmpDelayed.append(('delete', t[1]))
            else:
                assert False
        self.delayed = self.tmpDelayed
    
        # we can fill all parameters except numCells we should put to 0
        self.mote._sixtop_cell_reservation_request(self.mote.preferredParent, 0, Mote.DIR_TX, timeout, payload)

    def _resf_scheduleDelayedRequest(self, delay=1):
        ''' Schedule a new check for sending a delayed ReSF request in the next ASN. '''
        
        self.engine.scheduleAtAsn(
            asn=int(self.engine.asn + delay),
            cb=self._resf_actionDelayedRequest,
            uniqueTag=(self.mote.id, '_resf_actionDelayedRequest'),
            priority=4,
        )

        self._log(
            self.INFO,
            '[ReSF] scheduled a new delayed request check'
        )

    def _resf_find_uniqueId_timestamp(self, uniqueId, timestamp, dir):
        if dir == Mote.DIR_TX:
            for n in self.txTuples:
                for t in self.txTuples[n]:
                    if uniqueId == t['uniqueId'] and timestamp == t['timestamp']:
                        return True
        elif dir == Mote.DIR_RX:
            for n in self.rxTuples:
                for r in self.rxTuples[n]:
                    if uniqueId == r['uniqueId'] and timestamp == r['timestamp']:
                        return True
        else:
            assert False  # resf does not support any other direction types

        return False

    def _resf_find_oldParent(self, uniqueId, timestamp, dir):
        if dir == Mote.DIR_TX:
            for n in self.txTuples:
                for t in self.txTuples[n]:
                    if uniqueId == t['uniqueId'] and timestamp == t['timestamp']:
                        return n
        elif dir == Mote.DIR_RX:
            for n in self.rxTuples:
                for r in self.rxTuples[n]:
                    if uniqueId == r['uniqueId'] and timestamp == r['timestamp']:
                        return n
        else:
            assert False  # resf does not support any other direction types

        return None

    def _resf_actionDelayedRequest(self):
        if len(self.delayed) > 0:
            resf = self.delayed.pop(0) # get first inserted delayed request
            if resf[0] == 'add':
                resf[1]['reqNrCells'] = self._resf_calcReqNrCells() # recalculate the number of required cells
                resf[1]['reservationList'] = self._resf_calc_request(resf[1]['reservationBase'])

                timeout = self.mote._msf_get_sixtop_timeout(self.mote.preferredParent)

                # we can fill all parameters except numCells we should put to 0
                self.mote._sixtop_cell_reservation_request(self.mote.preferredParent, 0, Mote.DIR_TX, timeout, resf[1])
            elif resf[0] == 'delete':
                if resf[1]['parent_type'] == RESF_PREFPARENT:
                    self._resf_send_delete(copy.deepcopy(resf[1]['tuples']), RESF_PREFPARENT)
                elif resf[1]['parent_type'] == RESF_THISPARENT:
                    self._resf_send_delete(copy.deepcopy(resf[1]['tuples']), RESF_THISPARENT, resf[1]['parent_id'])

    def _resf_find_lcm(self, numbers):
        lcm = numbers[0]
        for i in numbers[1:]:
            lcm = lcm * i / gcd(lcm, i)
        return lcm

    def _resf_find_start_max(self, starts):
        start_max = starts[0]
        for i in starts[1:]:
            if i > start_max:
                start_max = i
        return start_max

    def _resf_calc_request(self, reservation):
        solver = Solver.CollisionSolver()
        starts = []
        periods = []

        # only when we restrict the ellsf part of resf to certain locations, add these backup locations
        if self.settings.ellsfMode == 'restricted' or self.settings.ellsfMode == 'halfrestricted':
            for ellsf_slot in self.mote.eLLSF.ELLSF_TIMESLOTS:
                starts.append(ellsf_slot)
                periods.append(self.mote.eLLSF.ELLSF_PERIOD)

        for n, l_resv in self.txTuples.iteritems():
            for resv in l_resv:
                starts.append(resv['start'])
                periods.append(resv['period'])

        for n, l_resv in self.rxTuples.iteritems():
            for resv in l_resv:
                starts.append(resv['start'])
                periods.append(resv['period'])

        for n, resfObject in self.txBlockedTuples.iteritems():
            if len(resfObject) > 0: # txBlockedTuples can only contain one reservationList dict per neighbor, if so: len(dict) > 0
                for resv in resfObject['reservationList']:
                    starts.append(resv['start'])
                    periods.append(resv['period'])

        for n, resfObject in self.rxBlockedTuples.iteritems():
            if len(resfObject) > 0: # rxBlockedTuples can only contain one reservationList dict per neighbor, if so: len(dict) > 0
                for resv in resfObject['reservationList']:
                    starts.append(resv['start'])
                    periods.append(resv['period'])

        resv_to_collisions = []

        for r in range(0, self.MAX_RESERVATIONS):
            tmp_resv = {}
            tmp_resv['uniqueId'] = reservation['uniqueId']
            tmp_resv['channel'] = self.genReSF.randint(0, 15)
            tmp_resv['start'] = reservation['start'] + r
            tmp_resv['next'] = reservation['next'] + r
            tmp_resv['period'] = reservation['period']
            tmp_resv['timestamp'] = reservation['timestamp']

            # find the LCM
            lcm = self._resf_find_lcm([tmp_resv['period']] + periods)
            # find the maximum start
            start_max = self._resf_find_start_max([tmp_resv['start']] + starts)
            # define the end
            end = start_max + lcm

            uniqueCollisions = set()
            totalNrCollisions = 0
            collisionCounter = 0
            maxValue = 0
            # go over every reseration that has to be checked
            for ix, start in enumerate(starts):
                if self.settings.resfMode == 'optimal':
                    tmpUniqueCollisions = solver.getCollisions(tmp_resv['start'], tmp_resv['period'], start, periods[ix], start_max, end, unique=True)
                    if tmpUniqueCollisions != []:
                        uniqueCollisions = uniqueCollisions.union(set(tmpUniqueCollisions))
                elif self.settings.resfMode == 'random' or self.settings.resfMode == 'minimaldelay':
                    pass
                elif self.settings.resfMode == 'sum':
                    nrColls = solver.getCollisions(tmp_resv['start'], tmp_resv['period'], start, periods[ix], start_max,
                                                 end, unique=False)
                    if nrColls != []:
                        totalNrCollisions += nrColls
                elif self.settings.resfMode == 'average':
                    nrColls = solver.getCollisions(tmp_resv['start'], tmp_resv['period'], start, periods[ix], start_max,
                                                 end, unique=False)
                    if nrColls != []:
                        totalNrCollisions += nrColls
                        collisionCounter += 1
                elif self.settings.resfMode == 'sort':
                    nrColls = solver.getCollisions(tmp_resv['start'], tmp_resv['period'], start, periods[ix], start_max,
                                                 end, unique=False)
                    if nrColls != []:
                        if nrColls > maxValue:
                            maxValue = nrColls
                        totalNrCollisions += nrColls

            if self.settings.resfMode == 'optimal':
                resv_to_collisions.append((copy.deepcopy(tmp_resv), len(uniqueCollisions)))
            elif self.settings.resfMode == 'sum':
                resv_to_collisions.append((copy.deepcopy(tmp_resv), totalNrCollisions))
            elif self.settings.resfMode == 'random' or self.settings.resfMode == 'minimaldelay':
                resv_to_collisions.append(copy.deepcopy(tmp_resv))
            elif self.settings.resfMode == 'average':
                if collisionCounter > 0:
                    resv_to_collisions.append((copy.deepcopy(tmp_resv), totalNrCollisions / float(collisionCounter)))
                else:
                    resv_to_collisions.append((copy.deepcopy(tmp_resv), 0.0))
            elif self.settings.resfMode == 'sort':
                resv_to_collisions.append((copy.deepcopy(tmp_resv), maxValue, totalNrCollisions))
            else:
                assert False

        resv_list = []
        # sort the list, based on the number of collisions
        if self.settings.resfMode == 'optimal' or self.settings.resfMode == 'sum' or self.settings.resfMode == 'average':
            resv_list = [r[0] for r in sorted(resv_to_collisions, key=lambda x: (x[1], x[0]['start']))]
        elif self.settings.resfMode == 'sort':
            resv_list = [r[0] for r in sorted(resv_to_collisions, key=lambda x: (x[1], x[2]))]
        elif self.settings.resfMode == 'random':
            self.genReSF.shuffle(resv_to_collisions)
            resv_list = [r for r in resv_to_collisions]
        elif self.settings.resfMode == 'minimaldelay':
            resv_list = [r for r in sorted(resv_to_collisions, key=lambda x: x['start'])]

        # cut off the list at the MAX_ALLOWED_RESERVATIONS
        resv_list = resv_list[:self.MAX_ALLOWED_RESERVATIONS]
        # sort the list, based on the start time
        # sorted(resv_list, key=lambda x: x['start'])

        assert len(resv_list) == self.MAX_ALLOWED_RESERVATIONS

        return resv_list

        # newReservation = {}
        # newReservation['channel'] = 5
        # newReservation['start'] = reservation['start']
        # newReservation['period'] = reservation['period']
        # newReservation['next'] = reservation['next']
        # newReservation['uniqueId'] = reservation['uniqueId']
        # newReservation['timestamp'] = reservation['timestamp']
        #
        # newReservation1 = {}
        # newReservation1['channel'] = 5
        # newReservation1['start'] = reservation['start'] + 1
        # newReservation1['period'] = reservation['period']
        # newReservation1['next'] = reservation['next'] + 1
        # newReservation1['uniqueId'] = reservation['uniqueId']
        # newReservation1['timestamp'] = reservation['timestamp']
        #
        # newReservation2 = {}
        # newReservation2['channel'] = 5
        # newReservation2['start'] = reservation['start'] + 2
        # newReservation2['period'] = reservation['period']
        # newReservation2['next'] = reservation['next'] + 2
        # newReservation2['uniqueId'] = reservation['uniqueId']
        # newReservation2['timestamp'] = reservation['timestamp']
        #
        # newReservation3 = {}
        # newReservation3['channel'] = 5
        # newReservation3['start'] = reservation['start'] + 3
        # newReservation3['period'] = reservation['period']
        # newReservation3['next'] = reservation['next'] + 3
        # newReservation3['uniqueId'] = reservation['uniqueId']
        # newReservation3['timestamp'] = reservation['timestamp']
        # return [newReservation, newReservation1, newReservation2, newReservation3]

    def _resf_calc_response(self, received_resv_list):
        solver = Solver.CollisionSolver()
        starts = []
        periods = []

        # only when we restrict the ellsf part of resf to certain locations, add these backup locations
        if self.settings.ellsfMode == 'restricted' or self.settings.ellsfMode == 'halfrestricted':
            for ellsf_slot in self.mote.eLLSF.ELLSF_TIMESLOTS:
                starts.append(ellsf_slot)
                periods.append(self.mote.eLLSF.ELLSF_PERIOD)

        for n, l_resv in self.txTuples.iteritems():
            for resv in l_resv:
                starts.append(resv['start'])
                periods.append(resv['period'])

        for n, l_resv in self.rxTuples.iteritems():
            for resv in l_resv:
                starts.append(resv['start'])
                periods.append(resv['period'])

        for n, resfObject in self.txBlockedTuples.iteritems():
            if len(resfObject) > 0:  # txBlockedTuples can only contain one reservationList dict per neighbor, if so: len(dict) > 0
                for resv in resfObject['reservationList']:
                    starts.append(resv['start'])
                    periods.append(resv['period'])
                    # if resv['period'] == 400:
                    #     assert False

        for n, resfObject in self.rxBlockedTuples.iteritems():
            if len(resfObject) > 0:  # rxBlockedTuples can only contain one reservationList dict per neighbor, if so: len(dict) > 0
                for resv in resfObject['reservationList']:
                    starts.append(resv['start'])
                    periods.append(resv['period'])
                    # if resv['period'] == 400:
                    #     assert False

        resv_to_collisions = []

        for r in received_resv_list:
            # find the LCM
            lcm = self._resf_find_lcm(periods + [r['period']])
            # find the maximum start
            start_max = self._resf_find_start_max(starts + [r['start']])
            # define the end
            end = start_max + lcm

            uniqueCollisions = set()
            totalNrCollisions = 0
            collisionCounter = 0
            maxValue = 0
            # go over every reseration that has to be checked
            for ix, start in enumerate(starts):
                if self.settings.resfMode == 'optimal':
                    tmpUniqueCollisions = solver.getCollisions(r['start'], r['period'], start,
                                                               periods[ix], start_max, end, unique=True)
                    if tmpUniqueCollisions != []:
                        # print '**** START ****'
                        # print 'r[\'start\'] %.4f' % r['start']
                        # print 'r[\'period\'] %.4f' % r['period']
                        # print 'start %.4f' % start
                        # print 'periods[ix] %.4f' % periods[ix]
                        # print 'start_max %.4f' % start_max
                        # print 'periods %s' % periods
                        # print 'lcm %.4f' % lcm
                        # print 'end %.4f' % end
                        # print '**** STOP ****'
                        uniqueCollisions = uniqueCollisions.union(set(tmpUniqueCollisions))
                elif self.settings.resfMode == 'sum':
                    nrColls = solver.getCollisions(r['start'], r['period'], start, periods[ix], start_max,
                                                   end, unique=False)
                    if nrColls != []:
                        totalNrCollisions += nrColls
                elif self.settings.resfMode == 'random' or self.settings.resfMode == 'minimaldelay':
                    pass
                elif self.settings.resfMode == 'average':
                    nrColls = solver.getCollisions(r['start'], r['period'], start, periods[ix], start_max,
                                                   end, unique=False)
                    if nrColls != []:
                        totalNrCollisions += nrColls
                        collisionCounter += 1
                elif self.settings.resfMode == 'sort':
                    nrColls = solver.getCollisions(r['start'], r['period'], start, periods[ix], start_max,
                                                   end, unique=False)
                    if nrColls != []:
                        if nrColls > maxValue:
                            maxValue = nrColls
                        totalNrCollisions += nrColls

            if self.settings.resfMode == 'optimal':
                resv_to_collisions.append((copy.deepcopy(r), len(uniqueCollisions)))
            elif self.settings.resfMode == 'sum':
                resv_to_collisions.append((copy.deepcopy(r), totalNrCollisions))
            elif self.settings.resfMode == 'random' or self.settings.resfMode == 'minimaldelay':
                resv_to_collisions.append(copy.deepcopy(r))
            elif self.settings.resfMode == 'average':
                if collisionCounter > 0:
                    resv_to_collisions.append((copy.deepcopy(r), totalNrCollisions / float(collisionCounter)))
                else:
                    resv_to_collisions.append((copy.deepcopy(r), 0.0))
            elif self.settings.resfMode == 'sort':
                resv_to_collisions.append((copy.deepcopy(r), maxValue, totalNrCollisions))
            else:
                assert False

        # sort the list, based on the number of collisions
        if self.settings.resfMode == 'optimal' or self.settings.resfMode == 'sum' or self.settings.resfMode == 'average':
            resv_list = [r[0] for r in sorted(resv_to_collisions, key=lambda x: (x[1], x[0]['start']))]
        elif self.settings.resfMode == 'sort':
            resv_list = [r[0] for r in sorted(resv_to_collisions, key=lambda x: (x[1], x[2]))]
        elif self.settings.resfMode == 'random':
            self.genReSF.shuffle(resv_to_collisions)
            resv_list = [r for r in resv_to_collisions]
        elif self.settings.resfMode == 'minimaldelay':
            resv_list = [r for r in sorted(resv_to_collisions, key=lambda x: x['start'])]

        return resv_list

    def _resf_calcReqNrCells(self):
        etx = self.mote._estimateETX(self.mote.preferredParent)
        if etx > Mote.RPL_MAX_ETX:
            etx = Mote.RPL_MAX_ETX
        elif self.settings.mobilityModel != 'none' and etx is None:
            # if there is mobility it is possible that the ETX (PDR) changed from the moment it changed parent
            # until the moment now that the new ReSF reservations are actually sent
            # so in this case, take the default one
            etx = Mote.RPL_MAX_ETX

        # extraCells = self.settings.extraBackup

        # pdr = self.mote.getPDR(self.mote.preferredParent)
        # if pdr >= 0.95:
        #     extraCells = 0
        # elif 0.8 <= pdr < 0.95:
        #     extraCells = 1
        # elif 0.65 <= pdr < 0.8:
        #     extraCells = 2
        # else:
        #     extraCells = 3

        # return (int(math.ceil(etx)) + extraCells)
        # return 1
        return (int(math.ceil(etx)))
    
    def _resf_receive_ADD_REQUEST(self, neighbor, reqPayload):
        numCells = min(reqPayload['reqNrCells'], len(reqPayload['reservationList']))
        # sort based on collisions --> cut off to numCells --> sort on start
        sorted_resv_list = sorted(self._resf_calc_response(reqPayload['reservationList'])[:numCells], key=lambda r: r['start'])

        payload = {}
        payload['uniqueId'] = reqPayload['uniqueId']
        payload['reservationList'] = sorted_resv_list
        payload['reqNrCells'] = numCells
        payload['timestamp'] = reqPayload['reservationList'][0]['timestamp'] # you can take whatever timestamp, they should all be the same

        # these become the ReSF blocked tuples
        self.rxBlockedTuples[neighbor] = reqPayload

        return payload
    
    def _resf_receive_RESPONSE(self, neighbor, receivedDir, resf):
        # set direction of cells
        newDir = None
        if receivedDir == Mote.DIR_TX:
            newDir = Mote.DIR_RX
        elif receivedDir == Mote.DIR_RX:
            newDir = Mote.DIR_TX
        else: # should not happen with ReSF
            assert False

        if self._resf_isFound(resf['uniqueId'], Mote.DIR_TX) == self.RESF_FOUND:
            # self._resf_removeTuples(newDir, resf['uniqueId'], neighbor)
            self._resf_removeTuples(newDir, resf['uniqueId'])
            self._log(
                self.INFO,
                '[ReSF] updated ReSF reservation from {0} to {1} (at sender side, {3}):\r\n{2}',
                (self.mote.id, neighbor.id, str(resf), newDir),
            )
        else:
            self._log(
                self.INFO,
                '[ReSF] add ReSF reservation from {0} to {1} (at sender side, {3}):\r\n{2}',
                (self.mote.id, neighbor.id, str(resf), newDir),
            )
        
        # if the start time already passed, calculate the new 'next' value.
        # this should happen in the reservation, not in a copy of the iteration
        endOfSlotframe = ((self.engine.getAsn() / self.settings.slotframeLength) * self.settings.slotframeLength) + self.settings.slotframeLength - 1 
        for reservation in resf['reservationList']:
            next = int(math.ceil((self.engine.getAsn() - reservation['start']) / float(reservation['period'])))
            if reservation['next'] <= endOfSlotframe:
                if (reservation['start'] + reservation['period'] * next) > endOfSlotframe:
                    reservation['next'] = reservation['start'] + reservation['period'] * next
                else:
                    reservation['next'] = reservation['start'] + reservation['period'] * (next + 1)

        # for the keep-alive policy
        if newDir == Mote.DIR_TX:
            found = None
            if int(resf['uniqueId'].split('_')[0]) == self.mote.id: # if the reservation comes from this mote
                found = self.mote.id
            else: # if it originates from another mote
                for n in self.rxTuples:
                    if found is not None: # if it has been found
                        break
                    for rxTuple in self.rxTuples[n]:
                        # TODO: I THINK THIS STATEMENT IS WRONG: YOU CAN ONLY HAVE ONE UNIQUE_ID IN YOUR RXTUPLES, SO YOU DO NOT HAVE TO CHECK TIMESTAMP
                        # if rxTuple['uniqueId'] == resf['uniqueId'] and rxTuple['timestamp'] == resf['timestamp']:
                        #     # also the timestamp should be checked otherwise it could be confused with newer updates
                        if rxTuple['uniqueId'] == resf['uniqueId']:
                            # also the timestamp should be checked otherwise it could be confused with newer updates
                            found = n.id
                            break
            if found is None:
                # assert False # this should not happen, which means that there is no RX reservation anymore for this TX reservation...
                # INFO
                # if there is no RX reservation anymore for this TX reservation, answer negatively to this response
                # the cause is probably because a delete request came in after this reservation request was sent out and that
                # delete request already deleted those reservations...
                return False # ignore the packet.

            # save the origNeighbor
            for reservation in resf['reservationList']:
                reservation['origNeighbor'] = found

        self._resf_addTuples(neighbor, newDir, resf)
        return True

    def _resf_receive_RESPONSE_ACK(self, neighbor, dir, resf):
        if self._resf_isFound(resf['uniqueId'], Mote.DIR_RX) == self.RESF_FOUND:
            # self._resf_removeTuples(dir, resf['uniqueId'], neighbor)
            self._resf_removeTuples(dir, resf['uniqueId'])
            self._log(
                self.INFO,
                '[ReSF] updated ReSF reservation from {0} to {1} (at receiver side, {3}):\r\n{2}',
                (self.mote.id, neighbor.id, str(resf), dir),
            )
        else:
            self._log(
                self.INFO,
                '[ReSF] add ReSF reservation from {0} to {1} (at receiver side, {3}):\r\n{2}',
                (self.mote.id, neighbor.id, str(resf), dir),
            )

        # if the start time already passed, calculate the new 'next' value.
        # this should happen in the reservation, not in a copy of the iteration
        endOfSlotframe = ((self.engine.getAsn() / self.settings.slotframeLength) * self.settings.slotframeLength) + self.settings.slotframeLength - 1 
        for reservation in resf['reservationList']:
            next = int(math.ceil((self.engine.getAsn() - reservation['start']) / float(reservation['period'])))
            if reservation['next'] <= endOfSlotframe:
                if (reservation['start'] + reservation['period'] * next) > endOfSlotframe:
                    reservation['next'] = reservation['start'] + reservation['period'] * next
                else:
                    reservation['next'] = reservation['start'] + reservation['period'] * (next + 1)

        # Add from where the reservation should be coming.
        for reservation in resf['reservationList']:
            reservation['origNeighbor'] = neighbor.id

        self._resf_addTuples(neighbor, dir, resf)

        # clear this for sure here, so the when calculating tuples for a forward ReSF messages the blocked but not used
        # rx tuples are not used
        del self.rxBlockedTuples[neighbor]

        if not self.mote.dagRoot: # forward the request
            self._resf_forward(resf)
        else:
            self._log(
                self.INFO,
                "[ReSF] ReSF reservation {0} arrived at DAG root.",
                (resf['uniqueId'],)
            )
            # only initial reservations should be considered for resf convergence
            # updates shoud not be considered
            if resf['timestamp'] == 0:
                orig_mote_id = resf['uniqueId'].split('_')[0]
                # used for SimStats
                self.resfReachedRoot[orig_mote_id] = self.engine.getAsn()
                self._resf_converged(orig_mote_id)

    def _resf_receive_DELETE_RESPONSE(self, neighbor, receivedDir, resf):
        self._log(
            self.INFO,
            "[ReSF] Received (at sender) ReSF DELETE response from neighbor {0} for ReSF contents: {1}.",
            (neighbor.id, resf)
        )

        # remove all the tuples in TX direction
        for t in resf['tuples']:
            uniqueId = t[0]
            timestamp = t[1]
            self._resf_removeTuplesTimestamp(Mote.DIR_TX, uniqueId, timestamp)

        # clean up the bad link deletes
        if neighbor.id in self.badLinkDeletes:
            del self.badLinkDeletes[neighbor.id]
            # TODO: this has to be deleted, I think.
            # self.delayed.append(('delete', resf))

    def _resf_receive_DELETE_RESPONSE_ACK(self, neighbor, dir, resf):
        self._log(
            self.INFO,
            "[ReSF] Received (at receiver) ReSF DELETE ACK response from neighbor {0} for ReSF contents: {1}.",
            (neighbor.id, resf)
        )

        # remove all the tuples in RX direction
        for t in resf['tuples']:
            uniqueId = t[0]
            timestamp = t[1]
            self._resf_removeTuplesTimestamp(Mote.DIR_RX, uniqueId, timestamp)

        if not self.mote.dagRoot: # forward the request
            # OLD INFO: forwarding should always happen to the preferred parent
            # OLD INFO: not the old parent

            # NO, should not happen to the preferred parent, but to the neighbor who owns the reservation!
            # because it can happen that the preferred parent of this node that receives the forwarded delete request is not the original parent
            # and thus does not have this reservation

            # check if all those tuples have the same original parent, if not, assert please and deal with it then
            # if all goes well, all those reservations should have the same parent
            listOfTXParents = []
            for t in resf['tuples']:
                # if self.mote.id == 3:
                #     print '--'
                #     print resf['tuples']
                #     print '--'
                #     print t
                #     print '--'
                #     print self.txTuples
                uniqueId = t[0]
                timestamp = t[1]
                # if timestamp != 0:
                #     print self.mote.id
                #     print resf['tuples']
                #     assert False
                p = self._resf_find_oldParent(uniqueId, timestamp, Mote.DIR_TX)
                if p is not None:
                    listOfTXParents.append(p.id)

            listOfTXParents = list(set(listOfTXParents))
            if len(listOfTXParents) >= 2: # if there is a difference in parent, that would be weird
                assert False

                # assert False
            #self._resf_send_delete(copy.deepcopy(resf['tuples']), RESF_PREFPARENT)
            if len(listOfTXParents) == 1:
                self._resf_send_delete(copy.deepcopy(resf['tuples']), RESF_THISPARENT, listOfTXParents[0])
            # if there is not parent in the TX, we assume it is already deleted. so ignore the forwarding

    def _resf_addTuples(self, neighbor, dir, resf):
        if dir == Mote.DIR_TX:
            if neighbor not in self.txTuples:
                # print self.txTuples
                self.txTuples[neighbor] = []
            for index in range(0, len(resf['reservationList'])):
                self.txTuples[neighbor].append(copy.deepcopy(resf['reservationList'][index]))
        elif dir == Mote.DIR_RX:
            if neighbor not in self.rxTuples:
                self.rxTuples[neighbor] = []
            for index in range(0, len(resf['reservationList'])):
                self.rxTuples[neighbor].append(copy.deepcopy(resf['reservationList'][index]))
        else:
            assert False # resf does not support any other direction types
        # self._log(
        #     self.INFO,
        #     "[ReSF] ---------- Adding these tuples: n {0}, dir {1}, resf {2}",
        #     (neighbor.id, dir, resf)
        # )
        # self._log(
        #     self.INFO,
        #     "[ReSF] rxTuples {0}",
        #     (self.rxTuples,)
        # )
        # self._log(
        #     self.INFO,
        #     "[ReSF] txTuples {0}",
        #     (self.txTuples,)
        # )

    def _resf_removeTuples(self, dir, uniqueId, neighbor=None):
        ''' 
            Remove tuples from tx or rx tuples, based on the neighbor and uniqueId.
        '''
        if neighbor is not None:
            if dir == Mote.DIR_TX:
                self.txTuples[neighbor] = [txTuple for txTuple in self.txTuples[neighbor] if txTuple['uniqueId'] != uniqueId]
            elif dir == Mote.DIR_RX:
                self.rxTuples[neighbor] = [rxTuple for rxTuple in self.rxTuples[neighbor] if rxTuple['uniqueId'] != uniqueId]
            else:
                assert False # resf does not support any other direction types
        else: # introduced this for updates from other children (due to parent changes)
            if dir == Mote.DIR_TX:
                for n in self.txTuples:
                    self.txTuples[n] = [txTuple for txTuple in self.txTuples[n] if txTuple['uniqueId'] != uniqueId]
            elif dir == Mote.DIR_RX:
                for n in self.rxTuples:
                    self.rxTuples[n] = [rxTuple for rxTuple in self.rxTuples[n] if rxTuple['uniqueId'] != uniqueId]
            else:
                assert False # resf does not support any other direction types

    def _resf_removeTuplesTimestamp(self, dir, uniqueId, timestamp, neighbor=None):
        '''
            Remove tuples from tx or rx tuples, based on the neighbor and uniqueId.
        '''
        if neighbor is not None:
            if dir == Mote.DIR_TX:
                self.txTuples[neighbor] = [txTuple for txTuple in self.txTuples[neighbor] if txTuple['uniqueId'] != uniqueId or (txTuple['uniqueId'] == uniqueId and txTuple['timestamp'] != timestamp)]
            elif dir == Mote.DIR_RX:
                self.rxTuples[neighbor] = [rxTuple for rxTuple in self.rxTuples[neighbor] if rxTuple['uniqueId'] != uniqueId or (rxTuple['uniqueId'] == uniqueId and rxTuple['timestamp'] != timestamp)]
            else:
                assert False # resf does not support any other direction types
        else: # introduced this for updates from other children (due to parent changes)
            if dir == Mote.DIR_TX:
                for n in self.txTuples:
                    self.txTuples[n] = [txTuple for txTuple in self.txTuples[n] if txTuple['uniqueId'] != uniqueId or (txTuple['uniqueId'] == uniqueId and txTuple['timestamp'] != timestamp)]
            elif dir == Mote.DIR_RX:
                for n in self.rxTuples:
                    self.rxTuples[n] = [rxTuple for rxTuple in self.rxTuples[n] if rxTuple['uniqueId'] != uniqueId or (rxTuple['uniqueId'] == uniqueId and rxTuple['timestamp'] != timestamp)]
            else:
                assert False # resf does not support any other direction types

    def _resf_removeTuplesOrigNeighbor(self, dir, uniqueId, origNeighbor):
        '''
            Remove tuples from tx or rx tuples, based on the neighbor and uniqueId.
        '''
        if dir == Mote.DIR_TX:
            for n in self.txTuples:
                self.txTuples[n] = [txTuple for txTuple in self.txTuples[n] if txTuple['uniqueId'] != uniqueId or txTuple['origNeighbor'] != origNeighbor]
        elif dir == Mote.DIR_RX:
            for n in self.rxTuples:
                self.rxTuples[n] = [rxTuple for rxTuple in self.rxTuples[n] if rxTuple['uniqueId'] != uniqueId or rxTuple['origNeighbor'] != origNeighbor]
        else:
            assert False # resf does not support any other direction types

    def _resf_forward(self, oldPayload):
        reservation = copy.deepcopy(oldPayload['reservationList'][self._resf_getIndexLatestTuple(oldPayload['reservationList'])])
        reservation['start'] += 1 # increment the next start ASN with 1
        reservation['next'] += 1 # increment the next start ASN with 1
        reservationList = self._resf_calc_request(reservation)
        reqNrCells = self._resf_calcReqNrCells()

        self._resf_reservationRequest(oldPayload['uniqueId'], reservationList, reqNrCells, copy.deepcopy(reservation))

    def _resf_allocateExtraCells(self, numCells):
        # print 'mote %d' % self.mote.id
        timeout = self.mote._msf_get_sixtop_timeout(self.mote.preferredParent)
        backupDuration = self.settings.resfBackupDuration # set the duration of the back up cells to stay alive
        self.mote._sixtop_cell_reservation_request(self.mote.preferredParent, numCells, Mote.DIR_TXRX_SHARED, timeout, backupDuration=backupDuration)

    def _resf_addCells(self, firstASN, lastASN):
        numReSFCells = 0 # number of ReSF cells in next slotframe
        uniqueIDs = []
        self.giveReSFPriority = False # put back to False
        for neighbor in self.txTuples:
            for txTuple in self.txTuples[neighbor]:
                while firstASN <= txTuple['next'] <= lastASN:
                    numReSFCells += 1
                    # self._log(
                    #     self.DEBUG,
                    #     "[ReSF] On mote {0}, adding ReSF TX cell [uniqueId = {1}, period = {2}, next = {3}], firstASN {4}, lastASN {5}.",
                    #     (self.mote.id, txTuple['uniqueId'], txTuple['period'], txTuple['next'], firstASN, lastASN)
                    # )
                    self.mote._tsch_addCells(neighbor, [(txTuple['next'] % self.settings.slotframeLength, txTuple['channel'], Mote.DIR_TX)], resf=True, resfUniqueId=txTuple['uniqueId'])
                    txTuple['next'] += txTuple['period']

        if self.settings.resfAllocateExtra == 1:
            extraAllocatedCells = 0
            if self.mote.preferredParent in self.mote.numCellsToNeighbors:
                extraAllocatedCells = self.mote.numCellsToNeighbors[self.mote.preferredParent]
            if self.settings.convergeFirst and \
                self.engine.asn >= self.engine.asnInitExperiment and \
                self.engine.asn <= self.engine.asnEndExperiment and \
                not self.mote.dagRoot:

                currentNumCells = (numReSFCells + extraAllocatedCells)
                reqNumCells = (len(self.mote.txQueue) * (int(math.ceil(self.mote._estimateETX(self.mote.preferredParent)))))

                if currentNumCells < reqNumCells:
                    # allocating extra cells to clean up packets that are lingering in the queue

                    allocateExtra = reqNumCells - currentNumCells

                    if self.mote.preferredParent.id not in self.allocated or not self.allocated[self.mote.preferredParent.id]:
                        self._log(
                            self.INFO,
                            "[ReSF] Allocating extra cells: {0} ({3} and {4}) < {1}, allocating {2} extra cells.",
                            (currentNumCells, reqNumCells, allocateExtra, numReSFCells, extraAllocatedCells),
                        )
                        # print self.allocateExtra
                        self._resf_allocateExtraCells(allocateExtra)
                        self.toAllocateCells += allocateExtra
                        self.allocated[self.mote.preferredParent.id] = True
                    else:
                        self._log(
                            self.INFO,
                            "[ReSF] Should allocate extra cells: {0} < {1}, need {2} extra cells. Already allocated extra {3} cells.",
                            (currentNumCells, reqNumCells, allocateExtra, extraAllocatedCells)
                        )

        for neighbor in self.rxTuples:
            for rxTuple in self.rxTuples[neighbor]:
                while firstASN <= rxTuple['next'] <= lastASN:
                    # self._log(
                    #     self.DEBUG,
                    #     "[ReSF] On mote {0}, adding ReSF RX cell [uniqueId = {1}, period = {2}, next = {3}], firstASN {4}, lastASN {5}.",
                    #     (self.mote.id, rxTuple['uniqueId'], rxTuple['period'], rxTuple['next'], firstASN, lastASN)
                    # )
                    uniqueIDs.append(rxTuple['uniqueId'])
                    self.mote._tsch_addCells(neighbor, [(rxTuple['next'] % self.settings.slotframeLength, rxTuple['channel'], Mote.DIR_RX)], resf=True, resfUniqueId=rxTuple['uniqueId'])
                    rxTuple['next'] += rxTuple['period']
        expectedReSFpackets = len(list(set(uniqueIDs)))

        if self.settings.resfPriority == 1:
            extraAllocatedCells = 0
            if self.mote.preferredParent in self.mote.numCellsToNeighbors:
                extraAllocatedCells = self.mote.numCellsToNeighbors[self.mote.preferredParent]
            # if self.settings.convergeFirst and \
            #     self.engine.asn >= (self.engine.asnInitExperiment - int((float(self.settings.settlingTime) / float(self.settings.slotDuration)))) and \
            #     self.engine.asn <= self.engine.asnEndExperiment and \
            #     not self.mote.dagRoot:
            if not self.mote.dagRoot:

                # + 1 for safety reasons
                expectedPackets = expectedReSFpackets + len(self.mote.txQueue) + 1
                # reqNumCells = (len(self.mote.txQueue) * (int(math.ceil(self.mote._estimateETX(self.mote.preferredParent)))))
                nrReSFResources = numReSFCells

                if nrReSFResources > expectedPackets:
                    # allocating extra cells to clean up packets that are lingering in the queue
                    self.giveReSFPriority = True
                    # self._log(
                    #     self.INFO,
                    #     "[ReSF] Should give priority to ReSF: resources {0} > (ReSF Packets {1} + queued packets {2} + 1).",
                    #     (nrReSFResources, expectedReSFpackets, len(self.mote.txQueue))
                    # )
                else:
                    # self._log(
                    #     self.INFO,
                    #     "[ReSF] Should NOT give priority to ReSF: resources {0} > (ReSF Packets {1} + queued packets {2} + 1).",
                    #     (nrReSFResources, expectedReSFpackets, len(self.mote.txQueue))
                    # )
                    pass

    # def _resf_countMSFCells(self, firstASN, lastASN):
    #     numReSFCells = 0 # number of ReSF cells in next slotframe
    #     uniqueIDs = []
    #     for neighbor in self.txTuples:
    #         for txTuple in self.txTuples[neighbor]:
    #             while firstASN <= txTuple['next'] <= lastASN:
    #                 numReSFCells += 1
    #
    #     for neighbor in self.rxTuples:
    #         for rxTuple in self.rxTuples[neighbor]:
    #             while firstASN <= rxTuple['next'] <= lastASN:
    #                 uniqueIDs.append(rxTuple['uniqueId'])
    #     expectedReSFpackets = len(list(set(uniqueIDs)))

    def _resf_removeCells(self):
        for ts, cell in self.mote.schedule.items():
            if cell['resf']:
                # self._log(
                #     self.DEBUG,
                #     "[ReSF] On mote {0}, removing RESF {2} cell {1}.",
                #     (self.mote.id, ts, cell['dir'])
                # )
                del self.mote.schedule[ts]
            elif cell['backupDuration'] > 0: # if there are tempory backup cells, decrement them
                self._log(
                    self.DEBUG,
                    "[ReSF - backup] On mote {0}, decrementing backup cell {1} from {2} to {3}.",
                    (self.mote.id, ts, cell['backupDuration'], (cell['backupDuration'] - 1))
                )
                self.mote.schedule[ts]['backupDuration'] -= 1
            elif cell['backupDuration'] == 0: # if there is a temporary backup cell that needs to be removed
                self._log(
                    self.DEBUG,
                    "[ReSF - backup] On mote {0}, removing backup cell {1} with backupDuration {2}.",
                    (self.mote.id, ts, cell['backupDuration'])
                )
                if cell['neighbor'].id in self.allocated:
                    self.allocated[cell['neighbor'].id] = False
                del self.mote.schedule[ts]

    def _resf_getIndexLatestTuple(self, reservationList):
        max = None
        indexMax = None
        for index, reservation in enumerate(reservationList):
            if indexMax is None or reservation['start'] > max:
                indexMax = index
        return indexMax
        
    def _resf_delayReservation(self, resf, type='add', cause='none'):
        # check delayed reservation requests, remove the ones which refer to the same uniqueId
        # self.delayed = [reservation for reservation in self.delayed if resf['uniqueId'] != reservation['uniqueId']]

        if type == 'add':
            self.delayed.append(('add', resf))
        elif type == 'delete':
            if cause == 'badlink': # if the cause is a bad link, check how many times this happened
                id = self.mote.preferredParent.id
                if resf['parent_type'] == RESF_THISPARENT:
                    id = resf['parent_id']

                if self.MAX_BADLINK_DELETES == 0:
                    self._log(
                        self.INFO,
                        "[ReSF] Not trying to resend the ReSF DELETE because MAX_BADLINK_DELETES == 0.",
                    )
                elif id not in self.badLinkDeletes:
                    self.badLinkDeletes[id] = 1
                    self.delayed.append(('delete', resf))
                elif id in self.badLinkDeletes and self.badLinkDeletes[id] < self.MAX_BADLINK_DELETES:
                    self.badLinkDeletes[id] += 1
                    self.delayed.append(('delete', resf))
                else:
                    del self.badLinkDeletes[id]
                    # do not add anymore

            else: # if the cause is NOT a bad link, re-add it anyway
                self.delayed.append(('delete', resf))
        else:
            assert False

    def _resf_isUpdate(self, uniqueId, timestamp, dir):
        if timestamp == 0: # if time stamp is 0, it is for sure NEW
            return self.RESF_NEW

        # for neighbor, reservationList in self.txBlockedTuples.iteritems():
        #     for t in reservationList:
        #         if uniqueId == t['uniqueId'] and timestamp > t['timestamp']:
        #             return self.RESF_UPDATE
        #         elif uniqueId == t['uniqueId'] and timestamp < t['timestamp']:
        #             return self.RESF_OUTDATED
        #         elif uniqueId == t['uniqueId'] and timestamp == t['timestamp']:
        #             return self.RESF_DUPLICATE

        if dir == Mote.DIR_TX:
            for neighbor, reservationList in self.txTuples.iteritems():
                for t in reservationList:
                    if uniqueId == t['uniqueId'] and timestamp > t['timestamp']:
                        return self.RESF_UPDATE
                    elif uniqueId == t['uniqueId'] and timestamp < t['timestamp']:
                        return self.RESF_OUTDATED
                    elif uniqueId == t['uniqueId'] and timestamp == t['timestamp']:
                        return self.RESF_DUPLICATE
        
        # for neighbor, reservationList in self.rxBlockedTuples.iteritems():
        #     for t in reservationList:
        #         if uniqueId == t['uniqueId'] and timestamp > t['timestamp']:
        #             return self.RESF_UPDATE
        #         elif uniqueId == t['uniqueId'] and timestamp < t['timestamp']:
        #             return self.RESF_OUTDATED
        #         elif uniqueId == t['uniqueId'] and timestamp == t['timestamp']:
        #             return self.RESF_DUPLICATE
        # 
        if dir == Mote.DIR_RX:
            for neighbor, reservationList in self.rxTuples.iteritems():
                for t in reservationList:
                    if uniqueId == t['uniqueId'] and timestamp > t['timestamp']:
                        return self.RESF_UPDATE
                    elif uniqueId == t['uniqueId'] and timestamp < t['timestamp']:
                        return self.RESF_OUTDATED
                    elif uniqueId == t['uniqueId'] and timestamp == t['timestamp']:
                        return self.RESF_DUPLICATE

        # if the timestamp is not 0, but can not be found in one the tuple dictionaries, the original new probably never made it here, so this one is considered NEW
        # OR the incoming one is a reservation originating from a parent change at a lower (in the tree) node therefore having a timestamp > 0, but maybe not existing in this node
        if timestamp > 0:
            return self.RESF_NEW
        
        assert False

    def _resf_isFound(self, uniqueId, dir):
        if dir == Mote.DIR_TX:
            for neighbor, reservationList in self.txTuples.iteritems():
                for t in reservationList:
                    if uniqueId == t['uniqueId']:
                        return self.RESF_FOUND

        if dir == Mote.DIR_RX:
            for neighbor, reservationList in self.rxTuples.iteritems():
                for t in reservationList:
                    if uniqueId == t['uniqueId']:
                        return self.RESF_FOUND

        return self.RESF_NOT_FOUND

    def _resf_getTuple(self):
        offset = self.settings.slotframeLength - (self.engine.dedicatedCellConvergence % self.settings.slotframeLength)
        start = self.engine.getAsn() + offset + self.mote.startApp # between now and 1 minute
        start += 1 # build in some buffer slots to catch pkPeriodVar
        period = int(float(self.mote.pkPeriod)/float(self.settings.slotDuration))
        uniqueId = '%d_%d_%d' % (self.mote.id, start, period)
        self.tuple = {'start': start,  'period': period, 'next': start, 'uniqueId': uniqueId, 'timestamp': 0}
        self._log(
            self.INFO,
            "[ReSF] Tuple calculation for {0}: dedicated cell convergence = {1}, offset = {2}, startApp = {3}",
            (self.mote.id, self.engine.getAsn(), offset, self.mote.startApp)

        )

        sendRequestIndex = self.genReSF.randrange(len(self.ReSFEngine.sendReSFRequestTimes))
        sendRequestTime = self.ReSFEngine.sendReSFRequestTimes[sendRequestIndex]
        del self.ReSFEngine.sendReSFRequestTimes[sendRequestIndex]

        self._log(
            self.INFO,
            "[ReSF] Tuple for {0}: {1}, sending request at ASN {2} after this ASN {3}.",
            (self.mote.id, self.tuple, sendRequestTime, self.engine.getAsn())
        )

        self.engine.scheduleAtAsn(
            # asn         = self.engine.getAsn() + self.genReSF.randint(1, 6000), # schedule the reservation within the minute
            asn         = self.engine.getAsn() + sendRequestTime, # schedule the reservation within the minute
            cb          = self._app_action_ReSFReservation,
            uniqueTag   = (self.mote.id, '_app_action_ReSFReservation'),
            priority    = 2,
        )

        return self.tuple


    def _resf_converged(self, m):
        if self.mote.id == 0:
            if m not in self.resf_converged:
                self.resf_converged.append(int(m))
                self.resf_converged.sort()
                if len(self.resf_converged) == (self.settings.numMotes - 1): # minus 1 for the root
                    # experiment time in ASNs
                    simTime = self.settings.numCyclesPerRun * self.settings.slotframeLength
                    # offset until the end of the current cycle
                    offset = self.settings.slotframeLength - (self.engine.asn % self.settings.slotframeLength)
                    settlingTime = int((float(self.settings.settlingTime) / float(self.settings.slotDuration)))
                    # experiment time + offset
                    terminationDelay = simTime + offset + settlingTime
                    self.engine.terminateSimulation(terminationDelay)
                    self.engine.asnInitExperiment = self.engine.asn + offset + settlingTime
                    self._log(
                        self.INFO,
                        "[ReSF] All ReSF reservations arrived at DAG root.",
                    )
                    self._log(
                        self.INFO,
                        "Start experiment set at ASN {0}, end experiment at ASN {1}.",
                        (self.engine.asnInitExperiment, self.engine.asnEndExperiment)
                    )
                    # start enabling the transmissions
                    self.engine.startSending()
                else:
                    expected_motes = range(1, self.settings.numMotes)
                    missing_motes = [mote for mote in expected_motes if mote not in self.resf_converged]
                    self._log(
                        self.INFO,
                        "[ReSF] {0} ReSF reservations arrived at DAG root: {1}.",
                        (len(self.resf_converged), self.resf_converged)
                    )
                    self._log(
                        self.INFO,
                        "[ReSF] missing motes: {0}",
                        (missing_motes,)
                    )
                    self._log(
                        self.INFO,
                        "[ReSF] expected motes: {0}",
                        (expected_motes,)
                    )
            else:
                assert False # mote can only be added once to ReSF converged motes
        else:
            assert False # should only be called at the root

    def _resf_parent_change(self, oldPreferredParent):
        assert self.mote.oldPreferredParent != self.mote.preferredParent

        reservation_tuple_dict = {}
        for neighbor, reservationList in self.txTuples.iteritems():
            if neighbor == oldPreferredParent:
                for t in reservationList:
                    if t['uniqueId'] not in reservation_tuple_dict:
                        reservation_tuple_dict[t['uniqueId']] = {}
                        reservation_tuple_dict[t['uniqueId']]['uniqueId'] = t['uniqueId']
                        reservation_tuple_dict[t['uniqueId']]['start'] = t['start']
                        reservation_tuple_dict[t['uniqueId']]['period'] = t['period']
                        reservation_tuple_dict[t['uniqueId']]['timestamp'] = self.engine.asn
                    # TODO for now, base the reservation to the new parent on the next value of the old reservation to the
                    # TODO old preferred parent. This should be changed by looking at the incoming reservations with this id
                    if 'next' not in reservation_tuple_dict[t['uniqueId']] or t['next'] < reservation_tuple_dict[t['uniqueId']]['next']:
                        reservation_tuple_dict[t['uniqueId']]['next'] = t['next']

        # print reservation_tuple_dict

        for uniqueId, reservation in reservation_tuple_dict.iteritems():
            self._log(
                self.INFO,
                "[ReSF] Trying to send out an existing ReSF reservation (unique id {0}, old pref parent {1}) to a new preferred parent {2}.",
                (uniqueId, oldPreferredParent.id, self.mote.preferredParent.id)
            )

            req_nr_cells = self._resf_calcReqNrCells()
            # print req_nr_cells
            reservation_list = self._resf_calc_request(reservation)
            # print reservation_list

            self._resf_reservationRequest(uniqueId, reservation_list, req_nr_cells, copy.deepcopy(reservation))

    def _resf_get_uniqueids_timestamps(self, oldPreferredParent):
        st = set()
        for neighbor, reservationList in self.txTuples.iteritems():
            if neighbor == oldPreferredParent:
                for t in reservationList:
                    if t['uniqueId'] not in st:
                        st.add((t['uniqueId'], t['timestamp']))

        lst = list(st)
        lst = sorted(lst, key=lambda x: x[0])
        return lst

    def _resf_send_delete(self, lst_ts, parentType, parent_id=None):
        resf = {}
        p = None
        if parentType == RESF_PREFPARENT:
            resf['parent_type'] = RESF_PREFPARENT
            resf['parent_id'] = self.mote.preferredParent.id
        elif parentType == RESF_THISPARENT:
            resf['parent_type'] = RESF_THISPARENT
            resf['parent_id'] = parent_id
        resf['tuples'] = lst_ts

        assert self.engine.motes[resf['parent_id']].id == resf['parent_id']

        timeout = self.mote._msf_get_sixtop_timeout(self.engine.motes[resf['parent_id']])
        self.mote._sixtop_cell_deletion_sender(self.engine.motes[resf['parent_id']], [], Mote.DIR_TX, timeout, resf=resf)

    def _resf_reservation_used(self, originator, neighbor, uniqueId):
        # 1) check if the cell is the first cell of that reservation in the slotframe
        if originator is None or neighbor is None or uniqueId is None:
            assert False
        if (originator, neighbor, uniqueId) not in self.keepAlive:
            self.keepAlive[(originator, neighbor, uniqueId)] = None
        # shift the contents (old, new) --> (new, newer)
        self.keepAlive[(originator, neighbor, uniqueId)] = self.engine.getAsn()

    def _resf_keep_alive_housekeeping(self):
        # 1) identify what to clean up
        clean = []
        # print self.keepAlive
        for (originator, neighbor, uniqueId), t in self.keepAlive.iteritems():
            period = int(uniqueId.split('_')[2])
            if t is not None and (self.engine.getAsn() - t) > (period * self.keepAliveMAX):
                clean.append((originator, neighbor, uniqueId))

        # 2) clean up
        for (originator, neighbor, uniqueId) in clean:
            self._log(
                self.INFO,
                "[ReSF] Cleaning up old TX/RX reservations on this mote for reservation {0} coming from neighbor {1}.",
                (str(uniqueId), neighbor)
            )
            # self._log(
            #     self.INFO,
            #     "[ReSF] before::: rxTuples {0}, txTuples {1}.",
            #     (self.rxTuples, self.txTuples)
            # )
            self._resf_removeTuplesOrigNeighbor(Mote.DIR_RX, uniqueId, neighbor)
            self._resf_removeTuplesOrigNeighbor(Mote.DIR_TX, uniqueId, neighbor)
            del self.keepAlive[(originator, neighbor, uniqueId)]
            # self._log(
            #     self.INFO,
            #     "[ReSF] after::: rxTuples {0}, txTuples {1}.",
            #     (self.rxTuples, self.txTuples)
            # )

    def _resf_schedule_housekeeping(self):
        self.engine.scheduleIn(
            delay=self.settings.resfHousekeepingPeriod * (0.95 + 0.1 * self.genReSF.random()),
            cb=self._resf_action_housekeeping,
            uniqueTag=(self.mote.id, '_resf_action_housekeeping'),
            priority=4,
        )

    def _resf_action_housekeeping(self):
        """
        ReSF housekeeping: decides when to relocate cells
        """
        if self.mote.dagRoot:
            self.avgQueue = []
            return

        if  self.mote.preferredParent is None:
            # schedule next housekeeping
            self._resf_schedule_housekeeping()
            self.avgQueue = []
            return

        avg = 0
        if len(self.avgQueue) == 0:
            avg = 0
        else:
            avg = sum(self.avgQueue) / float(len(self.avgQueue))

        etxval = self.mote._estimateETX(self.mote.preferredParent)
        reqCells = math.ceil(etxval * avg)
        intReqCells = int(reqCells)

        if self.settings.sf0aggressive == 1:
        # etxval2 = self.mote._estimateETX(self.mote.preferredParent)
            reqCells = math.ceil(etxval) * avg
            intReqCells = int(math.ceil(reqCells))

        nowCells = self.mote.numCellsToNeighbors.get(self.mote.preferredParent, 0)
        self._log(
            self.INFO,
            "[ReSF] Performing ReSF housekeeping for average of the queue = {0} * ETX = {1} = {2} to int {3}, cells to pref parent = {4}",
            (avg, etxval, reqCells, intReqCells, nowCells)
        )

        cellsToAdd = 0
        if nowCells == 0 or nowCells < intReqCells:
            if intReqCells > 0:
                cellsToAdd = intReqCells - nowCells + 1/2
            else: # always add one
                cellsToAdd = 1

            # # limit it to 4
            # if cellsToAdd > 4 and self.settings.sf0aggressive == 0:
            #     cellsToAdd = 4
            # elif cellsToAdd > 4 and self.settings.sf0aggressive == 1:
            #     cellsToAdd = cellsToAdd

            # self._log(
            #     self.INFO,
            #     "[ReSF] Going to add {0} cells.",
            #     (cellsToAdd,)
            # )

            timeout = self.mote._msf_get_sixtop_timeout(self.mote.preferredParent)
            celloptions = Mote.DIR_TXRX_SHARED
            self.mote._sixtop_cell_reservation_request(self.mote.preferredParent, cellsToAdd, celloptions, timeout)

        elif intReqCells < nowCells:
            cellsToRemove = 0
            if intReqCells > 0: # always keep one cell
                cellsToRemove = nowCells - intReqCells

                # self._log(
                #     self.INFO,
                #     "[ReSF] Having {0} cells, need {1} cells, going to remove {2} cells.",
                #     (nowCells, intReqCells, cellsToRemove)
                # )

                timeout = self.mote._msf_get_sixtop_timeout(self.mote.preferredParent)
                celloptions = Mote.DIR_TXRX_SHARED
                self.mote._sixtop_removeCells(self.mote.preferredParent, cellsToRemove, celloptions, timeout)

        # resetting queue
        self.avgQueue = []

        # schedule next housekeeping
        self._resf_schedule_housekeeping()

    def getBlockedTimeslots(self, maxASN):
        asns = []
        for n, l_resv in self.txTuples.iteritems():
            for resv in l_resv:
                n = resv['next']
                while n <= maxASN:
                    asns.append(n)
                    n += resv['period']

        for n, l_resv in self.rxTuples.iteritems():
            for resv in l_resv:
                n = resv['next']
                while n <= maxASN:
                    asns.append(n)
                    n += resv['period']

        for n, resfObject in self.txBlockedTuples.iteritems():
            if len(resfObject) > 0:  # txBlockedTuples can only contain one reservationList dict per neighbor, if so: len(dict) > 0
                for resv in resfObject['reservationList']:
                    n = resv['next']
                    while n <= maxASN:
                        asns.append(n)
                        n += resv['period']

        for n, resfObject in self.rxBlockedTuples.iteritems():
            if len(resfObject) > 0:  # rxBlockedTuples can only contain one reservationList dict per neighbor, if so: len(dict) > 0
                for resv in resfObject['reservationList']:
                    n = resv['next']
                    while n <= maxASN:
                        asns.append(n)
                        n += resv['period']

        tss = []
        for asn in asns:
            tss.append((asn % self.settings.slotframeLength))

        tss = list(set(tss))

        return tss

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
        