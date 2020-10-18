"""
\Brief Wireless network topology creator module

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>
\author Kazushi Muraoka <k-muraoka@eecs.berkeley.edu>
\author Nicola Accettura <nicola.accettura@eecs.berkeley.edu>
\author Xavier Vilajosana <xvilajosana@eecs.berkeley.edu>
"""

from abc import ABCMeta, abstractmethod
import logging
import math
import random
import numpy as np

import SimEngine
import SimSettings
import Mote


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


log = logging.getLogger('Topology')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())


class Topology(object):

    def __new__(cls, motes):
        settings = SimSettings.SimSettings()
        if hasattr(settings, 'topology'):
            if settings.topology == 'linear':
                return LinearTopology(motes)
            elif settings.topology == 'twoBranch':
                return TwoBranchTopology(motes)
            elif settings.topology == 'grid':
                return GridTopology(motes)
        if not hasattr(settings, 'topology') or settings.topology == 'random':
            return RandomTopology(motes)

    @classmethod
    def rssiToPdr(cls, rssi):
        settings = SimSettings.SimSettings()
        if hasattr(settings, 'topology'):
            if settings.topology == 'linear':
                return LinearTopology.rssiToPdr(rssi)
            elif settings.topology == 'twoBranch':
                return TwoBranchTopology.rssiToPdr(rssi)
            elif settings.topology == 'grid':
                return GridTopology.rssiToPdr(rssi)
        if not hasattr(settings, 'topology') or settings.topology == 'random':
            return RandomTopology.rssiToPdr(rssi)


class TopologyCreator:

    __metaclass__ = ABCMeta

    PISTER_HACK_LOWER_SHIFT = 40   # dB
    TWO_DOT_FOUR_GHZ = 2400000000  # Hz
    SPEED_OF_LIGHT = 299792458     # m/s

    @abstractmethod
    def __init__(self, motes):
        pass

    @abstractmethod
    def createTopology(self):
        pass

    @abstractmethod
    def rssiToPdr(cls, rssi):
        pass

    def _computeRSSI(self, mote, neighbor):
        """
        computes RSSI between any two nodes (not only neighbors)
        according to the Pister-hack model.
        """

        # distance in m
        distance = self._computeDistance(mote, neighbor)

        # sqrt and inverse of the free space path loss
        fspl = (self.SPEED_OF_LIGHT/(4*math.pi*distance*self.TWO_DOT_FOUR_GHZ))

        # simple friis equation in Pr=Pt+Gt+Gr+20log10(c/4piR)
        pr = (mote.txPower + mote.antennaGain + neighbor.antennaGain +
              (20 * math.log10(fspl)))

        # according to the receiver power (RSSI) we can apply the Pister hack
        # model.
        mu = pr - self.PISTER_HACK_LOWER_SHIFT / 2  # chosing the "mean" value

        # the receiver will receive the packet with an rssi uniformly
        # distributed between friis and friis -40
        rssi = (mu +
                random.uniform(-self.PISTER_HACK_LOWER_SHIFT/2,
                               self.PISTER_HACK_LOWER_SHIFT/2))

        return rssi

    def _computeRSSI_mobility(self, mote, neighbor):
        ''' computes RSSI between any two nodes (not only neighbors) for mobility scenarios applying a 12dB uniform variation'''

        mu = mote.initialRSSI[neighbor]
        rssi = random.uniform(-6, 6) + mu

        return rssi

    def _computePDR(self, mote, neighbor):
        """computes pdr to neighbor according to RSSI"""

        rssi = mote.getRSSI(neighbor)
        return self.rssiToPdr(rssi)

    def _computeDistance(self, mote, neighbor):
        """
        mote.x and mote.y are in km. This function returns the distance in m.
        """

        return 1000*math.sqrt((mote.x - neighbor.x)**2 +
                              (mote.y - neighbor.y)**2)


