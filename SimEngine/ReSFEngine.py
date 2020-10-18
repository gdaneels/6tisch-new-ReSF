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
log = logging.getLogger('ReSFEngine')
log.setLevel(logging.INFO)
log.addHandler(NullHandler())

#============================ imports =========================================

import SimEngine
import SimSettings

from collections import OrderedDict

class ReSFEngine(object):
    
    DEBUG                              = 'DEBUG'
    INFO                               = 'INFO'
    WARNING                            = 'WARNING'
    ERROR                              = 'ERROR'
        
    #===== start singleton
    _instance      = None
    _init          = False
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ReSFEngine,cls).__new__(cls, *args, **kwargs)
        return cls._instance
    #===== end singleton
    
    def __init__(self,failIfNotInit=False):
        
        if failIfNotInit and not self._init:
            raise EnvironmentError('ReSF singleton not initialized.')
        
        #===== start singleton
        if self._init:
            return
        self._init = True
        #===== end singleton
        
        self.engine                    = SimEngine.SimEngine()
        self.settings                  = SimSettings.SimSettings()

        self.didupdate = False
        self.didupdate2 = False

        self.tuples = OrderedDict()

        self.reservationSpread = 1000
        self.sendReSFRequestTimes = range(self.reservationSpread, self.reservationSpread * self.settings.numMotes + self.reservationSpread, self.reservationSpread)
        
        self._log(
            self.INFO,
            "[ReSFEngine] Initialized the ReSF engine singleton."
        )

        for m, resv in self.tuples.iteritems():
            self._log(
                self.INFO,
                "[ReSFEngine] Mote {0} = (start = {1} period = {2})",
                (m, resv['start'], resv['period'])
            )
    
    def converged(self):
        for m in self.engine.motes:
            if m.id != 0:
                self.tuples[m.id] = m.ReSF._resf_getTuple()
    
    def action(self):
        # if self.engine.motes[1].preferredParent is not None and not self.tuples[1]['exec'] and self.engine.asn > 20000:
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, period = {2}) reservation action executed.",
        #         (self.engine.motes[1].id, self.tuples[1]['start'], self.tuples[1]['period'])
        #     )
        #     self.engine.motes[1].ReSF._app_action_ReSFReservation()
        #     self.tuples[1]['exec'] = True
        # 
        # if self.engine.motes[1].preferredParent is not None and self.tuples[1]['exec'] and self.tuples[1]['timestamp'] < 32000 and self.engine.asn > 32000:
        #     self.tuples[1] = {'start':  100012, 'stop': 110012, 'period': 500, 'next': 100012, 'uniqueId': self.tuples[1]['uniqueId'], 'exec': True, 'timestamp': self.engine.asn}
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, stop = {2}, period = {3}) reservation action executed.",
        #         (self.engine.motes[1].id, self.tuples[1]['start'], self.tuples[1]['stop'], self.tuples[1]['period'])
        #     )
        #     self.engine.motes[1].ReSF._app_action_ReSFReservation()
        # 
        # if self.engine.motes[1].preferredParent is not None and self.engine.motes[2].preferredParent is not None and not self.tuples[2]['exec'] and self.engine.asn > 20000:
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, period = {2}) reservation action executed.",
        #         (self.engine.motes[2].id, self.tuples[2]['start'], self.tuples[2]['period'])
        #     )
        #     self.engine.motes[2].ReSF._app_action_ReSFReservation()
        #     self.tuples[2]['exec'] = True
        
        # if self.engine.motes[1].preferredParent is not None and self.engine.motes[2].preferredParent is not None and self.tuples[2]['exec'] and self.tuples[2]['timestamp'] < 32000 and self.engine.asn > 32000:
        #     self.tuples[2] = {'start':  100012, 'stop': 110012, 'period': 500, 'next': 100012, 'uniqueId': self.tuples[2]['uniqueId'], 'exec': True, 'timestamp': self.engine.asn}
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, stop = {2}, period = {3}) reservation action executed.",
        #         (self.engine.motes[2].id, self.tuples[2]['start'], self.tuples[2]['stop'], self.tuples[2]['period'])
        #     )
        #     self.engine.motes[2].ReSF._app_action_ReSFReservation()
        # 
        # if self.engine.motes[1].preferredParent is not None and self.engine.motes[3].preferredParent is not None and not self.tuples[3]['exec'] and self.engine.asn > 20000:
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, stop = {2}, period = {3}) reservation action executed.",
        #         (self.engine.motes[3].id, self.tuples[3]['start'], self.tuples[3]['stop'], self.tuples[3]['period'])
        #     )
        #     self.engine.motes[3].ReSF._app_action_ReSFReservation()
        #     self.tuples[3]['exec'] = True
        #

        # if self.engine.asn > 40000 and not self.didupdate and self.engine.motes[3].preferredParent is not None and self.engine.motes[3].preferredParent is not None and self.tuples[3]['timestamp'] < 40000:
        #     if self.settings.resfChangeParentPolicy == 'delete':
        #         # get list of tuples (unique_id, timestamp), do this before sending out new reservations
        #         # otherwise the list won't be correct anymore
        #         lst_ts = self.engine.motes[3].ReSF._resf_get_uniqueids_timestamps(self.engine.motes[3].preferredParent)
        #         print lst_ts
        #
        #     if self.settings.resfChangeParentPolicy == 'delete':
        #         self.engine.motes[3].ReSF._resf_send_delete(lst_ts, ReSF.RESF_PREFPARENT)
        #
        #     self.didupdate = True

        # if self.engine.asn > 40100 and self.didupdate and not self.didupdate2 and self.engine.motes[3].preferredParent is not None and self.engine.motes[3].preferredParent is not None:
        #     if self.settings.resfChangeParentPolicy == 'delete':
        #         # get list of tuples (unique_id, timestamp), do this before sending out new reservations
        #         # otherwise the list won't be correct anymore
        #         lst_ts = self.engine.motes[3].ReSF._resf_get_uniqueids_timestamps(self.engine.motes[3].preferredParent)
        #         print lst_ts
        #
        #     if self.settings.resfChangeParentPolicy == 'delete':
        #         self.engine.motes[3].ReSF._resf_send_delete(lst_ts, ReSF.RESF_THISPARENT, 1)
        #
        #     self.didupdate2 = True


        # if self.engine.asn > 40000 and not self.didupdate and self.engine.motes[3].preferredParent is not None and self.engine.motes[3].preferredParent is not None and self.tuples[3]['timestamp'] < 40000:
        #     self.tuples[3] = {'start':  150012, 'period': 500, 'next': 150012, 'uniqueId': self.tuples[3]['uniqueId'], 'timestamp': self.engine.asn}
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, period = {2}) reservation action executed.",
        #         (self.engine.motes[3].id, self.tuples[3]['start'], self.tuples[3]['period'])
        #     )
        #     self.engine.motes[3].ReSF._app_action_ReSFReservation()
        #     self.didupdate = True

        # if self.engine.asn > 40100 and self.didupdate and not self.didupdate2 and self.engine.motes[3].preferredParent is not None and self.engine.motes[3].preferredParent is not None:
        #     self.tuples[3] = {'start':  150100, 'period': 500, 'next': 150100, 'uniqueId': self.tuples[3]['uniqueId'], 'timestamp': self.engine.asn}
        #     self._log(
        #         self.INFO,
        #         "[ReSFEngine] Mote {0} = (start = {1}, period = {2}) reservation action executed.",
        #         (self.engine.motes[3].id, self.tuples[3]['start'], self.tuples[3]['period'])
        #     )
        #     self.engine.motes[3].ReSF._app_action_ReSFReservation()
        #     self.didupdate2 = True


        # if we are in the asn at the beginning of a cycle
        if self.engine.asn % self.settings.slotframeLength == 0:

            self._log(
                self.INFO,
                "[ReSFEngine] ---- START SLOTFRAME ----"
            )

            if self.settings.resfChangeParent == 1 and self.settings.resfChangeParentPolicy == 'keepalive' or self.settings.resfChangeParentPolicy == 'combined':
                # go through all the keep alive dictionaries and remove reservations if necessary
                for mote in self.engine.motes:
                    mote.ReSF._resf_keep_alive_housekeeping()

            for mote in self.engine.motes:
                mote.ReSF._resf_removeCells()
                mote.ReSF._resf_addCells(self.engine.asn, self.engine.asn + self.settings.slotframeLength - 1)
                # mote.ReSF._resf_countMSFCells(self.engine.asn, self.engine.asn + self.settings.slotframeLength - 1)

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
        output += ['[ASN={0:>6}] '.format(self.engine.getAsn())]
        output += [template.format(*params)]
        output  = ''.join(output)
        logfunc(output)
        