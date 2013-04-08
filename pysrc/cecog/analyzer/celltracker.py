"""
celltracker.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import os
import shutil
import subprocess
import numpy as np
from itertools import cycle
from collections import OrderedDict

from types import ListType
from csv import DictWriter

from cecog.util.util import makedirs
from cecog.util.logger import LoggerObject

from cecog.io.dotwriter import DotWriter
from cecog.extensions.graphLib import Graph
from cecog.util.util import write_table
from cecog.io.imagecontainer import Coordinate
from cecog import ccore

class CellTracker(LoggerObject):

    FEATURE_FLAT_PATTERN = "feature__%s"
    CLASS_FLAT_PATTERN = "class__%s"
    TRACKING_FLAT_PATTERN = "tracking__%s"
    FEATURE_COLUMN_PATTERN = "feature__%s"
    TRACKING_COLUMN_PATTERN = "tracking__%s"
    CLASS_COLUMN_PATTERN = "class__%s"
    OBJID_COLUMN_PATTERN = "objId"

    __slots__ = ['graph',
                 '_channelId',
                 '_dctTimePoints',
                 '_dctTimeChannels',
                 '_dctImageFilenames',
                 'dctVisitorData']

    def __init__(self, color_channel, region, timeholder, meta_data, position,
                 path_out,
                 fMaxObjectDistance, iMaxSplitObjects,
                 iMaxTrackingGap=5,
                 bHasClassificationData=False,
                 bExportTrackFeatures=False,
                 featureCompression=None,
                 flatFeatureCompression=None,
                 transitions=None,
                 forward_labels=None,
                 backward_labels=None,
                 iMaxInDegree=1,
                 iMaxOutDegree=2,
                 forward_check=0,
                 backward_check=0,
                 forward_range=-1,
                 backward_range=-1,
                 forward_range_min=False,
                 backward_range_min=False,
                 allow_one_daughter_cell=True):

        super(CellTracker, self).__init__()

        self._channelId = color_channel
        self._region = region
        self.graph = Graph()
        self._dctTimePoints = OrderedDict()

        self.meta_data = meta_data
        self.position = position
        self.timeholder = timeholder
        self.path_out = path_out

        self.fMaxObjectDistance = fMaxObjectDistance
        self.iMaxSplitObjects = iMaxSplitObjects
        self.iMaxTrackingGap = iMaxTrackingGap
        self.lstLabelTransitions = transitions
        self.iMaxInDegree = iMaxInDegree
        self.iMaxOutDegree = iMaxOutDegree
        self.iBackwardCheck = backward_check
        self.iForwardCheck = forward_check
        self.iBackwardRange = backward_range
        self.iForwardRange = forward_range
        self.bForwardRangeMin = forward_range_min
        self.bBackwardRangeMin = backward_range_min
        self.lstForwardLabels = forward_labels
        self.lstBackwardLabels = backward_labels
        self.bAllowOneDaughterCell = allow_one_daughter_cell

        self.bHasClassificationData = bHasClassificationData
        self.bExportTrackFeatures = bExportTrackFeatures
        self.featureCompression = featureCompression
        self.flatFeatureCompression = flatFeatureCompression

        self._timeholder = self.timeholder
        self._feature_names = None
        self.dctVisitorData = {}

    @property
    def start_frame(self):
        """Return the index of the first frame."""
        return min(self._dctTimePoints.keys())

    @property
    def end_frame(self):
        """Returns the index of the last frame currently processed."""
        return max(self._dctTimePoints.keys())

    @property
    def frames(self):
        return self._dctTimePoints

    @staticmethod
    def node_id(frame, object_label):
        return '%d_%s' %(frame, object_label)

    @staticmethod
    def split_nodeid(nodeid):
        return tuple([int(i) for i in nodeid.split('_')])

    def track_next_frame(self, frame):
        channel = self._timeholder[frame][self._channelId]
        holder = channel.get_region(self._region)

        for label, sample in holder.iteritems():
            node_id = self.node_id(frame, label)
            self.graph.add_node(node_id, sample)
            try:
                self._dctTimePoints[frame].append(label)
            except KeyError:
                self._dctTimePoints[frame] = [label]

        # connect time point only if any object is present
        if frame in self._dctTimePoints:
            self.connect_nodes(frame)

    def closest_preceding_frame(self, frame):
        assert self.iMaxTrackingGap > 0
        pre_frame = None
        iTries = 0


        # iMaxGap is the maximal number of steps we might go into the past
        # in order to find segmentation results.
        # a value of 0 or negative does not make any sense.
        # we therefore go at least 1 step into the past.
        iMaxGap = max(self.iMaxTrackingGap, 1)
        start = self.start_frame
        while pre_frame is None and iTries < iMaxGap and frame > start:
            frame -= 1
            if frame in self._dctTimePoints:
                pre_frame = frame
            else:
                iTries += 1
        return pre_frame

    def connect_nodes(self, iT):

        fMaxObjectDistanceSquared = float(self.fMaxObjectDistance) ** 2
        iMaxSplitObjects = self.iMaxSplitObjects

        bReturnSuccess = False
        oGraph = self.graph

        # search all nodes in the previous frame
        # if there is an empty frame, look for the closest frame
        # that contains objects. For this go up to iMaxTrackingGap
        # into the past.
        iPreviousT = self.closest_preceding_frame(iT)

        if not iPreviousT is None:
            bReturnSuccess = True
            dctMerges = {}
            dctSplits = {}

            # for all nodes in this layer
            for iObjIdP in self._dctTimePoints[iPreviousT]:

                strNodeIdP = self.node_id(iPreviousT, iObjIdP)
                oImageObjectP = oGraph.node_data(strNodeIdP)

                lstNearest = []

                for iObjIdC in self._dctTimePoints[iT]:
                    strNodeIdC = self.node_id(iT, iObjIdC)
                    oImageObjectC = oGraph.node_data(strNodeIdC)
                    dist = oImageObjectC.squaredMagnitude(oImageObjectP)

                    # take all candidates within a certain distance
                    if dist < fMaxObjectDistanceSquared:
                        lstNearest.append((dist, strNodeIdC))

                # lstNearest is the list of nodes in the current frame
                # whose distance to the previous node is smaller than the
                # fixed threshold.
                if len(lstNearest) > 0:
                    # sort ascending by distance (first tuple element)
                    lstNearest.sort(key=lambda x: x[0])

                    # take only a certain number as merge candidates (the N closest)
                    # and split candidates (this number is identical).
                    for dist, strNodeIdC in lstNearest[:iMaxSplitObjects]:
                        try:
                            dctMerges[strNodeIdC].append((dist, strNodeIdP))
                        except KeyError:
                            dctMerges[strNodeIdC] = [(dist, strNodeIdP)]

                        try:
                            dctSplits[strNodeIdP].append((dist, strNodeIdC))
                        except KeyError:
                            dctSplits[strNodeIdP] = [(dist, strNodeIdC)]

            # dctSplits contains for each node the list of potential
            # successors with distance smaller than threshold.
            # dctMerges contains for each node the list of potential
            # predecessors with distance smaller than threshold.

            # prevent split and merge for one node at the same time
            for id_c in dctMerges:
                found_connection = False

                nodes = dctMerges[id_c]
                # for all objects that have only one predecessor within the defined radius,
                # take this predecessor.
                if len(nodes) == 1:
                    oGraph.add_edge(nodes[0][1], id_c)
                    found_connection = True
                else:
                    # If there are several candidates (previous objects fulfilling the condition)
                    # take those candidates in the previous frame that have only one possible
                    # predecessor.
                    for dist, id_p in nodes:
                        if len(dctSplits[id_p]) == 1:
                            oGraph.add_edge(id_p, id_c)
                            found_connection = True

                # if there was no connection found, take the closest predecessor,
                # unless there is none.
                if not found_connection:
                    if len(nodes) > 0:
                        oGraph.add_edge(nodes[0][1], id_c)

        return iPreviousT, bReturnSuccess

    def visualizeTracks(self, iT, size, n=5, thick=True, radius=3):
        img_conn = ccore.Image(*size)
        img_split = ccore.Image(*size)
        min_T = self.start_frame
        if n < 0 or iT-n+1 < min_T:
            current = min_T
            n = iT-current+1
        else:
            current = iT-n+1

        found = False
        for i in range(n):
            col = int(255.*(i+1)/n)
            if col > 255:
                col = 255
            if current in self._dctTimePoints:
                previous = self.closest_preceding_frame(current)
                if not previous is None:
                    found = True
                    for objIdP in self._dctTimePoints[previous]:
                        nodeIdP = self.node_id(previous, objIdP)
                        objP = self.graph.node_data(nodeIdP)

                        if self.graph.out_degree(nodeIdP) > 1:
                            img = img_split
                        else:
                            img = img_conn

                        for edgeId in self.graph.out_arcs(nodeIdP):
                            nodeIdC = self.graph.tail(edgeId)
                            objC = self.graph.node_data(nodeIdC)
                            ccore.drawLine(ccore.Diff2D(*objP.oCenterAbs),
                                           ccore.Diff2D(*objC.oCenterAbs),
                                           img, col,
                                           thick=thick)
                            ccore.drawFilledCircle(ccore.Diff2D(*objC.oCenterAbs),
                                                   radius, img_conn, col)
            current += 1

        if not found and iT in self._dctTimePoints:
            for objId in self._dctTimePoints[iT]:
                nodeId = self.node_id(iT, objId)
                obj = self.graph.node_data(nodeId)
                ccore.drawFilledCircle(ccore.Diff2D(*obj.oCenterAbs),
                                       radius, img_conn, col)

        return img_conn, img_split

    def forwardReachable(self, node_id, reachableD, edgeD, iMaxLevel=None, iLevel=0):
        oGraph = self.graph
        reachableD[node_id] = True
        if iMaxLevel is None or iLevel < iMaxLevel:
            for out_edge_id in oGraph.out_arcs(node_id):
                next_node_id = oGraph.tail(out_edge_id)

                # ignore merging nodes
                key = "%s--%s" % (node_id, next_node_id)
                if key not in edgeD:
                    edgeD[key] = True
                    self.forwardReachable(next_node_id,
                                          reachableD,
                                          edgeD,
                                          iMaxLevel=iMaxLevel,
                                          iLevel=iLevel+1)

    def initVisitor(self, lstRootIds=None, iStart=None, iEnd=None):

        # this was somehow stupid since only root tracks (starting in the first
        # frame) are considered. tracks starting afterwards (due to cell
        # migration or stage shifts were NOT considered, resulting in a lower
        # and quality dependent yield.
        # This was fixed below.

        # find all starting tracks and use them for further analysis.
        # multiple traversing of one track is prevented by 'dctEdges', so that no
        # outgoing node ID can be touched twice

        if lstRootIds is None:
            # find all start tracks (without incoming edges)
            lstStartIds = [strNodeId for strNodeId in self.graph.node_list()
                           if self.graph.in_degree(strNodeId) == 0]
            # sort by time
            lstStartIds.sort(key = lambda x: self.split_nodeid(x)[0])
        else:
            lstStartIds = lstRootIds

        self.logger.debug("tracking: start nodes %d %s" %
                           (len(lstStartIds), lstStartIds))

        self.dctVisitorData = {}

        dctVisitedNodes = {}
        for strStartId in lstStartIds:
            self.dctVisitorData[strStartId] = {'_current': 0,
                                               '_full' : [[]],
                                               }
            self.logger.debug("root ID %s" % strStartId)
            self._forwardVisitor(strStartId, self.dctVisitorData[strStartId], dctVisitedNodes)


    def findNodesBoundingBox(self, nodeIdL):
        bbT = (float('+inf'), float('+inf'), float('-inf'), float('-inf'))
        for node_id in nodeIdL:
            nodeBbT = self.node_data(node_id).boundingBoxT
            bbT = (min(bbT[0], nodeBbT[0]),
                   min(bbT[1], nodeBbT[1]),
                   max(bbT[2], nodeBbT[2]),
                   max(bbT[3], nodeBbT[3]))
            for out_edge_id in self.out_arcs(node_id):
                next_node_id = self.tail(out_edge_id)
                ul_x, ul_y, lr_x, lr_y = self.findNodesBoundingBox([next_node_id])
                bbT = (min(bbT[0], ul_x),
                       min(bbT[1], ul_y),
                       max(bbT[2], lr_x),
                       max(bbT[3], lr_y))
        return bbT

    def clear(self, filter_area=None, filter_firstL=None):

        # remove nodes from first layer outside a certain area
        if not filter_area is None:
            for node_id in self.node_timeD[1][:]:
                s_obj = self.node_data(node_id)
                if not s_obj.inEllipse(filter_area):
                    self.node_timeD[1].remove(node_id)
                    #print " * node removed by filter_area:", node_id


        # remove first nodes by label
        if len(filter_firstL) > 0:
            for node_id in self.node_timeD[1][:]:
                s_obj = self.node_data(node_id)
                if s_obj.label in filter_firstL:
                    self.node_timeD[1].remove(node_id)
                    #print " * node removed by first_filter:", node_id


        # find all nodes which are not reachable from the first timepoint
        nodeL = self.node_timeD[1]
        reachableD = {}
        edgeD = {}
        for node_id in nodeL:
            self.forwardReachable(node_id, reachableD, edgeD)


        # remove all nodes from the entire graph which are not reachable
        for node_id in self.node_list()[:]:
            if node_id not in reachableD:
                #print " * node not reachable", node_id
                self.delete_node(node_id)
                time_point, obj_id = self.get_items_from_node_id(node_id)
                if node_id in self.node_timeD[time_point]:
                    self.node_timeD[time_point].remove(node_id)

        # delete all nodes which disappear without being in apoptosis
        # fix merges for short shapeI phases (segmentation errors)

    def clearByObjects(self, iStart, lstObjIds, iMaxLevel=None):
        """
        remove all nodes from first timepoint which are not in the list
        """

        for iObjId in self._dctTimePoints[iStart][:]:
            if not iObjId in lstObjIds:
                self._dctTimePoints[iStart].remove(iObjId)

        # find all nodes which are reachable from the first timepoint
        dctReachable = {}
        for iObjId in self._dctTimePoints[iStart][:]:
            strStartId = self.node_id(iStart, iObjId)
            self.forwardReachable(strStartId, dctReachable, {}, iMaxLevel=iMaxLevel)

        # remove all nodes from the entire graph which are not reachable
        lstNodes = self.graph.node_list()
        for strNodeId in lstNodes:
            if not strNodeId in dctReachable:
                self.graph.delete_node(strNodeId)
                iT, iObjId = self.split_nodeid(strNodeId)
                if iObjId in self._dctTimePoints[iT]:
                    self._dctTimePoints[iT].remove(iObjId)


    def clearByStartId(self, strStartId, iMaxLevel):
        dctReachable = {}
        self.forwardReachable(strStartId, dctReachable, {}, iMaxLevel=iMaxLevel)
        # remove all nodes from the entire graph which are not reachable
        for strNodeId in self.graph.node_list()[:]:
            if not strNodeId in dctReachable:
                #print " * node not reachable", node_id
                self.graph.delete_node(strNodeId)
                iT, iObjId = self.split_nodeid(strNodeId)
                if iObjId in self._dctTimePoints[iT]:
                    self._dctTimePoints[iT].remove(iObjId)
        for iT in self._dctTimePoints.keys():
            if len(self._dctTimePoints[iT]) == 0:
                del self._dctTimePoints[iT]
                del self._timeholder[iT]

    def iter_events(self):
        for track_results in self.dctVisitorData.itervalues():
            for start_id, event_data in track_results.iteritems():
                yield start_id, event_data

    def getBoundingBoxes(self, method="objectCentered", size=None, border=0):
        dctBoundingBoxes = {}
        for strStartId, dctEventData in self.iter_events():
            if strStartId in ['_full', '_current']:
                continue
            if method == "objectCentered":
                lstData = []
                for tplNodeIds in zip(*dctEventData['tracks']):
                    #print tplNodeIds
                    strNodeId = tplNodeIds[0]
                    iT = self.split_nodeid(strNodeId)[0]
                    lstObjIds = [self.split_nodeid(strNodeId)[1]
                                 for strNodeId in tplNodeIds]
                    lstImageObjects = [self.graph.node_data(strNodeId)
                                       for strNodeId in tplNodeIds]
                    minX = min([obj.oRoi.upperLeft[0] for obj in lstImageObjects])
                    minY = min([obj.oRoi.upperLeft[1] for obj in lstImageObjects])
                    maxX = max([obj.oRoi.lowerRight[0] for obj in lstImageObjects])
                    maxY = max([obj.oRoi.lowerRight[1] for obj in lstImageObjects])
                    width  = maxX - minX + 1
                    height = maxY - minY + 1
                    centerX = int(round(np.average([obj.oCenterAbs[0] for obj in lstImageObjects])))
                    centerY = int(round(np.average([obj.oCenterAbs[1] for obj in lstImageObjects])))
                    lstData.append((iT, centerX, centerY, width, height, lstObjIds))
                aData = np.array(lstData, 'O')
                if not size is None and len(size) == 2:
                    iDiffX = int(size[0] / 2)
                    iDiffY = int(size[1] / 2)
                else:
                    iDiffX = int(max(aData[:,3]) / 2 + border)
                    iDiffY = int(max(aData[:,4]) / 2 + border)
                # convert to float to for numpy float64 type
                lstTimeData = [(int(aI[0]),
                                (aI[1] - iDiffX,
                                 aI[2] - iDiffY,
                                 aI[1] + iDiffX - 1 + size[0] % 2,
                                 aI[2] + iDiffY - 1 + size[1] % 2),
                                aI[5])
                               for aI in aData]
            else:
                lstNodeIds = [id_ for data in dctEventData['tracks'] for id_ in data]
                lstImageObjects = [self.graph.node_data(strNodeId)
                                   for strNodeId in lstNodeIds]
                iMinX = min([oImgObj.oRoi.upperLeft[0] for oImgObj in lstImageObjects])
                iMinY = min([oImgObj.oRoi.upperLeft[1] for oImgObj in lstImageObjects])
                iMaxX = max([oImgObj.oRoi.lowerRight[0] for oImgObj in lstImageObjects])
                iMaxY = max([oImgObj.oRoi.lowerRight[1] for oImgObj in lstImageObjects])

                tplBoundingBox = (iMinX-border, iMinY-border,
                                  iMaxX+border, iMaxY+border)
                lstTimePoints = sorted(set([self.split_nodeid(strNodeId)[0]
                                            for strNodeId in lstNodeIds]))
                lstObjIds = [[self.split_nodeid(strNodeId)[1]
                              for strNodeId in tplNodeIds]
                             for tplNodeIds in zip(*dctEventData['tracks'])]
                assert len(lstObjIds) == len(lstTimePoints)
                lstTimeData = zip(lstTimePoints, cycle([tplBoundingBox], lstObjIds))

            dctBoundingBoxes[strStartId] = lstTimeData
        return dctBoundingBoxes

    def _backwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self.graph
        lstNodeIds.append(strNodeId)
        if ((self.iBackwardRange == -1 and oGraph.in_degree(strNodeId) == 0) or
            (self.bBackwardRangeMin and iLevel >= self.iBackwardRange and oGraph.in_degree(strNodeId) == 0) or
            (not self.bBackwardRangeMin and iLevel >= self.iBackwardRange)):
            return True
        if oGraph.out_degree(strNodeId) != 1:
            return False
        # check for split
        if oGraph.in_degree(strNodeId) != 1:
            return False

        oObject = oGraph.node_data(strNodeId)
        if iLevel > 1 and iLevel-1 <= self.iBackwardCheck and not \
                oObject.iLabel in self.lstBackwardLabels:
            return False

        strInEdgeId = oGraph.in_arcs(strNodeId)[0]
        strHeadId = oGraph.head(strInEdgeId)
        return self._backwardCheck(strHeadId, lstNodeIds, iLevel=iLevel+1)

    def _forwardCheck(self, strNodeId, lstNodeIds, iLevel=1, strFoundSplitId=None):
        oGraph = self.graph
        lstNodeIds.append(strNodeId)
        if ((self.iForwardRange == -1 and oGraph.out_degree(strNodeId) == 0) or
            (self.bForwardRangeMin and iLevel >= self.iForwardRange and oGraph.out_degree(strNodeId) == 0) or
            (not self.bForwardRangeMin and iLevel >= self.iForwardRange)):
            return True
        if oGraph.in_degree(strNodeId) > self.iMaxInDegree:
            return False
        # check for split
        if oGraph.out_degree(strNodeId) > self.iMaxOutDegree or oGraph.out_degree(strNodeId) == 0:
            return False

        oObject = oGraph.node_data(strNodeId)
        if iLevel <= self.iForwardCheck and not oObject.iLabel in self.lstForwardLabels:
            return False

        if (strFoundSplitId is None and
            oGraph.out_degree(strNodeId) > 1 and
            oGraph.out_degree(strNodeId) <= self.iMaxOutDegree):
            self.logger.info("     FOUND SPLIT! %s" % strNodeId)
            strFoundSplitId = strNodeId
            lstNewNodeIds = []
            if self.bAllowOneDaughterCell:
                bResult = False
            else:
                bResult = True
            for strOutEdgeId in oGraph.out_arcs(strNodeId):
                lstNewNodeIds.append([])
                strTailId = oGraph.tail(strOutEdgeId)
                if self.bAllowOneDaughterCell:
                    bResult |= self._forwardCheck(strTailId, lstNewNodeIds[-1], iLevel=iLevel+1, strFoundSplitId=strFoundSplitId)
                else:
                    bResult &= self._forwardCheck(strTailId, lstNewNodeIds[-1], iLevel=iLevel+1, strFoundSplitId=strFoundSplitId)
            lstNodeIds.append(lstNewNodeIds)
            return bResult
        else:
            strOutEdgeId = oGraph.out_arcs(strNodeId)[0]
            strTailId = oGraph.tail(strOutEdgeId)
            return self._forwardCheck(strTailId, lstNodeIds, iLevel=iLevel+1, strFoundSplitId=strFoundSplitId)

    def _forwardVisitor(self, strNodeId, dctResults, dctVisitedNodes, iLevel=0):
        oGraph = self.graph

        if oGraph.out_degree(strNodeId) == 1 and oGraph.in_degree(strNodeId) == 1:
            oObject = oGraph.node_data(strNodeId)
            oObjectNext = oGraph.node_data(oGraph.tail(oGraph.out_arcs(strNodeId)[0]))

            bFound = False
            for tplCheck in self.lstLabelTransitions:
                if (len(tplCheck) == 2 and
                    oObject.iLabel == tplCheck[0] and
                    oObjectNext.iLabel == tplCheck[1]):
                    bFound = True
                    break

            if bFound:
                bCandidateOk = True
                self.logger.debug("  found %6s" % strNodeId)

                if bCandidateOk:
                    lstBackwardNodeIds = []
                    bCandidateOk = self._backwardCheck(strNodeId,
                                                       lstBackwardNodeIds)
                    self.logger.debug("    %s - backwards %s    %s" % (strNodeId, {True: 'ok', False: 'failed'}[bCandidateOk], lstBackwardNodeIds))

                if bCandidateOk:
                    lstForwardNodeIds = []
                    strTailId = oGraph.tail(oGraph.out_arcs(strNodeId)[0])
                    bCandidateOk = self._forwardCheck(strTailId,
                                                      lstForwardNodeIds)
                    self.logger.debug("    %s - forwards %s    %s" % (strTailId, {True: 'ok', False: 'failed'}[bCandidateOk], lstForwardNodeIds))

                if bCandidateOk:

                    track_length = self.iBackwardRange + self.iForwardRange

                    lstBackwardNodeIds.reverse()
                    strStartId = lstBackwardNodeIds[0]

                    # found a split event
                    lstSplitIds = [i for i,t in enumerate(map(type, lstForwardNodeIds))
                                   if t == ListType]

                    #print lstSplitIds
                    if len(lstSplitIds) > 0:
                        # take only the first split event
                        iSplitIdx = lstSplitIds[0]
                        lstTracks = []
                        for lstSplit in lstForwardNodeIds[iSplitIdx]:
                            lstNodes = lstBackwardNodeIds + lstForwardNodeIds[:iSplitIdx] + lstSplit
                            if len(lstNodes) == track_length:
                                lstTracks.append(lstNodes)

                        for cnt, track in enumerate(lstTracks):
                            new_start_id = '%s_%d' % (strStartId, cnt+1)
                            dctResults[new_start_id] = {'splitId'  : lstForwardNodeIds[iSplitIdx-1],
                                                        'eventId'  : strNodeId,
                                                        'maxLength': track_length,
                                                        'tracks'   : [track],
                                                        # keep value at which index the two daugther
                                                        # tracks differ due to a split event
                                                        'splitIdx' : iSplitIdx + len(lstBackwardNodeIds),
                                                        }
                    else:
                        lstNodeIds = lstBackwardNodeIds + lstForwardNodeIds
                        dctResults[strStartId] = {'splitId'  : None,
                                                  'eventId'  : strNodeId,
                                                  'maxLength': track_length,
                                                  'tracks'   : [lstNodeIds],
                                                  }
                    #print dctResults[strStartId]
                    self.logger.debug("  %s - valid candidate" % strStartId)

        # record the full trajectory in a liniearized way
        base = dctResults['_current']
        dctResults['_full'][base].append(strNodeId)
        depth = len(dctResults['_full'][base])

        #self.logger.debug("moo %s" % self.out_arcs(strNodeId))
        for idx, strOutEdgeId in enumerate(oGraph.out_arcs(strNodeId)):
            strTailId = oGraph.tail(strOutEdgeId)
            if not strTailId in dctVisitedNodes:
                dctVisitedNodes[strTailId] = True

                # make a copy of the list for the new branch
                if idx > 0:
                    dctResults['_full'].append(dctResults['_full'][base][:depth])
                    dctResults['_current'] += idx
                self._forwardVisitor(strTailId, dctResults, dctVisitedNodes, iLevel=iLevel+1)

    @staticmethod
    def callGraphviz(dot_filename, format = "png"):
        cmd = "dot %s -T%s -o %s" %\
               (dot_filename, format,
                dot_filename.replace(".dot",".%s" % format))
        # start a subprocess and do something else in between... :-)
        p = subprocess.Popen(cmd, shell=True)
        # we dont have to wait for the subprocess...
        p.wait()

    def _exportGraph(self, oTracker, strDotFilePath, bRunDot=False):
        dot = DotWriter(strDotFilePath, oTracker)
        if bRunDot:
            self.callGraphviz(strDotFilePath)

    def exportGraph(self, strDotFilePath, bRunDot=False):
        self._exportGraph(self, strDotFilePath, bRunDot=bRunDot)
        self.exportChannelDataFlat(strDotFilePath.split('.')[0] + '_features.txt', 'Primary', 'primary', None)

    def export_track_features(self, dctChannels, clear_path=False):
        outdir = os.path.join(self.path_out, 'events')
        if clear_path:
            shutil.rmtree(outdir, True)
            makedirs(outdir)


        for strRootId, dctTrackResults in self.dctVisitorData.iteritems():
            self.logger.debug("* root %s, candidates %s" % (strRootId, dctTrackResults.keys()))
            for strStartId, dctEventData in dctTrackResults.iteritems():
                if strStartId[0] != '_':
                    if self.bExportTrackFeatures:
                        for strChannelId, dctRegions in dctChannels.iteritems():
                            if strChannelId in self._timeholder.channels:
                                for strRegionId, lstFeatureNames in dctRegions.iteritems():
                                    if self.featureCompression is None:
                                        strCompression = ''
                                    else:
                                        strCompression = '.%s' %self.featureCompression
                                    strFilename = self._formatFilename('C%s__R%s' % (strChannelId, strRegionId),
                                                                       nodeId=strStartId, prefix='features', subPath='events',
                                                                       ext='.txt%s' % strCompression)

                                    self.exportChannelData(dctEventData,
                                                           strFilename,
                                                           strChannelId,
                                                           strRegionId,
                                                           lstFeatureNames)
                    self.logger.debug("* root %s ok" % strStartId)


    def exportChannelDataFlat(self, strFilename, strChannelId, strRegionId, lstFeatureNames):

            oTable = None
            if not lstFeatureNames is None:
                lstFeatureNames = sorted(lstFeatureNames)

            for iT in self._timeholder:
                oChannel = self._timeholder[iT][strChannelId]

                if oChannel.has_region(strRegionId):
                    oRegion = oChannel.get_region(strRegionId)

                    if len(oRegion) > 0:
                        if lstFeatureNames is None:
                            lstFeatureNames = oRegion.feature_names

                        if oTable is None:
                            tracking_features = ['center_x','center_y',
                                                 'upperleft_x', 'upperleft_y',
                                                 'lowerright_x', 'lowerright_y']


                            oTable = DictWriter(open(strFilename,'wb'), ['Frame', 'ObjectID'] +
                                              [self.FEATURE_FLAT_PATTERN % f for f in lstFeatureNames] +
                                              [self.CLASS_FLAT_PATTERN % x for x in ['name', 'label', 'probability']] +
                                              [self.TRACKING_FLAT_PATTERN % x for x in tracking_features],
                                              delimiter='\t')
                            oTable.writeheader()

                        for iObjId, oObj in oRegion.iteritems():
                            dctData = {'Frame' : iT,
                                       'ObjectID' : iObjId}
                            aFeatures = oRegion.features_by_name(iObjId, lstFeatureNames)
                            for fFeature, strName in zip(aFeatures, lstFeatureNames):
                                dctData[self.FEATURE_FLAT_PATTERN % strName] = float(fFeature)
                            if self.bHasClassificationData:
                                dctData[self.CLASS_FLAT_PATTERN % 'label'] = oObj.iLabel
                                dctData[self.CLASS_FLAT_PATTERN % 'name'] = oObj.strClassName
                                dctData[self.CLASS_FLAT_PATTERN % 'probability'] =\
                                    ','.join(['%d:%.5f' % (int(x),y) for x,y in oObj.dctProb.iteritems()])

                            dctData[self.TRACKING_FLAT_PATTERN % 'center_x'] = oObj.oCenterAbs[0]
                            dctData[self.TRACKING_FLAT_PATTERN % 'center_y'] = oObj.oCenterAbs[1]
                            dctData[self.TRACKING_FLAT_PATTERN % 'upperleft_x'] = oObj.oRoi.upperLeft[0]
                            dctData[self.TRACKING_FLAT_PATTERN % 'upperleft_y'] = oObj.oRoi.upperLeft[1]
                            dctData[self.TRACKING_FLAT_PATTERN % 'lowerright_x'] = oObj.oRoi.lowerRight[0]
                            dctData[self.TRACKING_FLAT_PATTERN % 'lowerright_y'] = oObj.oRoi.lowerRight[1]

                            oTable.writerow(dctData)


    def exportChannelData(self, dctEventData, strFilename, strChannelId, strRegionId, lstFeatureNames):
        bHasFeatures = False
        strEventId = dctEventData['eventId']
        iEventT, iObjId = self.split_nodeid(strEventId)

        bHasSplitId = 'splitId' in dctEventData

        lstHeaderNames = ['Frame', 'Timestamp', 'isEvent']
        lstHeaderTypes = ['i', 'f', 'b']
        if bHasSplitId:
            lstHeaderNames.append('isSplit')
            lstHeaderTypes.append('b')
            if not dctEventData['splitId'] is None:
                iSplitT, iObjId = self.split_nodeid(dctEventData['splitId'])
            else:
                iSplitT = None

        table = []

        # zip nodes with same time together
        for tplNodes in zip(*dctEventData['tracks']):

            lstObjectIds = []
            iT = None
            for strNodeId in tplNodes:
                iNodeT, iObjId = self.split_nodeid(strNodeId)
                if iT is None:
                    iT = iNodeT
                else:
                    assert iT == iNodeT
                lstObjectIds.append(iObjId)

            # FIXME
            if iT is None:
                return

            oChannel = self._timeholder[iT][strChannelId]
            oRegion = oChannel.get_region(strRegionId)

            if not bHasFeatures:
                bHasFeatures = True
                if lstFeatureNames is None:
                    lstFeatureNames = oRegion.feature_names
                lstHeaderNames += [self.OBJID_COLUMN_PATTERN]

                if self.bHasClassificationData:
                    lstHeaderNames += [self.CLASS_COLUMN_PATTERN % x
                                       for x in ['name', 'label', 'probability']]
                lstHeaderNames += [self.FEATURE_COLUMN_PATTERN % strFeatureName
                                   for strFeatureName in lstFeatureNames]

                tracking_features = ['center_x','center_y',
                                     'upperleft_x', 'upperleft_y',
                                     'lowerright_x', 'lowerright_y']
                lstHeaderNames += [self.TRACKING_COLUMN_PATTERN % strFeatureName
                                   for strFeatureName in tracking_features]

            coordinate = Coordinate(position=self.position, time=iT)

            dctData = {'Frame' : iT,
                       'Timestamp' : self.meta_data.get_timestamp_relative(coordinate),
                       'isEvent' : 1 if iT == iEventT else 0,}

            if bHasSplitId:
                dctData['isSplit'] = 1 if iT == iSplitT else 0

            #for iIdx, iObjId in enumerate(lstObjectIds):
            iObjId = lstObjectIds[0]
            if iObjId in oRegion:
                oObj = oRegion[iObjId]

                dctData[self.OBJID_COLUMN_PATTERN] = iObjId

                # classification data
                if self.bHasClassificationData:
                    dctData[self.CLASS_COLUMN_PATTERN % 'label'] = oObj.iLabel
                    dctData[self.CLASS_COLUMN_PATTERN % 'name'] = oObj.strClassName
                    dctData[self.CLASS_COLUMN_PATTERN % 'probability'] =\
                        ','.join(['%d:%.5f' % (int(x),y) for x,y in oObj.dctProb.iteritems()])

                common_ftr = [f for f in set(oRegion.feature_names).intersection(lstFeatureNames)]
                aFeatures = oRegion.features_by_name(iObjId, common_ftr)
                for fFeature, strFeatureName in zip(aFeatures, common_ftr):
                    dctData[self.FEATURE_COLUMN_PATTERN % strFeatureName] = fFeature

                # features not calculated are exported as NAN
                diff_ftr = [f for f in set(lstFeatureNames).difference(oRegion.feature_names)]
                for df in diff_ftr:
                    dctData[self.FEATURE_COLUMN_PATTERN %df] = float("NAN")

                # object tracking data (absolute center)
                dctData[self.TRACKING_COLUMN_PATTERN %'center_x'] = oObj.oCenterAbs[0]
                dctData[self.TRACKING_COLUMN_PATTERN %'center_y'] = oObj.oCenterAbs[1]
                dctData[self.TRACKING_COLUMN_PATTERN %'upperleft_x'] = oObj.oRoi.upperLeft[0]
                dctData[self.TRACKING_COLUMN_PATTERN %'upperleft_y'] = oObj.oRoi.upperLeft[1]
                dctData[self.TRACKING_COLUMN_PATTERN %'lowerright_x'] = oObj.oRoi.lowerRight[0]
                dctData[self.TRACKING_COLUMN_PATTERN %'lowerright_y'] = oObj.oRoi.lowerRight[1]
            else:
                # we rather skip the entire event in case the object ID is not valid
                return

            #print dctData
            table.append(dctData)

        if len(table) > 0:
            #print "exportChannelData, filenname: ", strFilename
            write_table(strFilename, table, column_names=lstHeaderNames)

    def _formatFilename(self, strSuffix=None, nodeId=None, prefix=None, subPath=None, branchId=None, ext='.txt'):
        lstParts = []
        if not prefix is None:
            lstParts.append(prefix)
        lstParts.append('P%s' % self.position)
        if not nodeId is None:
            items = self.split_nodeid(nodeId)
            frame, obj_id = items[:2]
            if not branchId is None:
                branch_id = branchId
            else:
                if len(items) == 3:
                    branch_id = items[2]
                else:
                    branch_id = 1
            lstParts += ['T%05d' % frame,
                         'O%04d' % obj_id,
                         'B%02d' % branch_id,
                         ]
        if not strSuffix is None:
            lstParts.append(strSuffix)
        strParts = '__'.join(lstParts)
        if not subPath is None:
            strPathOut = os.path.join(self.path_out, subPath)
            makedirs(strPathOut)
        else:
            strPathOut = self.path_out
        return os.path.join(strPathOut, strParts) + ext

    def map_feature_names(self, feature_names):
        """Return a hash table to map feature names to new names."""

        name_table = OrderedDict()
        name_table['mean'] = 'n2_avg'
        name_table['sd'] = 'n2_stddev'
        name_table['size'] = 'roisize'

        # prominent place int the table for certain features
        flkp = OrderedDict()
        for nname, name in name_table.iteritems():
            if name in feature_names:
                flkp[nname] = name
        for fn in feature_names:
            flkp[self.FEATURE_FLAT_PATTERN %fn] = fn
        return flkp

    def exportFullTracks(self, sep='\t'):
        path = os.path.join(self.path_out, 'full')
        shutil.rmtree(path, True)
        makedirs(path)

        for start_id, data in self.dctVisitorData.iteritems():
            for idx, track in enumerate(data['_full']):
                has_header = False
                line1 = []
                line2 = []
                line3 = []

                filename = self._formatFilename(nodeId=start_id, subPath='full', branchId=idx+1)
                f = file(filename, 'w')

                for node_id in track:
                    frame, obj_id = self.split_nodeid(node_id)

                    coordinate = Coordinate(position=self.position, time=frame)
                    prefix = [frame, self.meta_data.get_timestamp_relative(coordinate), obj_id]
                    prefix_names = ['frame', 'time', 'objID']
                    items = []

                    for channel in self._timeholder[frame].values():
                        for region_id in channel.region_names():
                            region = channel.get_region(region_id)
                            if obj_id in region:
                                flkp = self.map_feature_names(region.feature_names)
                                if not has_header:
                                    keys = ['classLabel', 'className']
                                    if channel.NAME == 'Primary':
                                        keys += ['centerX', 'centerY']
                                    keys += flkp.keys()
                                    line1 += [channel.NAME.upper()] * len(keys)
                                    line2 += [str(region_id)] * len(keys)
                                    line3 += keys
                                obj = region[obj_id]
                                features = region.features_by_name(obj_id, flkp.values())
                                values = [x if not x is None else '' for x in [obj.iLabel, obj.strClassName]]
                                if channel.NAME == 'Primary':
                                    values += [obj.oCenterAbs[0], obj.oCenterAbs[1]]
                                values += list(features)
                                items.extend(values)

                    if not has_header:
                        has_header = True
                        prefix_str = [''] * len(prefix)
                        line1 = prefix_str + line1
                        line2 = prefix_str + line2
                        line3 = prefix_names + line3
                        f.write('%s\n' % sep.join(line1))
                        f.write('%s\n' % sep.join(line2))
                        f.write('%s\n' % sep.join(line3))

                    f.write('%s\n' % sep.join(map(str, prefix + items)))
                f.close()