class GridTopology(TopologyCreator):

    # dBm, corresponds to PDR = 0.5 (see rssiPdrTable below)
    # STABLE_RSSI = -93.6
    # STABLE_RSSI = -95
    STABLE_RSSI = -91
    STABLE_NEIGHBORS = 1
    # (hack) small value to speed up the construction of fully-meshed topology
    FULLY_MESHED_SQUARE_SIDE = 0.005
    DISTANCE = 0.1
    # DISTANCE = 0.230

    def __init__(self, motes):
        # store params
        self.motes = motes

        # local variables
        self.settings = SimSettings.SimSettings()
        random.seed(self.settings.seed)
        np.random.seed(int(self.settings.seed))

        # if fullyMeshed is enabled, create a topology where each node has N-1
        # stable neighbors
        if self.settings.fullyMeshed:
            self.stable_neighbors = len(self.motes) - 1
            self.squareSide = self.FULLY_MESHED_SQUARE_SIDE
        else:
            self.stable_neighbors = self.STABLE_NEIGHBORS
            self.squareSide = self.settings.squareSide

    def getSquareCoordinates(self, coordinate, distance):
        '''
        Return the coordinates from the square around the given coordinate.
        '''
        coordinates = []
        coordinates.append((coordinate[0] - distance, coordinate[1] + distance)) # top, left
        coordinates.append((coordinate[0], coordinate[1] + distance)) # top, middle
        coordinates.append((coordinate[0] + distance, coordinate[1] + distance)) # top, right
        coordinates.append((coordinate[0] + distance, coordinate[1])) # middle, right
        coordinates.append((coordinate[0] + distance, coordinate[1] - distance)) # bottom, right
        coordinates.append((coordinate[0], coordinate[1] - distance)) # bottom, middle
        coordinates.append((coordinate[0] - distance, coordinate[1] - distance)) # bottom, left
        coordinates.append((coordinate[0] - distance, coordinate[1])) # middle, left
        return coordinates

    def isInCoordinates(self, coordinate, coordinates):
        epsilon = 0.000001
        for coordTmp in coordinates:
            if abs(coordinate[0] - coordTmp[0]) < epsilon and abs(coordinate[1] - coordTmp[1]) < epsilon:
                return True
        return False

    def createTopology(self):
        """
        Create a topology in which all nodes have at least
        stable_neighbors link with enough RSSI.
        If the mote does not have stable_neighbors links with enough RSSI,
        reset the location of the mote.
        """

        # find DAG root
        dagRoot = None
        for mote in self.motes:
            if mote.id == 0:
                mote.role_setDagRoot()
                dagRoot = mote
        assert dagRoot

        # put DAG root at center of area
        dagRoot.setLocation(x=self.squareSide/2,
                            y=self.squareSide/2)

        # Copy the contents of the list (but keep the originals) and shuffle them.
        # shuffledMotes = list(self.motes)
        # random.shuffle(shuffledMotes)
        # print shuffledMotes

        #### GRID PREPRATIONS.
        dagRootX, dagRootY = dagRoot.getLocation()
        # determine the number of 'square levels'
        numberOfMotes = len(self.motes)
        currentLvl = 0
        sumMotes = 0
        while (sumMotes < numberOfMotes):
            if currentLvl == 0:
                sumMotes += 1
            else:
                sumMotes += currentLvl * 8
            currentLvl += 1
        maxLvl = currentLvl - 1
        # print sumMotes
        coordinatesPerLvl = []
        for lvl in range(0, maxLvl + 1):
            coordinatesThisLvl = []
            if lvl == 0:
                coordinatesThisLvl = [(dagRootX, dagRootY)]
            elif lvl == 1:
                coordinatesThisLvl = self.getSquareCoordinates((dagRootX, dagRootY), self.DISTANCE)
            elif lvl > 1:
                coordinatesPrevLvl = coordinatesPerLvl[lvl - 1]
                coordinatesPrevPrevLvl = coordinatesPerLvl[lvl - 2]
                for coordinatePrevLvl in coordinatesPrevLvl:
                    squareCoordinates = self.getSquareCoordinates(coordinatePrevLvl, self.DISTANCE)
                    for squareCoordinate in squareCoordinates:
                        if not self.isInCoordinates(squareCoordinate,
                                                    coordinatesPrevPrevLvl) and not self.isInCoordinates(
                                squareCoordinate, coordinatesPrevLvl) and not self.isInCoordinates(squareCoordinate,
                                                                                                   coordinatesThisLvl):
                            coordinatesThisLvl.append(squareCoordinate)
            coordinatesPerLvl.append(coordinatesThisLvl)
            # print 'Level %d: # motes = %d' % (lvl, len(coordinatesThisLvl))
            # print coordinatesThisLvl
            assert len(coordinatesThisLvl) == 1 or len(coordinatesThisLvl) == lvl * 8

        allCoordinates = [j for i in coordinatesPerLvl for j in i]
        # print allCoordinates

        # reposition each mote until it is connected
        countMote = 1  # root 0 already has coordinates
        connectedMotes = [dagRoot]
        for mote in self.motes:
            if mote in connectedMotes:
                continue

            connected = False
            while not connected:
                # pick a random location

                newX = np.random.normal(allCoordinates[countMote][0], self.DISTANCE / 8, 1)[0]
                newY = np.random.normal(allCoordinates[countMote][1], self.DISTANCE / 8, 1)[0]

                mote.setLocation(
                    x=newX,
                    y=newY
                )

                # mote.setLocation(
                #     x = allCoordinates[countMote][0],
                #     y = allCoordinates[countMote][1]
                # )

                numStableNeighbors = 0

                # count number of neighbors with sufficient RSSI
                for cm in connectedMotes:

                    rssi = self._computeRSSI(mote, cm)
                    mote.setRSSI(cm, rssi)
                    cm.setRSSI(mote, rssi)

                    # save the intial RSSI values for future use in the mobility models
                    mote.initialRSSI[cm] = rssi
                    cm.initialRSSI[mote] = rssi

                    if rssi > self.STABLE_RSSI:
                        # print rssi
                        numStableNeighbors += 1

                # make sure it is connected to at least STABLE_NEIGHBORS motes
                # or connected to all the currently deployed motes when the number of deployed motes
                # are smaller than STABLE_NEIGHBORS
                if numStableNeighbors >= self.STABLE_NEIGHBORS or numStableNeighbors == len(connectedMotes):
                    connected = True

            connectedMotes += [mote]
            countMote += 1

        # for each mote, compute PDR to each neighbors
        for mote in self.motes:
            shortestDistance = None
            for m in self.motes:
                if mote == m:
                    continue
                if mote.getRSSI(m) > mote.minRssi:
                    pdr = self._computePDR(mote, m)
                    mote.setPDR(m, pdr)
                    m.setPDR(mote, pdr)
                # closest distance
                dist = self._computeDistance(mote, m)
                if shortestDistance == None or dist < shortestDistance:
                    mote.closestNeighbor = m
                    shortestDistance = dist

    def updateTopology(self):
        '''
        update topology: re-calculate RSSI values. For scenarios != static
        '''

        for mote1 in self.motes:
            for mote2 in self.motes:
                if mote1.id != mote2.id:
                    rssi = self._computeRSSI_mobility(mote1, mote2)  # the RSSI is calculated with applying a random variation
                    mote1.setRSSI(mote2, rssi)
                    mote2.setRSSI(mote1, rssi)
                    if rssi > mote1.minRssi:
                        pdr = self.rssiToPdr(rssi)
                        mote1.setPDR(mote2, pdr)
                        mote2.setPDR(mote1, pdr)
                    else:
                        pdr = 0
                        mote1.setPDR(mote2, pdr)
                        mote2.setPDR(mote1, pdr)

    @classmethod
    def rssiToPdr(cls, rssi):
        """
        rssi and pdr relationship obtained by experiment below
        http://wsn.eecs.berkeley.edu/connectivity/?dataset=dust
        """

        rssiPdrTable = {
            -97:    0.0000,  # this value is not from experiment
            -96:    0.1494,
            -95:    0.2340,
            -94:    0.4071,
            # <-- 50% PDR is here, at RSSI=-93.6
            -93:    0.6359,
            -92:    0.6866,
            -91:    0.7476,
            -90:    0.8603,
            -89:    0.8702,
            -88:    0.9324,
            -87:    0.9427,
            -86:    0.9562,
            -85:    0.9611,
            -84:    0.9739,
            -83:    0.9745,
            -82:    0.9844,
            -81:    0.9854,
            -80:    0.9903,
            -79:    1.0000,  # this value is not from experiment
        }

        # rssiPdrTable = {
        #     -97:    1.0000,  # this value is not from experiment
        #     -96:    1.0000,
        #     -95:    1.0000,
        #     -94:    1.0000,
        #     # <-- 50% PDR is here, at RSSI=-93.6
        #     -93:    1.0000,
        #     -92:    1.0000,
        #     -91:    1.0000,
        #     -90:    1.0000,
        #     -89:    1.0000,
        #     -88:    1.0000,
        #     -87:    1.0000,
        #     -86:    1.0000,
        #     -85:    1.0000,
        #     -84:    1.0000,
        #     -83:    1.0000,
        #     -82:    1.0000,
        #     -81:    1.0000,
        #     -80:    1.0000,
        #     -79:    1.0000,  # this value is not from experiment
        # }

        minRssi = min(rssiPdrTable.keys())
        maxRssi = max(rssiPdrTable.keys())

        if rssi < minRssi:
            pdr = 0.0
        elif rssi > maxRssi:
            pdr = 1.0
        else:
            floorRssi = int(math.floor(rssi))
            pdrLow = rssiPdrTable[floorRssi]
            pdrHigh = rssiPdrTable[floorRssi+1]
            # linear interpolation
            pdr = (pdrHigh - pdrLow) * (rssi - float(floorRssi)) + pdrLow

        assert pdr >= 0.0
        assert pdr <= 1.0

        return pdr

