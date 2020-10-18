#!/usr/bin/python
"""
\brief GUI frame which shows the topology.

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
log = logging.getLogger('TopologyFrame')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

#============================ imports =========================================

import Tkinter

from SimEngine import SimEngine, \
                      SimSettings

#============================ defines =========================================

#============================ body ============================================

class TopologyFrame(Tkinter.Frame):

    UPDATE_PERIOD       = 100
    MOTE_SIZE           = 5
    HEIGHT              = 300
    WIDTH               = 300

    def __init__(self,guiParent):

        # store params
        self.guiParent  = guiParent

        # variables
        self.motes      = {}
        self.moteIds    = {}
        self.prevCoords = {}
        self.links      = {}
        self.resLinks   = {}
        self.attLinks   = {}
        self.repLinks   = {}

        # initialize the parent class
        Tkinter.Frame.__init__(
            self,
            self.guiParent,
            relief      = Tkinter.RIDGE,
            borderwidth = 1,
        )

        # GUI layout
        self.topology   = Tkinter.Canvas(self, width=self.WIDTH, height=self.HEIGHT)
        self.topology.grid(row=0,column=0)
        self._update=self.topology.after(self.UPDATE_PERIOD,self._updateGui)

    #======================== public ==========================================

    def close(self):
        self.topology.after_cancel(self._update)

    #======================== attributes ======================================

    @property
    def engine(self):
        return SimEngine.SimEngine(failIfNotInit=True)

    @property
    def settings(self):
        return SimSettings.SimSettings(failIfNotInit=True)

    #======================== private =========================================

    def _updateGui(self):

        try:
            self._redrawTopology()
        except EnvironmentError:
            # this happens when we try to update between runs
            pass

        self._update=self.topology.after(self.UPDATE_PERIOD,self._updateGui)

    def _redrawTopology(self):

        #===== mark all elements to be removed

        for (k,v) in self.motes.items():
            self.topology.itemconfig(v,tags=("deleteMe"))
        for (k,v) in self.moteIds.items():
            self.topology.itemconfig(v,tags=("deleteMe",))
        for (k,v) in self.links.items():
            self.topology.itemconfig(v,tags=("deleteMe",))

        #===== draw links

        # go over all links in the network
        for mote in self.engine.motes:
            for (ts,ch,neighbor) in mote.getTxCells():
                if (mote,neighbor) not in self.links:
                    # create
                    newLink = self.topology.create_line(self._linkCoordinates(mote,neighbor))
                    self.topology.itemconfig(newLink,activefill='red')
                    self.topology.tag_bind(newLink, '<ButtonPress-1>', self._linkClicked)
                    self.links[(mote,neighbor)] = newLink
                elif self.settings.mobilityModel != 'none' and (mote, neighbor) in self.links and \
                        (mote.id in self.prevCoords and neighbor.id in self.prevCoords and
                        ((self.prevCoords[mote.id][0] != mote.x or self.prevCoords[mote.id][1] != mote.y) or
                        (self.prevCoords[neighbor.id][0] != neighbor.x or self.prevCoords[neighbor.id][1] != neighbor.y))):
                    # first delete the previous ones
                    self.topology.delete(self.links[(mote,neighbor)])

                    # create
                    newLink = self.topology.create_line(self._linkCoordinates(mote,neighbor))
                    self.topology.itemconfig(newLink,activefill='red')
                    self.topology.tag_bind(newLink, '<ButtonPress-1>', self._linkClicked)
                    self.links[(mote,neighbor)] = newLink
                else:
                    # move
                    self.topology.dtag(self.links[(mote,neighbor)],"deleteMe")
                    # TODO:move
            for (ts,ch,neighbor) in mote.getSharedCells():
                # only include unicast links
                # if neighbor != mote._myNeighbors():
                if not mote._isBroadcast(neighbor):
                    # print self.prevCoords
                    if (mote,neighbor) not in self.links:
                        # create
                        newLink = self.topology.create_line(self._linkCoordinates(mote,neighbor))
                        self.topology.itemconfig(newLink,activefill='red')
                        self.topology.tag_bind(newLink, '<ButtonPress-1>', self._linkClicked)
                        self.links[(mote,neighbor)] = newLink
                    elif self.settings.mobilityModel != 'none' and (mote, neighbor) in self.links and \
                            (mote.id in self.prevCoords and neighbor.id in self.prevCoords and
                            ((self.prevCoords[mote.id][0] != mote.x or self.prevCoords[mote.id][1] != mote.y) or
                            (self.prevCoords[neighbor.id][0] != neighbor.x or self.prevCoords[neighbor.id][
                        1] != neighbor.y))):
                        # first delete the previous ones
                        self.topology.delete(self.links[(mote, neighbor)])

                        # create
                        newLink = self.topology.create_line(self._linkCoordinates(mote, neighbor))
                        self.topology.itemconfig(newLink, activefill='red')
                        self.topology.tag_bind(newLink, '<ButtonPress-1>', self._linkClicked)
                        self.links[(mote, neighbor)] = newLink
                    else:
                        # move
                        self.topology.dtag(self.links[(mote,neighbor)],"deleteMe")
                        # TODO:move

        #===== draw motes and moteIds

        if self.settings.mobilityModel == 'RPGM':
            # two obstacles
            rect1 = (self.engine.rect1[0]/self.settings.squareSide, self.engine.rect1[1]/self.settings.squareSide, self.engine.rect1[2]/self.settings.squareSide, self.engine.rect1[3]/self.settings.squareSide)
            rect1 = self.topology.create_rectangle(rect1[0]*self.WIDTH, rect1[1]*self.HEIGHT, rect1[2]*self.WIDTH, rect1[3]*self.HEIGHT)
            self.topology.itemconfig(rect1, fill='black')

            rect2 = (self.engine.rect2[0]/self.settings.squareSide, self.engine.rect2[1]/self.settings.squareSide, self.engine.rect2[2]/self.settings.squareSide, self.engine.rect2[3]/self.settings.squareSide)
            rect2 = self.topology.create_rectangle(rect2[0]*self.WIDTH, rect2[1]*self.HEIGHT, rect2[2]*self.WIDTH, rect2[3]*self.HEIGHT)
            self.topology.itemconfig(rect2, fill='black')

            # two obstacles
            rect3 = (self.engine.rect3[0]/self.settings.squareSide, self.engine.rect3[1]/self.settings.squareSide, self.engine.rect3[2]/self.settings.squareSide, self.engine.rect3[3]/self.settings.squareSide)
            rect3 = self.topology.create_rectangle(rect3[0]*self.WIDTH, rect3[1]*self.HEIGHT, rect3[2]*self.WIDTH, rect3[3]*self.HEIGHT)
            self.topology.itemconfig(rect3, fill='black')

            rect4 = (self.engine.rect4[0]/self.settings.squareSide, self.engine.rect4[1]/self.settings.squareSide, self.engine.rect4[2]/self.settings.squareSide, self.engine.rect4[3]/self.settings.squareSide)
            rect4 = self.topology.create_rectangle(rect4[0]*self.WIDTH, rect4[1]*self.HEIGHT, rect4[2]*self.WIDTH, rect4[3]*self.HEIGHT)
            self.topology.itemconfig(rect4, fill='black')

            for t in self.engine.targets:
                self.topology.create_oval((((
                                                    t[0] - self.engine.targetRadius) / self.settings.squareSide) * self.WIDTH,
                                           ((
                                                    t[1] - self.engine.targetRadius) / self.settings.squareSide) * self.HEIGHT,
                                           ((
                                                    t[0] + self.engine.targetRadius) / self.settings.squareSide) * self.WIDTH,
                                           ((
                                                    t[1] + self.engine.targetRadius) / self.settings.squareSide) * self.HEIGHT),
                                          fill='orange')

            # target = self.topology.create_oval((((self.engine.targetX-self.engine.targetRadius)/self.settings.squareSide)*self.WIDTH, ((self.engine.targetY-self.engine.targetRadius)/self.settings.squareSide)*self.HEIGHT, ((self.engine.targetX+self.engine.targetRadius)/self.settings.squareSide)*self.WIDTH, ((self.engine.targetY+self.engine.targetRadius)/self.settings.squareSide)*self.HEIGHT), fill='orange')
            # origin = self.topology.create_oval((((self.engine.originX-self.engine.targetRadius)/self.settings.squareSide)*self.WIDTH, ((self.engine.originY-self.engine.targetRadius)/self.settings.squareSide)*self.HEIGHT, ((self.engine.originX+self.engine.targetRadius)/self.settings.squareSide)*self.WIDTH, ((self.engine.originY+self.engine.targetRadius)/self.settings.squareSide)*self.HEIGHT), fill='orange')

        # go over all motes in the network
        for m in self.engine.motes:
            if m not in self.motes:
                # create
                newMote = self.topology.create_oval(self._moteCoordinates(m), fill='blue')
                self.topology.itemconfig(newMote, activefill='red')
                self.topology.tag_bind(newMote, '<ButtonPress-1>', self._moteClicked)
                self.motes[m] = newMote

                newMoteId = self.topology.create_text(self._moteIdCoordinates(m))
                self.topology.itemconfig(newMoteId,text=m.id)
                self.moteIds[m] = newMoteId
            elif self.settings.mobilityModel != 'none' and m in self.motes and (self.prevCoords[m.id][0] != m.x or self.prevCoords[m.id][1] != m.y):
                # first delete the previous ones
                self.topology.delete(self.motes[m])
                self.topology.delete(self.moteIds[m])
                if m in self.resLinks and m.id == 0:
                    self.topology.delete(self.resLinks[m])
                    self.topology.delete(self.attLinks[m])
                    self.topology.delete(self.repLinks[m])

                # create new ones at the new location
                newMote = self.topology.create_oval(self._moteCoordinates(m), fill='blue')
                self.topology.itemconfig(newMote, activefill='red')
                self.topology.tag_bind(newMote, '<ButtonPress-1>', self._moteClicked)
                self.motes[m] = newMote

                newMoteId = self.topology.create_text(self._moteIdCoordinates(m))
                self.topology.itemconfig(newMoteId,text=m.id)
                self.moteIds[m] = newMoteId

                if self.settings.mobilityModel == 'RPGM':
                    if m.id == 0 and m.resVec[0] is not None and m.resVec[1] is not None:
                        repLink = self.topology.create_line(
                            self._linkCoordinatesVector(m.x / self.settings.squareSide, m.y / self.settings.squareSide,
                                                        (m.x + m.repVec[0]) / self.settings.squareSide,
                                                        (m.y + m.repVec[1]) / self.settings.squareSide), fill='red')
                        attLink = self.topology.create_line(
                            self._linkCoordinatesVector(m.x / self.settings.squareSide, m.y / self.settings.squareSide,
                                                        (m.x + m.attVec[0]) / self.settings.squareSide,
                                                        (m.y + m.attVec[1]) / self.settings.squareSide), fill='green')
                        resLink = self.topology.create_line(
                            self._linkCoordinatesVector(m.x / self.settings.squareSide, m.y / self.settings.squareSide,
                                                        (m.x + m.resVec[0]) / self.settings.squareSide,
                                                        (m.y + m.resVec[1]) / self.settings.squareSide), fill='orange')

                        self.resLinks[m] = resLink
                        self.attLinks[m] = attLink
                        self.repLinks[m] = repLink
            else:
                # move
                self.topology.dtag(self.motes[m],"deleteMe")
                self.topology.dtag(self.moteIds[m],"deleteMe")
                if m in self.resLinks:
                    self.topology.dtag(self.resLinks[m], "deleteMe")
                # TODO: move

            # update the prev. coordinates.
            self.prevCoords[m.id] = (m.x, m.y)

        #===== remove all elements still marked

        for elem in self.topology.find_withtag("deleteMe"):
            self.topology.delete(elem)

    #======================== helpers =========================================

    #===== handle click events

    def _linkClicked(self,event):
        linkGui = event.widget.find_closest(event.x, event.y)[0]
        link    = None
        for (k,v) in self.links.items():
            if v==linkGui:
                link = k
                break
        assert link
        print "selected link {0}->{1}".format(link[0].id,link[1].id)
        self.guiParent.selectedLink = link

    def _moteClicked(self,event):
        moteGui = event.widget.find_closest(event.x, event.y)[0]
        mote    = None
        for (k,v) in self.motes.items():
            if v==moteGui:
                mote = k
                break
        assert mote
        print "selected mote {0}".format(mote.id)
        self.guiParent.selectedMote = mote

    #===== coordinate calculation

    def _moteCoordinates(self,m):
        (x,y) = self._normalizeLocation(m.getLocation())
        return (
            self.WIDTH*x-self.MOTE_SIZE/2,
            self.HEIGHT*y-self.MOTE_SIZE/2,
            self.WIDTH*x+self.MOTE_SIZE/2,
            self.HEIGHT*y+self.MOTE_SIZE/2,
        )

    def _moteIdCoordinates(self,m):
        (x,y) = self._normalizeLocation(m.getLocation())
        return (
            self.WIDTH*x,
            self.HEIGHT*y+self.MOTE_SIZE,
        )

    def _linkCoordinates(self,fromMote,toMote):
        (fromX, fromY)  = self._normalizeLocation(fromMote.getLocation())
        (toX,   toY)    = self._normalizeLocation(toMote.getLocation())
        return (
            fromX*self.WIDTH,
            fromY*self.HEIGHT,
            toX*self.WIDTH,
            toY*self.HEIGHT,
        )

    def _linkCoordinatesVector(self, x1, y1, x2, y2):
        return (
            x1*self.WIDTH,
            y1*self.HEIGHT,
            x2*self.WIDTH,
            y2*self.HEIGHT,
        )

    def _normalizeLocation(self,xy):
        (x,y) = xy
        return (
            x/self.settings.squareSide,
            y/self.settings.squareSide
        )