class RandomTopology(TopologyCreator):

    # dBm, corresponds to PDR = 0.5 (see rssiPdrTable below)
    # STABLE_RSSI = -93.6
    # STABLE_RSSI = -95
    STABLE_RSSI = -91
    STABLE_NEIGHBORS = 1
    # (hack) small value to speed up the construction of fully-meshed topology
    FULLY_MESHED_SQUARE_SIDE = 0.005

    def __init__(self, motes):
        # store params
        self.motes = motes

        # local variables
        self.settings = SimSettings.SimSettings()
        random.seed(self.settings.seed)

        # if fullyMeshed is enabled, create a topology where each node has N-1
        # stable neighbors
        if self.settings.fullyMeshed:
            self.stable_neighbors = len(self.motes) - 1
            self.squareSide = self.FULLY_MESHED_SQUARE_SIDE
        else:
            self.stable_neighbors = self.STABLE_NEIGHBORS
            self.squareSide = self.settings.squareSide

    # def checkValidPosition(self, xcoord, ycoord, countSquare):
    #     '''
    #     Checks if a given postition is valid when moving
    #     '''
    #
    #     inSquare = False  # total area
    #     insideObstacle1 = False  # rectangle 1
    #     insideObstacle2 = False  # rectangle 2
    #     if countSquare:
    #         if (xcoord < self.settings.squareSide and ycoord < self.settings.squareSide) and (
    #                 xcoord > 0 and ycoord > 0):
    #             inSquare = True
    #     else:
    #         inSquare = True
    #
    #     if (xcoord < (self.rect1[3] + self.margin)) and (ycoord > (self.rect1[2] - self.margin) and (ycoord < (self.rect1[4] + self.margin))):
    #         insideObstacle1 = True
    #     if (xcoord > (self.rect2[0] - self.margin)) and (ycoord > (self.rect2[2] - self.margin) and (ycoord < (self.rect1[4] + self.margin))):
    #         insideObstacle2 = True
    #
    #     if inSquare and not insideObstacle1 and not insideObstacle2:
    #         return True
    #     else:
    #         return False

    def createTopology(self):
        """
        Create a topology in which all nodes have at least
        stable_neighbors link with enough RSSI.
        If the mote does not have stable_neighbors links with enough RSSI,
        reset the location of the mote.
        """

        # find DAG root
        dagRoot = None
        for mote in self.motes:
            if mote.id == 0:
                mote.role_setDagRoot()
                dagRoot = mote
        assert dagRoot

        if self.settings.mobilityModel == 'RPGM':
            # put DAG root at center of area
            dagRoot.setLocation(x=SimEngine.SimEngine().targets[0][0],
                                y=SimEngine.SimEngine().targets[0][1])
        else:
            # put DAG root at center of area
            dagRoot.setLocation(x=self.squareSide/2,
                                y=self.squareSide/2)

        # reposition each mote until it is connected
        connectedMotes = [dagRoot]
        for mote in self.motes:
            if mote in connectedMotes:
                continue

            connected = False
            while not connected:
                # pick a random location
                mote.setLocation(x=self.squareSide*random.random(),
                                 y=self.squareSide*random.random())

                # if mote.id == 1:
                #     mote.setLocation(
                #         x=self.squareSide / 2.5 + 0.02,
                #         y=self.squareSide / 2.5 + 0.3
                #     )
                # elif mote.id == 2:
                #     mote.setLocation(
                #         x=self.squareSide / 2.5 + 0.3,
                #         y=self.squareSide / 2.5 + 0.3
                #     )
                #
                # elif mote.id == 3:
                #     mote.setLocation(
                #         x=self.squareSide / 2.5 + 0.1,
                #         y=self.squareSide / 2.5 + 0.4
                #     )

                # elif mote.id == 4:
                #     mote.setLocation(
                #         x=self.squareSide / 2.5 + 0.2,
                #         y=self.squareSide / 2.5 + 0.65
                #     )
                # else:

                mote.setLocation(
                    x=self.settings.squareSide * random.random(),
                    y=self.settings.squareSide * random.random()
                )

                numStableNeighbors = 0

                # count number of neighbors with sufficient RSSI
                for cm in connectedMotes:

                    rssi = self._computeRSSI(mote, cm)
                    mote.setRSSI(cm, rssi)
                    cm.setRSSI(mote, rssi)

                    # save the intial RSSI values for future use in the mobility models
                    mote.initialRSSI[cm] = rssi
                    cm.initialRSSI[mote] = rssi

                    if rssi > self.STABLE_RSSI:
                        numStableNeighbors += 1

                # make sure it is connected to at least stable_neighbors motes
                # or connected to all the currently deployed motes when the
                # number of deployed motes are smaller than stable_neighbors
                if (numStableNeighbors >= self.stable_neighbors or
                   numStableNeighbors == len(connectedMotes)):
                    print 'moteid %d, mote x %.4f, mote y %.4f: valid %s' % (mote.id, mote.x, mote.y , SimEngine.SimEngine().checkValidPosition(mote.x, mote.y, countSquare=True, placement=True))
                    if self.settings.mobilityModel == 'RPGM' and SimEngine.SimEngine().checkValidPosition(mote.x, mote.y, countSquare=True, placement=True):
                        connected = True
                    elif self.settings.mobilityModel != 'RPGM':
                        connected = True

            connectedMotes += [mote]

        # self.motes[3].setRSSI(self.motes[0], -96)
        # self.motes[0].setRSSI(self.motes[3], -96)

        # for each mote, compute PDR to each neighbors
        for mote in self.motes:
            for m in self.motes:
                if mote == m:
                    continue
                if mote.getRSSI(m) > mote.minRssi:
                    pdr = self._computePDR(mote, m)
                    mote.setPDR(m, pdr)
                    m.setPDR(mote, pdr)

    def updateTopology(self):
        '''
        update topology: re-calculate RSSI values. For scenarios != static
        '''

        for mote1 in self.motes:
            for mote2 in self.motes:
                if mote1.id != mote2.id:
                    rssi = self._computeRSSI_mobility(mote1, mote2)  # the RSSI is calculated with applying a random variation
                    mote1.setRSSI(mote2, rssi)
                    mote2.setRSSI(mote1, rssi)
                    if rssi > mote1.minRssi:
                        pdr = self.rssiToPdr(rssi)
                        mote1.setPDR(mote2, pdr)
                        mote2.setPDR(mote1, pdr)
                    else:
                        pdr = 0
                        mote1.setPDR(mote2, pdr)
                        mote2.setPDR(mote1, pdr)

    @classmethod
    def rssiToPdr(cls, rssi):
        """
        rssi and pdr relationship obtained by experiment below
        http://wsn.eecs.berkeley.edu/connectivity/?dataset=dust
        """

        rssiPdrTable = {
            -97:    0.0000,  # this value is not from experiment
            -96:    0.1494,
            -95:    0.2340,
            -94:    0.4071,
            # <-- 50% PDR is here, at RSSI=-93.6
            -93:    0.6359,
            -92:    0.6866,
            -91:    0.7476,
            -90:    0.8603,
            -89:    0.8702,
            -88:    0.9324,
            -87:    0.9427,
            -86:    0.9562,
            -85:    0.9611,
            -84:    0.9739,
            -83:    0.9745,
            -82:    0.9844,
            -81:    0.9854,
            -80:    0.9903,
            -79:    1.0000,  # this value is not from experiment
        }

        # rssiPdrTable = {
        #     -97:    1.0000,  # this value is not from experiment
        #     -96:    1.0000,
        #     -95:    1.0000,
        #     -94:    1.0000,
        #     # <-- 50% PDR is here, at RSSI=-93.6
        #     -93:    1.0000,
        #     -92:    1.0000,
        #     -91:    1.0000,
        #     -90:    1.0000,
        #     -89:    1.0000,
        #     -88:    1.0000,
        #     -87:    1.0000,
        #     -86:    1.0000,
        #     -85:    1.0000,
        #     -84:    1.0000,
        #     -83:    1.0000,
        #     -82:    1.0000,
        #     -81:    1.0000,
        #     -80:    1.0000,
        #     -79:    1.0000,  # this value is not from experiment
        # }

        minRssi = min(rssiPdrTable.keys())
        maxRssi = max(rssiPdrTable.keys())

        if rssi < minRssi:
            pdr = 0.0
        elif rssi > maxRssi:
            pdr = 1.0
        else:
            floorRssi = int(math.floor(rssi))
            pdrLow = rssiPdrTable[floorRssi]
            pdrHigh = rssiPdrTable[floorRssi+1]
            # linear interpolation
            pdr = (pdrHigh - pdrLow) * (rssi - float(floorRssi)) + pdrLow

        assert pdr >= 0.0
        assert pdr <= 1.0

        return pdr


class LinearTopology(TopologyCreator):

    COMM_RANGE_RADIUS = 50

    def __init__(self, motes):

        self.motes = motes
        self.settings = SimSettings.SimSettings()

    def createTopology(self):

        # place motes on a line at every 30m
        # coordinate of mote is expressed in km
        gap = 0.030
        for m in self.motes:
            if m.id == 0:
                m.role_setDagRoot()
            m.x = gap * m.id
            m.y = 0

        for mote in self.motes:

            # clear RSSI and PDR table; we may need clearRSSI and clear PDR
            # methods
            mote.RSSI = {}
            mote.PDR = {}

            for neighbor in self.motes:
                if mote == neighbor:
                    continue
                mote.setRSSI(neighbor, self._computeRSSI(mote, neighbor))
                pdr = self._computePDR(mote, neighbor)
                if(pdr > 0):
                    mote.setPDR(neighbor, pdr)

        if (hasattr(self.settings, 'linearTopologyStaticScheduling') and
           self.settings.linearTopologyStaticScheduling is True):
            assert ((not hasattr(self.settings, 'withJoin')) or
                    (self.settings.withJoin is False))
            self._build_rpl_tree()

            if (not hasattr(self.settings, 'cascadingScheduling')) or (self.settings.cascadingScheduling == False):
                self._install_symmetric_schedule()
            else:
                self._install_cascading_schedule()

            # make all the motes synchronized
            for mote in self.motes:
                mote.timeCorrectedSlot = 0

    @classmethod
    def rssiToPdr(cls, rssi):
        # This is for test purpose; PDR is 1.0 for -93 and above, otherwise PDR
        # is 0.0.
        rssiPdrTable = {
            -95: 0.0,
            -94: 1.0,
        }

        minRssi = min(rssiPdrTable.keys())
        maxRssi = max(rssiPdrTable.keys())

        if rssi < minRssi:
            pdr = 0.0
        elif rssi > maxRssi:
            pdr = 1.0
        else:
            pdr = rssiPdrTable[int(math.floor(rssi))]

        assert pdr >= 0.0
        assert pdr <= 1.0

        return pdr

    def _computeRSSI(self, mote, neighbor):
        if self._computeDistance(mote, neighbor) < self.COMM_RANGE_RADIUS:
            return -80
        else:
            return -100

    def _computePDR(self, mote, neighbor):
        return self.rssiToPdr(self._computeRSSI(mote, neighbor))

    def _build_rpl_tree(self):
        root = None
        for mote in self.motes:
            if mote.id == 0:
                mote.role_setDagRoot()
                root = mote
                mote.rank = Mote.RPL_MIN_HOP_RANK_INCREASE
            else:
                # mote with smaller ID becomes its preferred parent
                for neighbor in mote.PDR:
                    if ((not mote.preferredParent) or
                       (neighbor.id < mote.preferredParent.id)):
                        mote.preferredParent = neighbor
                root.parents.update({tuple([mote.id]):
                                     [[mote.preferredParent.id]]})
                mote.rank = (7 * Mote.RPL_MIN_HOP_RANK_INCREASE +
                             mote.preferredParent.rank)

            mote.dagRank = mote.rank / Mote.RPL_MIN_HOP_RANK_INCREASE

    def _alloc_cell(self, transmitter, receiver, slot_offset, channel_offset):
        # cell structure: (slot_offset, channel_offset, direction)
        transmitter._tsch_addCells(receiver,
                                   [(slot_offset,
                                     channel_offset,
                                     Mote.DIR_TX)])
        if receiver not in transmitter.numCellsToNeighbors:
            transmitter.numCellsToNeighbors[receiver] = 1
        else:
            transmitter.numCellsToNeighbors[receiver] += 1

        receiver._tsch_addCells(transmitter,
                                [(slot_offset,
                                  channel_offset,
                                  Mote.DIR_RX)])
        if transmitter not in receiver.numCellsFromNeighbors:
            receiver.numCellsFromNeighbors[transmitter] = 1
        else:
            receiver.numCellsFromNeighbors[transmitter] += 1

    def _install_symmetric_schedule(self):
        # find the edge node in the given linear topology
        depth = len(self.motes)
        for mote in self.motes:
            if mote.preferredParent:
                self._alloc_cell(mote,
                                 mote.preferredParent,
                                 depth - mote.id,
                                 0)

    def _install_cascading_schedule(self):
        alloc_pointer = 1 # start allocating with slot-1

        for mote in self.motes[::-1]: # loop in the reverse order
            child = mote
            while child and child.preferredParent:
                self._alloc_cell(child, child.preferredParent,
                                 alloc_pointer, 0)
                alloc_pointer += 1
                child = child.preferredParent


class TwoBranchTopology(TopologyCreator):

    COMM_RANGE_RADIUS = 50

    def __init__(self, motes):
        self.motes = motes
        self.settings = SimSettings.SimSettings()
        self.depth = int(math.ceil((float(len(self.motes)) - 2) / 2) + 1)
        if len(self.motes) < 2:
            self.switch_to_right_branch = 2
        else:
            self.switch_to_right_branch = self.depth + 1

    def createTopology(self):
        # place motes on a line at every 30m
        # coordinate of mote is expressed in km
        gap = 0.030

        for m in self.motes:
            if m.id == 0:
                m.role_setDagRoot()

            if m.id < self.switch_to_right_branch:
                m.x = gap * m.id
            else:
                m.x = gap * (m.id - self.switch_to_right_branch + 2)

            if m.id < 2:
                m.y = 0
            elif m.id < self.switch_to_right_branch:
                m.y = -0.03
            else:
                m.y = 0.03

        for mote in self.motes:
            # clear RSSI and PDR table; we may need clearRSSI and clearPDR methods
            mote.RSSI = {}
            mote.PDR = {}

            for neighbor in self.motes:
                if mote == neighbor:
                    continue
                mote.setRSSI(neighbor, self._computeRSSI(mote, neighbor))
                pdr = self._computePDR(mote, neighbor)
                if(pdr > 0):
                    mote.setPDR(neighbor, pdr)

        if (not hasattr(self.settings, 'withJoin')) or (self.settings.withJoin == False):
            self._build_rpl_tree()
            if (not hasattr(self.settings, 'cascadingScheduling') or
               not self.settings.cascadingScheduling):
                self._install_symmetric_schedule()
            else:
                self._install_cascading_schedule()
            # make all the motes synchronized
            for mote in self.motes:
                mote.timeCorrectedSlot = 0

    @classmethod
    def rssiToPdr(cls, rssi):
        # This is for test purpose; PDR is 1.0 for -93 and above, otherwise PDR
        # is 0.0.
        rssiPdrTable = {
            -95: 0.0,
            -94: 1.0,
        }

        minRssi = min(rssiPdrTable.keys())
        maxRssi = max(rssiPdrTable.keys())

        if rssi < minRssi:
            pdr = 0.0
        elif rssi > maxRssi:
            pdr = 1.0
        else:
            pdr = rssiPdrTable[int(math.floor(rssi))]

        assert pdr >= 0.0
        assert pdr <= 1.0

        return pdr

    def _computeRSSI(self, mote, neighbor):
        if self._computeDistance(mote, neighbor) < self.COMM_RANGE_RADIUS:
            return -80
        else:
            return -100

    def _computePDR(self, mote, neighbor):
        return self.rssiToPdr(self._computeRSSI(mote, neighbor))

    def _build_rpl_tree(self):
        root = None
        for mote in self.motes:
            if mote.id == 0:
                mote.role_setDagRoot()
                root = mote
            else:
                # mote with smaller ID becomes its preferred parent
                for neighbor in mote.PDR:
                    if (not mote.preferredParent or
                       neighbor.id < mote.preferredParent.id):
                        mote.preferredParent = neighbor
                root.parents.update({tuple([mote.id]):
                                     [[mote.preferredParent.id]]})

            if mote.id == 0:
                mote.rank = Mote.RPL_MIN_HOP_RANK_INCREASE
            else:
                mote.rank = (7 * Mote.RPL_MIN_HOP_RANK_INCREASE +
                             mote.preferredParent.rank)
            mote.dagRank = mote.rank / Mote.RPL_MIN_HOP_RANK_INCREASE

    def _alloc_cell(self, transmitter, receiver, slot_offset, channel_offset):
        # cell structure: (slot_offset, channel_offset, direction)
        transmitter._tsch_addCells(receiver, [(slot_offset, channel_offset,
                                               Mote.DIR_TX)])
        if receiver not in transmitter.numCellsToNeighbors:
            transmitter.numCellsToNeighbors[receiver] = 1
        else:
            transmitter.numCellsToNeighbors[receiver] += 1

        receiver._tsch_addCells(transmitter, [(slot_offset, channel_offset,
                                               Mote.DIR_RX)])
        if transmitter not in receiver.numCellsFromNeighbors:
            receiver.numCellsFromNeighbors[transmitter] = 1
        else:
            receiver.numCellsFromNeighbors[transmitter] += 1

    def _install_symmetric_schedule(self):
        # allocate TX cells for each node to its parent, which has the same
        # channel offset, 0.
        tx_alloc_factor = 1

        for mote in self.motes:
            if mote.preferredParent:
                if mote.id == 1:
                    slot_offset = len(self.motes) - 1
                elif mote.id < self.switch_to_right_branch:
                    slot_offset = (self.depth - mote.id) * 2 + 1
                elif len(self.motes) % 2 == 0: # even branches
                    slot_offset = (self.depth +
                                   self.switch_to_right_branch -
                                   1 - mote.id) * 2
                else:
                    slot_offset = (self.depth - 1 +
                                   self.switch_to_right_branch - 1 -
                                   mote.id) * 2

                self._alloc_cell(mote,
                                 mote.preferredParent,
                                 int(slot_offset), 0)

    def _install_cascading_schedule(self):
        # allocate TX cells and RX cells in a cascading bandwidth manner.

        for mote in self.motes[::-1]: # loop in the reverse order
            child = mote
            while child and child.preferredParent:
                if (hasattr(self.settings, 'schedulingMode') and
                   self.settings.schedulingMode == 'random-pick'):
                    if 'alloc_table' not in locals():
                        alloc_table = set()

                    if len(alloc_table) >= self.settings.slotframeLength:
                        raise ValueError('slotframe is too small')

                    while True:
                        # we don't use slot-0 since it's designated for a shared cell
                        alloc_pointer = random.randint(1,
                                                       self.settings.slotframeLength - 1)
                        if alloc_pointer not in alloc_table:
                            alloc_table.add(alloc_pointer)
                            break
                else:
                    if 'alloc_pointer' not in locals():
                        alloc_pointer = 1
                    else:
                        alloc_pointer += 1

                    if alloc_pointer > self.settings.slotframeLength:
                        raise ValueError('slotframe is too small')

                self._alloc_cell(child,
                                 child.preferredParent,
                                 alloc_pointer,
                                 0)
                child = child.preferredParent
