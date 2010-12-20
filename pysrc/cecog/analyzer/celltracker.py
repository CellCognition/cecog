"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

#-------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       subprocess, \
       logging, \
       itertools, \
       re, \
       shutil
from types import ListType, FloatType

#-------------------------------------------------------------------------------
# extension module imports:
#
from numpy import array, average

from pdk.options import Option
from pdk.optionmanagers import OptionManager
#from pdk.containers.tableio import (importTable,
#                                    exportTable)
#from pdk.containers.tablefactories import newTable
from pdk.ordereddict import OrderedDict
from pdk.map import dict_append_list
from pdk.fileutils import safe_mkdirs, collect_files
from pdk.iterator import unique, flatten, all_equal
from pdk.attributemanagers import (get_slot_values,
                                   set_slot_values)

#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog.extensions.graphLib import Graph
from cecog.util.util import write_table
from cecog import ccore

#-------------------------------------------------------------------------------
# constants:
#

DEBUG = False

#-------------------------------------------------------------------------------
# functions:
#

def printd(str):
    if DEBUG:
        print str


#-------------------------------------------------------------------------------
# classes:
#


class DotWriter(object):

    #SHAPE = 'ellipse'
    SHAPE = 'plaintext'
    NODE_STYLE = ' [shape=circle]'
    EDGE_STYLE = ' [style=bold, arrowsize=0.5]'

    def __init__(self, strFilename, oTracker, lstNodeIds=[], tplTimeRange=None,
                 strNodeDefaultColor="#AAAAAA"):
        self.oTracker = oTracker
        self._dctKnownNodeIds = {}
        self._dctEdges = {}
        self.strNodeDefaultColor = strNodeDefaultColor
        self.oDotFile = file(strFilename, "w")

        self.oDotFile.write("digraph G {\n")
#        tmp = "ratio=auto; size=\"160.0,260.0\"; " +\
#              "ranksep=.25; nodesep=.5; " +\
#              "fontname=\"Helvetica\"; rankdir=TB;\n"
#        tmp = "ratio=auto; size=\"100.0,200.0\"; " +\
#              "ranksep=.8; nodesep=.8; " +\
#              "fontname=\"Helvetica\"; rankdir=TB;\n"
        tmp = "ranksep=.01; nodesep=1.5; " +\
              "fontname=\"Helvetica\"; rankdir=TB;\n"
        self.oDotFile.write(tmp)


#        self.dot_file.write("node [shape=\"plaintext\"];\n")
        lstTimeStrings = ["time %d" % x for x in oTracker.getTimePoints()]
#        self.dot_file.write("%s;\n" %\
#                            " -> ".join(["\"%s\"" % x
#                                         for x in time_nodeL]))

        self.oDotFile.write("node%s;\n" % self.NODE_STYLE)

        iStart, iEnd = oTracker.getValidTimeLimits()
#        print iStart, iEnd, oTracker.getTimePoints(), oTracker.getGraph().node_list()

        for iT, lstNodeIds in oTracker.getTimePoints().iteritems():
            for iObjId in lstNodeIds:
                strNodeId = oTracker.getNodeIdFromComponents(iT, iObjId)
                if iT == iStart:
                    self._traverseGraph(strNodeId)
                # find appearing nuclei
                elif strNodeId not in self._dctKnownNodeIds:
                    self._traverseGraph(strNodeId)


        # write nodes
        strTmpNode = '"%s" [%s];\n'
        oGraph = self.oTracker.getGraph()

        for strNodeId, strLabel in self._dctKnownNodeIds.iteritems():
            node = oGraph.node_data(strNodeId)
            #lstNodeAttributes = ["label=\"%s\"" % str_label]
            lstNodeAttributes = []

            if node.strHexColor is None:
                strHexColor = self.strNodeDefaultColor
            else:
                strHexColor = node.strHexColor
            lstNodeAttributes += ['style=filled','fillcolor="%s"' % strHexColor]
            if len(node.dctProb) > 0:
                fClasses = 1.0 / len(node.dctProb)
                fProb = node.dctProb[node.iLabel]
                # scale the node size between 1.1 (100% prob) and 0.1 (1/n% prob, less possible)
                fWidth = 1.0 * (fProb - fClasses) / (1.01 - fClasses) + 0.1
                #fWidth = 1.0
                fHeight = fWidth
                #lstNodeAttributes += ["label=\"%d %.1f\"" % (node.iId, fProb * 100.0),
                #                      "width=\"%.2f\"" % fWidth,
                #                      "height=\"%.2f\"" % fHeight,
                #                      "fixedsize=\"%s\"" % True]
                lstNodeAttributes += ['label="%s"' % strNodeId,
                                      "width=\"%.2f\"" % fWidth,
                                      "height=\"%.2f\"" % fHeight,
                                      'fixedsize="%s\"' % True,
                                      ]
            else:
                lstNodeAttributes += ['fixedsize="%s\"' % True,
                                      ]


            strNode = strTmpNode % (strNodeId,
                                    ",".join(lstNodeAttributes)
                                    )
            self.oDotFile.write(strNode)

        # write ranks (force node to be on the same ranks)
        for strNode, (iT, lstObjIds) in zip(lstTimeStrings, oTracker.getTimePoints().iteritems()):
            #shown_nodeL = [x for x in node_idL if x in self.labelD]
            #tmp = "{%s}\n" % "; ".join(["rank=same", "\"%s\"" % time_node] +
            #                           ["\"%s\"" % self._nodeName(x)
            #                            for x in node_idL])
            tmp = "{%s}\n" % "; ".join(['rank=same'] +
                                       ['"%s"' % oTracker.getNodeIdFromComponents(iT, iObjId)
                                        for iObjId in lstObjIds])
            self.oDotFile.write(tmp)



        self.oDotFile.write("}\n")
        self.oDotFile.close()



    def _traverseGraph(self, strNodeId, level=0):
        oGraph = self.oTracker.getGraph()
        node = oGraph.node_data(strNodeId)
        if strNodeId not in self._dctKnownNodeIds:
#            self.labelD[node_id] = "%s - %d%%\\n%s" %\
#                                   (node.label,
#                                    node.probD[node.label]*100.0,
#                                    node_id)
            #self.labelD[node_id] = "%d (%d)" % (node.id, node.label)
            #self.labelD[node_id] = "%d" % node.id
            self._dctKnownNodeIds[strNodeId] = " "

        for strEdgeId in oGraph.out_arcs(strNodeId):
            strNodeIdN = oGraph.tail(strEdgeId)

            # since merges are possible, a node reachable more than one time
            # -> store all edges (combined node ids) and follow them only once
            strKey = "%s--%s" % (strNodeId, strNodeIdN)
            if not strKey in self._dctEdges:
                self._dctEdges[strKey] = 1
                self._writeEdge(strNodeId, strNodeIdN)
                self._traverseGraph(strNodeIdN, level+1)

    def _writeEdge(self, strNodeId, strNodeIdN):
        self.oDotFile.write('"%s" -> "%s"%s;\n' % \
                            (strNodeId, strNodeIdN, self.EDGE_STYLE))




class CellTracker(OptionManager):

    OPTIONS = {"oMetaData"                  : Option(None),
               "P"                          : Option(None),
               "origP"                      : Option(None),
               "strPathOut"                 : Option(None),
               "fMaxObjectDistance"         : Option(None),
               "iMaxSplitObjects"           : Option(None),
               "oTimeHolder"                : Option(None),
               "iMaxTrackingGap"            : Option(5),
               "bVisualize"                 : Option(False),
               "tplRenderInfo"              : Option(None),
               }

    __slots__ = ['_oGraph',
                 '_channelId',
                 '_dctTimePoints',
                 '_dctTimeChannels',
                 '_dctImageFilenames',
                 'dctVisitorData',
                 ]

    def __init__(self, **dctOptions):
        super(CellTracker, self).__init__(**dctOptions)
        self.oMetaData = self.getOption('oMetaData')
        self.P = self.getOption('P')
        self.origP = self.getOption('origP')
        #print "mooooo", self.iP
        self.strPathOut = self.getOption('strPathOut')

        self._dctTimeChannels = self.getOption('oTimeHolder')
        self._oGraph = None
        self._channelId = None
        self._dctTimePoints = None
        self.dctVisitorData = None
        self.oLogger = logging.getLogger(self.__class__.__name__)


    def __getstate__(self):
        dctSlots = {}
        dctSlots.update(super(CellTracker, self).__getstate__())
        dctSlots.update(get_slot_values(self))
        return dctSlots

    def __setstate__(self, state):
        super(CellTracker, self).__setstate__(state)
        set_slot_values(self, state)
        # FIXME:
        self.oMetaData = self.getOption('oMetaData')
        self.P = self.getOption('P')
        self.origP = self.getOption('origP')
        self.strPathOut = self.getOption('strPathOut')
        self._dctTimeChannels = self.getOption('oTimeHolder')
        self.oLogger = logging.getLogger(self.__class__.__name__)

    def __copy__(self):
        oInstance = self.__class__(**self.getAllOptions())
        oInstance._dctTimeChannels = self._dctTimeChannels.copy()
        # careful here: we want to copy the list of node IDs for every T but
        # we don't want to duplicate the channel data and ImageObjects
        oInstance._dctTimePoints = self._dctTimePoints.deepcopy()
        oInstance._oGraph = Graph()
        oInstance._oGraph.copy(self._oGraph)
        return oInstance

    def copy(self, channelId=None):
        tracker = self.__copy__()
        if not channelId is None and channelId != self._channelId:
            tracker._channelId = channelId
            g = tracker._oGraph
            for nodeId in g.node_list():
                t, objId = self.getComponentsFromNodeId(nodeId)
                channel = self._dctTimeChannels[t][channelId]
                region = channel._dctRegions.values()[0]
                g.update_node_data(nodeId, region[objId])
        return tracker

    def getValidTimeLimits(self, iStart=None, iEnd=None):
        try:
            if iStart is None:
                if not self._dctTimePoints is None:
                    iStart = self._dctTimePoints.keys()[0]
                else:
                    iStart = self._dctTimeChannels.keys()[0]
            if iEnd is None:
                if not self._dctTimePoints is None:
                    iEnd = self._dctTimePoints.keys()[-1]
                else:
                    iEnd = self._dctTimeChannels.keys()[-1]
        except IndexError:
            iStart = 0
            iEnd = -1
        return iStart, iEnd

    def getGraph(self):
        return self._oGraph

    def getTimePoints(self):
        return self._dctTimePoints

    def trackObjects(self, strChannelId, strRegionName, iStart=None, iEnd=None):

        if self.getOption('bVisualize'):
            lstImageFilenames = collect_files(os.path.join(self.strPathOut, os.pardir, '_images',
                                                           self.getOption('tplRenderInfo')[0]),
                                             ['.png', '.jpg'])
            reTime = re.compile('T(\d+)')
            self._dctImageFilenames = OrderedDict()
            for filename in lstImageFilenames:
                oSearch = reTime.search(os.path.split(filename)[1])
                if not oSearch is None:
                    iT = int(oSearch.groups()[0])
                    self._dctImageFilenames[iT] = filename

        self._channelId = strChannelId
        self._oGraph = Graph()
        iStart, iEnd = self.getValidTimeLimits(iStart=iStart, iEnd=iEnd)
        self._dctTimePoints = OrderedDict()

        for iT in range(iStart, iEnd+1):
            if iT in self._dctTimeChannels:
                #print "moo", iT, iStart, iEnd
                oChannel = self._dctTimeChannels[iT][strChannelId]
                #print iT, self._dctTimeChannels[iT]
                self.lstFeatureNames = oChannel.lstFeatureNames

                # does Region exist for that time-point?
                # (yes: segmentation was successfully applied)
                if strRegionName in oChannel._dctRegions:
                    #print "  ", strRegionName
                    oObjectHolder = oChannel._dctRegions[strRegionName]
                    for iObjId, oImageObject in oObjectHolder.iteritems():
                        strNodeId = self.getNodeIdFromComponents(iT, iObjId)
                        self._oGraph.add_node(strNodeId, oImageObject)
                        if not iT in self._dctTimePoints:
                            self._dctTimePoints[iT] = []
                        self._dctTimePoints[iT].append(iObjId)
                    if iT > iStart:
                        self._connectTimePoints(iT)

    def initTrackingAtTimepoint(self, strChannelId, strRegionName):
        self._channelId = strChannelId
        self._regionName = strRegionName
        self._oGraph = Graph()
        self._dctTimePoints = OrderedDict()

    def trackAtTimepoint(self, iT):
        oChannel = self._dctTimeChannels[iT][self._channelId]
        self.lstFeatureNames = oChannel.lstFeatureNames
        oObjectHolder = oChannel._dctRegions[self._regionName]
        for iObjId, oImageObject in oObjectHolder.iteritems():
            strNodeId = self.getNodeIdFromComponents(iT, iObjId)
            self._oGraph.add_node(strNodeId, oImageObject)
            dict_append_list(self._dctTimePoints, iT, iObjId)
        #if len(self._dctTimePoints) > 1:
        self._connectTimePoints(iT)

    def _getClosestPreviousT(self, iT):
        iResultT = None
        iTries = 0
        iMaxGap = self.getOption('iMaxTrackingGap')
        start = self.getValidTimeLimits()[0]
        while iResultT is None and iTries < iMaxGap and iT > start:
            iT -= 1
            if iT in self._dctTimePoints:
                iResultT = iT
            else:
                iTries += 1
        return iResultT

    def _connectTimePoints(self, iT):

        fMaxObjectDistanceSquared = float(self.getOption('fMaxObjectDistance')) ** 2
        iMaxSplitObjects = self.getOption('iMaxSplitObjects')

        bReturnSuccess = False
        oGraph = self._oGraph

        # search all nodes in the previous frame
        iPreviousT = self._getClosestPreviousT(iT)

        if not iPreviousT is None:
            bReturnSuccess = True
            dctMerges = {}
            dctSplits = {}

            # for all nodes in this layer
            for iObjIdP in self._dctTimePoints[iPreviousT]:

                strNodeIdP = self.getNodeIdFromComponents(iPreviousT, iObjIdP)
                oImageObjectP = oGraph.node_data(strNodeIdP)

                lstNearest = []

                for iObjIdC in self._dctTimePoints[iT]:
                    strNodeIdC = self.getNodeIdFromComponents(iT, iObjIdC)
                    oImageObjectC = oGraph.node_data(strNodeIdC)
                    dist = oImageObjectC.squaredMagnitude(oImageObjectP)

                    # take all candidates within a certain distance
                    if dist < fMaxObjectDistanceSquared:
                        lstNearest.append((dist, strNodeIdC))

                if len(lstNearest) > 0:
                    # sort ascending by distance (first tuple element)
                    lstNearest.sort(key=lambda x: x[0])

                    # take only a certain number as merge candidates (the N closest)
                    for dist, strNodeIdC in lstNearest[:iMaxSplitObjects]:
                        dict_append_list(dctMerges, strNodeIdC,
                                         (dist, strNodeIdP))
                        dict_append_list(dctSplits, strNodeIdP,
                                         (dist, strNodeIdC))

            # prevent split and merge for one node at the same time
            for id_c in dctMerges:
                nodes = dctMerges[id_c]
                if len(nodes) == 1:
                    oGraph.add_edge(nodes[0][1], id_c)
                else:
                    for dist, id_p in nodes:
                        if len(dctSplits[id_p]) == 1:
                            oGraph.add_edge(id_p, id_c)



            if self.getOption('bVisualize'):

                img = ccore.readRGBImage(self._dctImageFilenames[iT])
                for objIdP in self._dctTimePoints[iPreviousT]:
                    nodeIdP = self.getNodeIdFromComponents(iPreviousT, objIdP)
                    objP = oGraph.node_data(nodeIdP)

                    for edgeId in oGraph.out_arcs(nodeIdP):
                        nodeIdC = oGraph.tail(edgeId)
                        objC = oGraph.node_data(nodeIdC)

                        x1 = objP.oCenterAbs[0]
                        y1 = objP.oCenterAbs[1]
                        x2 = objC.oCenterAbs[0]
                        y2 = objC.oCenterAbs[1]
                        if (x1 == x2 and y1 == y2):
                            x1 += 1
                        ccore.drawLine(ccore.Diff2D(x1, y1),
                                       ccore.Diff2D(x2, y2),
                                       img, ccore.RGBValue(255,0,0),
                                       thick=True)


                pathOut = os.path.join(self.strPathOut, '_visualize')
                safe_mkdirs(pathOut)
                ccore.writeImage(img, os.path.join(pathOut, 'T%05d.jpg' % iT), '89')


        # build edges for merged objects: take all items from reverse map
#        for node_id_prev, node_idTL in mergeD.iteritems():
#            # take only prev_nodes without successor
#            # prevent a crossing of edges between two nodes
#            node_idTL.sort(lambda a,b: cmp(a[0], b[0]))
#            for dist, node_id in node_idTL[:self.iMaxMergeObjects]:
#                self.add_edge(node_id_prev, node_id)

        return bReturnSuccess

    def visualizeTracks(self, iT, size, n=5, thick=True, radius=3):
        img_conn = ccore.Image(*size)
        img_split = ccore.Image(*size)
        min_T = self.getValidTimeLimits()[0]
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
                previous = self._getClosestPreviousT(current)
                if not previous is None:
                    found = True
                    for objIdP in self._dctTimePoints[previous]:
                        nodeIdP = self.getNodeIdFromComponents(previous, objIdP)
                        objP = self._oGraph.node_data(nodeIdP)

                        if self._oGraph.out_degree(nodeIdP) > 1:
                            img = img_split
                        else:
                            img = img_conn

                        for edgeId in self._oGraph.out_arcs(nodeIdP):
                            nodeIdC = self._oGraph.tail(edgeId)
                            objC = self._oGraph.node_data(nodeIdC)
                            ccore.drawLine(ccore.Diff2D(*objP.oCenterAbs),
                                           ccore.Diff2D(*objC.oCenterAbs),
                                           img, col,
                                           thick=thick)
                            ccore.drawFilledCircle(ccore.Diff2D(*objC.oCenterAbs),
                                                   radius, img_conn, col)
            current += 1

        if not found:
            for objId in self._dctTimePoints[iT]:
                nodeId = self.getNodeIdFromComponents(iT, objId)
                obj = self._oGraph.node_data(nodeId)
                ccore.drawFilledCircle(ccore.Diff2D(*obj.oCenterAbs),
                                       radius, img_conn, col)

        return img_conn, img_split

    @staticmethod
    def getNodeIdFromComponents(iT, iObjectId):
        return '%d_%s' % (iT, iObjectId)

    @staticmethod
    def getComponentsFromNodeId(strNodeId):
        iT, iObjectId = map(int, strNodeId.split('_'))
        return iT, iObjectId

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

    def getSubTracker(self, strNodeId, iMaxLevel=None, channelId=None):
        oTrackerCopy = self.copy(channelId=channelId)
        oTrackerCopy.clearByStartId(strNodeId, iMaxLevel)
        return oTrackerCopy

    def exportGraph(self, strDotFilePath, bRunDot=False):
        self._exportGraph(self, strDotFilePath, bRunDot=bRunDot)

    def exportSubGraph(self, strDotFilePath, strStartId, iMaxLevel=None, bRunDot=False, channelId=None):
        tracker = self.getSubTracker(strStartId, iMaxLevel=iMaxLevel, channelId=channelId)
        tracker.exportGraph(strDotFilePath, bRunDot=bRunDot)

    def forwardReachable(self, node_id, reachableD, edgeD, iMaxLevel=None, iLevel=0):
        oGraph = self._oGraph
        reachableD[node_id] = True
        #print node_id
        #print "     out:", self.out_arcs(node_id)
        #print "      in:", self.in_arcs(node_id)

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

#        if lstRootIds is None:
#            iStart, iEnd = self.getValidTimeLimits(iStart, iEnd)
#            if iEnd > -1:
#                lstRootIds = [self.getNodeIdFromComponents(iStart, iObjectId)
#                              for iObjectId in self._dctTimePoints[iStart]]
#                self.oLogger.debug("tracking: start nodes %d %s" %
#                                   (len(lstRootIds), lstRootIds))
#            else:
#                lstRootIds = []
#                self.oLogger.warning("tracking: no time-points found for this video.")
#
#        self.dctVisitorData = {}
#        for strRootId in lstRootIds:
#            self.dctVisitorData[strRootId] = {}
#            self.oLogger.debug("root ID %s" % strRootId)
#            dctEdges = {}
#            self._forwardVisitor(strRootId, self.dctVisitorData[strRootId], dctEdges)

        # find all starting tracks and use them for further analysis.
        # multiple traversing of one track is prevented by 'dctEdges', so that no
        # outgoing node ID can be touched twice

        if lstRootIds is None:
            # find all start tracks (without incoming edges)
            lstStartIds = [strNodeId for strNodeId in self._oGraph.node_list()
                           if self._oGraph.in_degree(strNodeId) == 0]
            # sort by time
            lstStartIds.sort(key = lambda x: self.getComponentsFromNodeId(x)[0])
        else:
            lstStartIds = lstRootIds

        self.oLogger.debug("tracking: start nodes %d %s" %
                           (len(lstStartIds), lstStartIds))

        self.dctVisitorData = {}

        dctVisitedNodes = {}
        for strStartId in lstStartIds:
            self.dctVisitorData[strStartId] = {'_current': 0,
                                               '_full'   : [[]],
                                               }
            self.oLogger.debug("root ID %s" % strStartId)
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

##         # find broken links
##         broken_outL = []
##         broken_inL = []
##         time_pointL = self.node_timeD.keys()
##         for time_point, node_idL in self.node_timeD.iteritems():
##             for node_id in node_idL:
##                 if (time_point != max(time_pointL) and
##                     len(self.out_arcs(node_id)) == 0):
##                     broken_outL.append((time_point, node_id))
##                 if (time_point != min(time_pointL) and
##                     len(self.in_arcs(node_id)) == 0):
##                     broken_inL.append((time_point, node_id))

##         # bridge the broken links (which are shorter than MAX_OBJECT_DISTANCE)
##         for time_point_out, node_id_out in broken_outL:
##             for time_point_in, node_id_in in broken_inL:
##                 if (node_id_out != node_id_in and
##                     time_point_out < time_point_in and
##                     time_point_in-time_point_out <= self.MAX_LINK_BRIDGE_TIME):
##                     obj_out = self.node_data(node_id_out)
##                     obj_in = self.node_data(node_id_in)
##                     dist = obj_in.distance(obj_out)
##                     if dist < self.MAX_OBJECT_DISTANCE:
##                         dataD = {'broken link': True}
##                         self.add_edge(node_id_out, node_id_in, dataD)

#        print "*** old graph id: %s, levels: %d, nodes %d\n" %\
#                  (self,
#                   len(self.node_timeD),
#                   len(self.node_list())
#                   )


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
                #else:
                #    print "moo", time_point, node_id

#        print "moo2"
#        print "*** new graph id: %s, levels: %d, nodes %d\n" %\
#                  (self,
#                   len(self.node_timeD),
#                   len(self.node_list())
#                   )

##         # filter merges close to border
##         for node_id in self.node_timeD[1]:
##             self.forward_traversal(node_id, functor=self.functor_reachable)


##                     # if center is MIN_DISTANCE_FROM_BORDER away
##             if (self.time_point > 1 or
##                 (s_obj.centerT[0] > self.MIN_DISTANCE_FROM_BORDER and
##                  s_obj.centerT[1] > self.MIN_DISTANCE_FROM_BORDER and
##                  s_obj.centerT[0] < min_x_from_border and
##                  s_obj.centerT[1] < min_y_from_border)):



        # delete all nodes which disappear without being in apoptosis


        # fix merges for short shapeI phases (segmentation errors)

    def clearByObjects(self, iStart, lstObjIds, iMaxLevel=None):
        """
        remove all nodes from first timepoint which are not in the list
        """
        #iStart, iEnd = self.getTimePoints()
        for iObjId in self._dctTimePoints[iStart][:]:
            #s_obj = self.node_data(node_id)
            if not iObjId in lstObjIds:
                self._dctTimePoints[iStart].remove(iObjId)

        # find all nodes which are reachable from the first timepoint
        dctReachable = {}
        for iObjId in self._dctTimePoints[iStart][:]:
            strStartId = self.getNodeIdFromComponents(iStart, iObjId)
            self.forwardReachable(strStartId, dctReachable, {}, iMaxLevel=iMaxLevel)

        # remove all nodes from the entire graph which are not reachable
        lstNodes = self._oGraph.node_list()
        for strNodeId in lstNodes:
            if not strNodeId in dctReachable:
                self._oGraph.delete_node(strNodeId)
                iT, iObjId = self.getComponentsFromNodeId(strNodeId)
                if iObjId in self._dctTimePoints[iT]:
                    self._dctTimePoints[iT].remove(iObjId)


    def clearByStartId(self, strStartId, iMaxLevel):
        dctReachable = {}
        self.forwardReachable(strStartId, dctReachable, {}, iMaxLevel=iMaxLevel)
        # remove all nodes from the entire graph which are not reachable
        for strNodeId in self._oGraph.node_list()[:]:
            if not strNodeId in dctReachable:
                #print " * node not reachable", node_id
                self._oGraph.delete_node(strNodeId)
                iT, iObjId = self.getComponentsFromNodeId(strNodeId)
                if iObjId in self._dctTimePoints[iT]:
                    self._dctTimePoints[iT].remove(iObjId)
        for iT in self._dctTimePoints.keys():
            if len(self._dctTimePoints[iT]) == 0:
                del self._dctTimePoints[iT]
                del self._dctTimeChannels[iT]



class PlotCellTracker(CellTracker):

    OPTIONS = {"bExportRootGraph"            : Option(False, doc=""),
               "bRenderRootGraph"            : Option(False, doc=""),
               "bExportSubGraph"             : Option(False, doc=""),
               "bRenderSubGraph"             : Option(False, doc=""),
               "bPlotterUseCairo"            : Option(False, doc=""),
               "bHasClassificationData"      : Option(False, doc=""),
               "bExportTrackFeatures"        : Option(False, doc=""),
               "bExportFlatFeatures"         : Option(False, doc=""),
               "featureCompression"          : Option(None, doc=""),
               "flatFeatureCompression"      : Option(None, doc=""),
               }

    FEATURE_FLAT_PATTERN = "feature__%s"
    CLASS_FLAT_PATTERN = "class__%s"
    TRACKING_FLAT_PATTERN = "tracking__%s"
    FEATURE_COLUMN_PATTERN = "feature__%s__%s"
    TRACKING_COLUMN_PATTERN = "tracking__%s__%s"
    CLASS_COLUMN_PATTERN = "class__%s__%s"
    OBJID_COLUMN_PATTERN = "objId__%s"

    def __init__(self, **dctOptions):
        super(PlotCellTracker, self).__init__(**dctOptions)
        self.dctVisitorData = {}

    def eventIterator(self):
        for strRootId, dctTrackResults in self.dctVisitorData.iteritems():
            for strStartId, dctEventData in dctTrackResults.iteritems():
                yield strStartId, dctEventData

    def getBoundingBoxes(self, method="objectCentered", size=None, border=0):
        dctBoundingBoxes = {}
        for strStartId, dctEventData in self.eventIterator():
            if strStartId in ['_full', '_current']:
                continue
            if method == "objectCentered":
                lstData = []
                for tplNodeIds in zip(*dctEventData['tracks']):
                    #print tplNodeIds
                    strNodeId = tplNodeIds[0]
                    iT = self.getComponentsFromNodeId(strNodeId)[0]
                    lstObjIds = [self.getComponentsFromNodeId(strNodeId)[1]
                                 for strNodeId in tplNodeIds]
                    lstImageObjects = [self._oGraph.node_data(strNodeId)
                                       for strNodeId in tplNodeIds]
                    minX = min([obj.oRoi.upperLeft[0] for obj in lstImageObjects])
                    minY = min([obj.oRoi.upperLeft[1] for obj in lstImageObjects])
                    maxX = max([obj.oRoi.lowerRight[0] for obj in lstImageObjects])
                    maxY = max([obj.oRoi.lowerRight[1] for obj in lstImageObjects])
                    width  = maxX - minX + 1
                    height = maxY - minY + 1
                    centerX = int(round(average([obj.oCenterAbs[0] for obj in lstImageObjects])))
                    centerY = int(round(average([obj.oCenterAbs[1] for obj in lstImageObjects])))
                    lstData.append((iT, centerX, centerY, width, height, lstObjIds))
                aData = array(lstData, 'O')
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
                lstNodeIds = flatten(dctEventData['tracks'])
                lstImageObjects = [self._oGraph.node_data(strNodeId)
                                   for strNodeId in lstNodeIds]
                iMinX = min([oImgObj.oRoi.upperLeft[0] for oImgObj in lstImageObjects])
                iMinY = min([oImgObj.oRoi.upperLeft[1] for oImgObj in lstImageObjects])
                iMaxX = max([oImgObj.oRoi.lowerRight[0] for oImgObj in lstImageObjects])
                iMaxY = max([oImgObj.oRoi.lowerRight[1] for oImgObj in lstImageObjects])

                tplBoundingBox = (iMinX-border, iMinY-border,
                                  iMaxX+border, iMaxY+border)
                lstTimePoints = sorted(unique([self.getComponentsFromNodeId(strNodeId)[0]
                                               for strNodeId in lstNodeIds]))
                lstObjIds = [[self.getComponentsFromNodeId(strNodeId)[1]
                              for strNodeId in tplNodeIds]
                             for tplNodeIds in zip(*dctEventData['tracks'])]
                assert len(lstObjIds) == len(lstTimePoints)
                lstTimeData = zip(lstTimePoints, itertools.cycle([tplBoundingBox], lstObjIds))

            dctBoundingBoxes[strStartId] = lstTimeData
        return dctBoundingBoxes

    def exportFullTracks(self):
        strPathOut = os.path.join(self.strPathOut, 'full')
        if clear_path:
            shutil.rmtree(strPathOut, True)
            safe_mkdirs(strPathOut)



    def analyze(self, dctChannels, channelId=None, clear_path=False):
        #print self.lstChromatinFeatureNames
        #print self.lstSecondaryFeatureNames

        strPathOut = os.path.join(self.strPathOut, 'events')
        if clear_path:
            shutil.rmtree(strPathOut, True)
            safe_mkdirs(strPathOut)

        for strRootId, dctTrackResults in self.dctVisitorData.iteritems():

            self.oLogger.debug("* root %s, candidates %s" % (strRootId, dctTrackResults.keys()))

#            if self.getOption("bExportRootGraph"):
#                self.exportSubGraph(self._formatFilename("graph.dot", nodeId=strRootId, prefix="root_", subPath='_graphs'),
#                                    strRootId,
#                                    bRunDot=self.getOption("bRenderRootGraph"),
#                                    channelId=channelId)

            for strStartId, dctEventData in dctTrackResults.iteritems():

                if strStartId[0] != '_':

    #                if self.getOption("bExportSubGraph"):
    #                    self.exportSubGraph(self._formatFilename("graph.dot", strStartId, subPath='_graphs'),
    #                                        strStartId,
    #                                        iMaxLevel=dctEventData['maxLength'],
    #                                        bRunDot=self.getOption("bRenderSubGraph"),
    #                                        channelId=channelId)

                    if self.getOption("bExportTrackFeatures"):
                        for strChannelId, dctRegions in dctChannels.iteritems():
                            print strChannelId, dctRegions,self._dctTimeChannels.channels
                            if strChannelId in self._dctTimeChannels.channels:
                                for strRegionId, lstFeatureNames in dctRegions.iteritems():

                                    if self.getOption('featureCompression') is None:
                                        strCompression = ''
                                    else:
                                        strCompression = '.%s' % self.getOption('featureCompression')
                                    strFilename = self._formatFilename('C%s__R%s' % (strChannelId, strRegionId),
                                                                       nodeId=strStartId, prefix='features', subPath='events',
                                                                       ext='.txt%s' % strCompression)
                                    self.exportChannelData(dctEventData,
                                                           strFilename,
                                                           strChannelId,
                                                           strRegionId,
                                                           lstFeatureNames)

                    self.oLogger.debug("* root %s ok" % strStartId)

        if self.getOption("bExportFlatFeatures"):
            for strChannelId, dctRegions in dctChannels.iteritems():
                if strChannelId in self._dctTimeChannels.channels:
                    for strRegionId, lstFeatureNames in dctRegions.iteritems():
                        if self.getOption('flatFeatureCompression') is None:
                            strCompression = ''
                        else:
                            strCompression = '.%s' % self.getOption('flatFeatureCompression')
                        strFilename = self._formatFilename('C%s__R%s' % (strChannelId, strRegionId),
                                                            nodeId=strStartId, prefix='_flat_features', subPath='events',
                                                            ext='.txt%s' % strCompression)
                        self.exportChannelDataFlat(strFilename,
                                                   strChannelId,
                                                   strRegionId,
                                                   lstFeatureNames)


    def exportChannelDataFlat(self, strFilename, strChannelId, strRegionId, lstFeatureNames):

        oTable = None
        if not lstFeatureNames is None:
            lstFeatureNames = sorted(lstFeatureNames)

        for iT in self._dctTimeChannels:
            oChannel = self._dctTimeChannels[iT][strChannelId]

            if oChannel.has_region(strRegionId):
                oRegion = oChannel.get_region(strRegionId)

                if len(oRegion) > 0:
                    if lstFeatureNames is None:
                        lstFeatureNames = oRegion.getFeatureNames()

                    if oTable is None:
                        tracking_features = ['center_x','center_y',
                                             'upperleft_x', 'upperleft_y',
                                             'lowerright_x', 'lowerright_y']

                        oTable = newTable(['Frame', 'ObjectID'] +
                                          [self.FEATURE_FLAT_PATTERN % f for f in lstFeatureNames] +
                                          [self.CLASS_FLAT_PATTERN % x for x in ['name', 'label', 'probability']] +
                                          [self.TRACKING_FLAT_PATTERN % x for x in tracking_features],
                                          typeCodes=['i','i'] +
                                                    ['f']*len(lstFeatureNames) +
                                                    ['c','i','f'] +
                                                    ['i'] * len(tracking_features))

                    for iObjId, oObj in oRegion.iteritems():
                        dctData = {'Frame' : iT,
                                   'ObjectID' : iObjId}
                        aFeatures = oRegion.getFeaturesByNames(iObjId, lstFeatureNames)
                        for fFeature, strName in zip(aFeatures, lstFeatureNames):
                            dctData[self.FEATURE_FLAT_PATTERN % strName] = float(fFeature)
                        if self.getOption('bHasClassificationData'):
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

                        oTable.append(dctData)

        if not oTable is None:
            oTable.sort(['Frame', 'ObjectID'])
            exportTable(oTable,
                        strFilename,
                        fieldDelimiter='\t',
                        typeFormatting={FloatType: lambda x: "%E" % x},
                        detectCompression=True,
                        stringDelimiter='')


    def exportChannelData(self, dctEventData, strFilename, strChannelId, strRegionId, lstFeatureNames):
        bHasFeatures = False
        lstChildIds = None

        strEventId = dctEventData['eventId']
        iEventT, iObjId = self.getComponentsFromNodeId(strEventId)

        bHasSplitId = 'splitId' in dctEventData

        lstHeaderNames = ['Frame', 'Timestamp', 'isEvent']
        lstHeaderTypes = ['i', 'f', 'b']
        if bHasSplitId:
            lstHeaderNames.append('isSplit')
            lstHeaderTypes.append('b')
            if not dctEventData['splitId'] is None:
                iSplitT, iObjId = self.getComponentsFromNodeId(dctEventData['splitId'])
            else:
                iSplitT = None

        table = []

        # zip nodes with same time together
        for tplNodes in zip(*dctEventData['tracks']):

            lstObjectIds = []
            iT = None
            for strNodeId in tplNodes:
                iNodeT, iObjId = self.getComponentsFromNodeId(strNodeId)
                if iT is None:
                    iT = iNodeT
                else:
                    assert iT == iNodeT
                lstObjectIds.append(iObjId)

            # FIXME
            if iT is None:
                #print "no tracks found for event '%strEventId'" % strEventId
                return
            elif lstChildIds is None:
                lstChildIds = [chr(65+i) for i in range(len(lstObjectIds))]
            else:
                assert len(lstChildIds) == len(lstObjectIds)

            oChannel = self._dctTimeChannels[iT][strChannelId]
            oRegion = oChannel.get_region(strRegionId)

            if not bHasFeatures:
                bHasFeatures = True
                if lstFeatureNames is None:
                    lstFeatureNames = oRegion.getFeatureNames()
                    #print "moo123", lstFeatureNames

                lstHeaderNames += [self.OBJID_COLUMN_PATTERN % strChild
                                   for strChild in lstChildIds]
                #lstFeatureTypes += ['i'] * len(lstChildIds)

                if self.getOption('bHasClassificationData'):
                    lstHeaderNames += [self.CLASS_COLUMN_PATTERN % (strChild, x)
                                       for strChild in lstChildIds
                                       for x in ['name', 'label', 'probability']]
                    #lstFeatureTypes += ['c', 'i', 'c'] * len(lstChildIds)

                lstHeaderNames += [self.FEATURE_COLUMN_PATTERN % (strChild, strFeatureName)
                                   for strChild in lstChildIds
                                   for strFeatureName in lstFeatureNames]
                #lstFeatureTypes += ['f'] * (len(lstFeatureNames) * len(lstChildIds))

                tracking_features = ['center_x','center_y',
                                     'upperleft_x', 'upperleft_y',
                                     'lowerright_x', 'lowerright_y']
                lstHeaderNames += [self.TRACKING_COLUMN_PATTERN % (strChild, strFeatureName)
                                   for strChild in lstChildIds
                                   for strFeatureName in tracking_features]
                #lstFeatureTypes += ['i'] * (len(tracking_features) * len(lstChildIds))

#                for strColumnName, strTypeCode in zip(lstFeatureColumns,
#                                                      lstFeatureTypes):
#                    oTable.appendColumn(strColumnName, typeCode=strTypeCode)

                #print lstFeatureColumns
                #print lstFeatureTypes

            dctData = {'Frame' : iT,
                       'Timestamp' : self.oMetaData.get_timestamp_relative(self.origP, iT),
                       'isEvent' : 1 if iT == iEventT else 0,
                       }
            if bHasSplitId:
                dctData['isSplit'] = 1 if iT == iSplitT else 0

            #print iT, strChannelId, strRegionId, lstObjectIds
            for iIdx, iObjId in enumerate(lstObjectIds):
                if iObjId in oRegion:
                    oObj = oRegion[iObjId]

                    dctData[self.OBJID_COLUMN_PATTERN % lstChildIds[iIdx]] = iObjId

                    # classification data
                    if self.getOption('bHasClassificationData'):
                        dctData[self.CLASS_COLUMN_PATTERN % (lstChildIds[iIdx], 'label')] = oObj.iLabel
                        dctData[self.CLASS_COLUMN_PATTERN % (lstChildIds[iIdx], 'name')] = oObj.strClassName
                        dctData[self.CLASS_COLUMN_PATTERN % (lstChildIds[iIdx], 'probability')] =\
                            ','.join(['%d:%.5f' % (int(x),y) for x,y in oObj.dctProb.iteritems()])

                    # object features
                    aFeatures = oRegion.getFeaturesByNames(iObjId, lstFeatureNames)
                    for fFeature, strFeatureName in zip(aFeatures, lstFeatureNames):
                        dctData[self.FEATURE_COLUMN_PATTERN % (lstChildIds[iIdx], strFeatureName)] = fFeature

                    # object tracking data (absolute center)
                    dctData[self.TRACKING_COLUMN_PATTERN % (lstChildIds[iIdx], 'center_x')] = oObj.oCenterAbs[0]
                    dctData[self.TRACKING_COLUMN_PATTERN % (lstChildIds[iIdx], 'center_y')] = oObj.oCenterAbs[1]
                    dctData[self.TRACKING_COLUMN_PATTERN % (lstChildIds[iIdx], 'upperleft_x')] = oObj.oRoi.upperLeft[0]
                    dctData[self.TRACKING_COLUMN_PATTERN % (lstChildIds[iIdx], 'upperleft_y')] = oObj.oRoi.upperLeft[1]
                    dctData[self.TRACKING_COLUMN_PATTERN % (lstChildIds[iIdx], 'lowerright_x')] = oObj.oRoi.lowerRight[0]
                    dctData[self.TRACKING_COLUMN_PATTERN % (lstChildIds[iIdx], 'lowerright_y')] = oObj.oRoi.lowerRight[1]

            #print dctData
            table.append(dctData)

        write_table(strFilename, table, column_names=lstHeaderNames)


    def _forwardVisitor(self, strNodeId, dctResults, dctEdges, iLevel=0, strStartId=None):
        oGraph = self._oGraph
        oObject = oGraph.node_data(strNodeId)

        if strStartId is None:
            strStartId = strNodeId
            dctResults[strStartId] = {'eventId'  : strNodeId,
                                      'maxLength': 0,
                                      'tracks'   : [[]],
                                      }
            self.oLogger.debug("%s - valid candidate" % strStartId)

        dctResults[strStartId]['tracks'][0].append(strNodeId)
        dctResults[strStartId]['maxLength'] += 1

        for strOutEdgeId in oGraph.out_arcs(strNodeId):
            strTailId = oGraph.tail(strOutEdgeId)
            # ignore merging nodes
            strKey = "%s--%s" % (strNodeId, strTailId)
            if strKey not in dctEdges:
                dctEdges[strKey] = True
                self._forwardVisitor(strTailId, dctResults, dctEdges, iLevel=iLevel+1, strStartId=strStartId)

#    def analyze(self):
#
#        from rpy import r
#
#        oPlotter = RPlotter(bUseCairo=self.getOption("bPlotterUseCairo"))
#        for strRootId, dctTrackResults in self.dctVisitorData.iteritems():
#
#            if self.getOption("bExportRootGraph"):
#                self.exportSubGraph(self._formatFilename("graph.dot", strRootId),
#                                    strRootId,
#                                    bRunDot=self.getOption("bRenderRootGraph"))
#
#            if 'chromatin' in dctTrackResults:
#                aChromatin = array(dctTrackResults['chromatin'])
#
#                if self.getOption("bChromatinCreateTrackFiles"):
#                    oTable = newTable(range(len(self.getOption("lstChromatinFeatureNames"))),
#                                      data=aChromatin,
#                                      columnLabels=self.getOption("lstChromatinFeatureNames"))
#                    exportTable(oTable,
#                                self._formatFilename("chromatin.dat", strRootId),
#                                fieldDelimiter="\t",
#                                writeColumnKeys=True,
#                                writeRowLabels=False,
#                                stringDelimiter="",
#                                useLabelsAsKeys=True)
#
#                if self.getOption("bChromatinCreateTrackImages"):
#                    oPlotter.figure(strFilename=self._formatFilename("chromatin.png", strRootId), width=900, height=600)
#                    aChromatin2 = (aChromatin - min(aChromatin,0)) / (max(aChromatin,0) - min(aChromatin,0))
#                    oPlotter.par(mar=(2.5, 0.5, 0.5, 5))
#                    oPlotter.image(range(len(aChromatin2)),
#                                   range(len(aChromatin2[0])),
#                                   aChromatin2, axes=False,
#                                   ylab="features", xlab="frames",
#                                   zlim=(0,1), col=r.heat_colors(100))
#                    oPlotter.box()
#                    oPlotter.axis(1, range(len(aChromatin2)),
#                                  labels=map(str, range(1,len(aChromatin2)+1)),
#                                  las=1, cex=0.9, tick=1)
#                    oPlotter.axis(4, range(len(aChromatin2[0])),
#                                  labels=self.getOption("lstChromatinFeatureNames"),
#                                  las=2, tick=1, cex=0.9)
#                    oPlotter.close()
#
#
#            if 'secondary' in dctTrackResults:
#                aSecondary = array(dctTrackResults['secondary'])
#
#                if self.getOption("bSecondaryCreateTrackFiles"):
#                    oTable = newTable(range(len(self.getOption("lstSecondaryFeatureNames"))),
#                                      data=aSecondary,
#                                      columnLabels=self.getOption("lstSecondaryFeatureNames"))
#                    exportTable(oTable,
#                                self._formatFilename("secondary.dat", strRootId),
#                                fieldDelimiter="\t",
#                                writeColumnKeys=True,
#                                writeRowLabels=False,
#                                stringDelimiter="",
#                                useLabelsAsKeys=True)
#
#                if self.getOption("bSecondaryCreateTrackImages"):
#                    dctData = {}
#                    for iIdx, strFeatureName in enumerate(self.getOption("lstSecondaryFeatureNames")):
#                        dctData[strFeatureName] = aSecondary[:,iIdx]
#
#                    tplYRange = r.range(dctData['second_in_avg'],
#                                        dctData['second_out_avg'])
#
#                    if 'nan' not in [str(x).lower() for x in tplYRange]:
#
#                        oPlotter.figure(strTitle="Timeseries",
#                                        strFilename=self._formatFilename("secondary.png", strRootId))
#
#                        r.plot(dctData['second_in_avg'], type='b', col='red', lwd=2,
#                               xlab='Frames',
#                               ylab='Secondary Intensity',
#                               ylim=tplYRange)
#                        r.grid()
#                        r.lines(dctData['second_out_avg'], type='b', col='green', lwd=2,
#                                ylim=tplYRange)
#                        r.legend(1, tplYRange[0],
#                                 legend=('in avg', 'out avg'),
#                                 fill=('red', 'green'),
#                                 xjust=0, yjust=0)
#
#                        oPlotter.close()


    def _formatFilename(self, strSuffix=None, nodeId=None, prefix=None, subPath=None, branchId=None, ext='.txt'):
        lstParts = []
        if not prefix is None:
            lstParts.append(prefix)
        lstParts.append('P%s' % self.P)
        if not nodeId is None:
            items = self.getComponentsFromNodeId(nodeId)
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
            strPathOut = os.path.join(self.strPathOut, subPath)
            safe_mkdirs(strPathOut)
        else:
            strPathOut = self.strPathOut
        return os.path.join(strPathOut, strParts) + ext



class SplitCellTracker(PlotCellTracker):

    OPTIONS = {"iForwardRange"           :   Option(None, doc=""),
               "iBackwardRange"          :   Option(None, doc=""),
               }

    def __init__(self, **dctOptions):
        super(SplitCellTracker, self).__init__(**dctOptions)
        self.bRunDotCmdRoot = False

    def _backwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if iLevel > 1 and oGraph.out_degree(strNodeId) != 1:
            #logging.debug("mooo out")
            return False
        # check for split
        if oGraph.in_degree(strNodeId) != 1:
            #logging.debug("mooo in")
            return False
        if iLevel >= self.getOption('iBackwardRange'):
            return True
        strInEdgeId = oGraph.in_arcs(strNodeId)[0]
        assert len(oGraph.in_arcs(strNodeId)) == 1
        strHeadId = oGraph.head(strInEdgeId)
        return self._backwardCheck(strHeadId, lstNodeIds, iLevel=iLevel+1)

    def _forwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if oGraph.in_degree(strNodeId) != 1:
            return False
        # check for split
        if oGraph.out_degree(strNodeId) != 1:
            return False
        if iLevel >= self.getOption('iForwardRange'):
            return True
        strOutEdgeId = oGraph.out_arcs(strNodeId)[0]
        strTailId = oGraph.tail(strOutEdgeId)
        return self._forwardCheck(strTailId, lstNodeIds, iLevel=iLevel+1)

    def _forwardVisitor(self, strNodeId, dctResults, dctVisitedNodes, iLevel=0):
        oGraph = self._oGraph
        oObject = oGraph.node_data(strNodeId)

        self.oLogger.debug('_forwardVisitor nodeId=%s level=%d' % (strNodeId, iLevel))

        if oGraph.out_degree(strNodeId) == 2 and oGraph.in_degree(strNodeId) == 1: # and oObject.iLabel in [2,3,4,5,6,7]:
            bCandidateOk = True
            self.oLogger.debug("%s - found n=2" % strNodeId)
#            for strOutEdgeId in self.out_arcs(strNodeId):
#                strOutTailId = self.tail(strOutEdgeId)
#                oTailObject = self.node_data(strOutTailId)
#                #if oTailObject.iLabel not in [6,7]:
#                #    bCandidateOk = False

            if bCandidateOk:
                lstBackwardNodeIds = []
                bCandidateOk = self._backwardCheck(strNodeId, lstBackwardNodeIds)
                self.oLogger.debug("%s - backwards %s    %s" % (strNodeId, {True: 'ok', False: 'failed'}[bCandidateOk], lstBackwardNodeIds))

            lstForwardNodeIds = [[],[]]
            dctNodeIds = {}
            for iCnt, strOutEdgeId in enumerate(oGraph.out_arcs(strNodeId)):
                if bCandidateOk:
                    strTailId = oGraph.tail(strOutEdgeId)
                    bCandidateOk = self._forwardCheck(strTailId, lstForwardNodeIds[iCnt])
                    self.oLogger.debug("%s - forwards %s %s" % (strNodeId, ['A','B'][iCnt], {True: 'ok', False: 'failed'}[bCandidateOk]))

            if bCandidateOk:

                lstBackwardNodeIds.reverse()
                strStartId = lstBackwardNodeIds[0]

                lstTrackA = lstBackwardNodeIds + lstForwardNodeIds[0]
                lstTrackB = lstBackwardNodeIds + lstForwardNodeIds[1]
                #assert len(lstTrackA) == len(lstTrackB)
                dctResults[strStartId] = {'eventId'  : strNodeId,
                                          'maxLength': len(lstTrackA),
                                          'tracks'   : [lstTrackA, lstTrackB],
                                          }
                self.oLogger.debug("%s - valid candidate" % strStartId)

        self.oLogger.debug("outdegree=%d, outarcs=%s, level=%d" %\
                           (len(oGraph.out_arcs(strNodeId)), oGraph.out_arcs(strNodeId), iLevel))
        for strOutEdgeId in oGraph.out_arcs(strNodeId):
            strTailId = oGraph.tail(strOutEdgeId)
            if strTailId not in dctVisitedNodes:
                dctVisitedNodes[strTailId] = True
                self._forwardVisitor(strTailId, dctResults, dctVisitedNodes, iLevel=iLevel+1)

class SplitCellTrackerExt(SplitCellTracker):

    def __init__(self, **dctOptions):
        super(SplitCellTrackerExt, self).__init__(**dctOptions)
        self.bRunDotCmdRoot = False

    def _backwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if iLevel < self.getOption('iBackwardCheck'):
            if iLevel > 1 and oGraph.out_degree(strNodeId) != 1:
                #logging.debug("mooo out")
                return False
            # check for split
            if oGraph.in_degree(strNodeId) != 1:
                #logging.debug("mooo in")
                return False
        if len(oGraph.in_arcs(strNodeId)) > 0:
            strInEdgeId = oGraph.in_arcs(strNodeId)[0]
            #assert len(oGraph.in_arcs(strNodeId)) == 1
            strHeadId = oGraph.head(strInEdgeId)
            return self._backwardCheck(strHeadId, lstNodeIds, iLevel=iLevel+1)
        else:
            return True

    def _forwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if iLevel < self.getOption('iForwardCheck'):
            if oGraph.in_degree(strNodeId) != 1:
                return False
            # check for split
            if oGraph.out_degree(strNodeId) != 1:
                return False

        if len(oGraph.out_arcs(strNodeId)) > 0:
            strOutEdgeId = oGraph.out_arcs(strNodeId)[0]
            strTailId = oGraph.tail(strOutEdgeId)
            return self._forwardCheck(strTailId, lstNodeIds, iLevel=iLevel+1)
        else:
            return True

class NoSplitCellTrackerExt(PlotCellTracker):

    def __init__(self, **dctOptions):
        super(NoSplitCellTrackerExt, self).__init__(**dctOptions)
        self.bRunDotCmdRoot = False

    def _forwardVisitor(self, strNodeId, dctResults, dctEdges, iLevel=0):
        oGraph = self._oGraph
        oObject = oGraph.node_data(strNodeId)

        if oGraph.out_degree(strNodeId) == 1:
            bCandidateOk = True
            self.oLogger.debug("%s - found n=1" % strNodeId)

            lstForwardNodeIds = []
            strTailId = oGraph.tail(oGraph.out_arcs(strNodeId)[0])
            bCandidateOk = self._forwardCheck(strTailId, lstForwardNodeIds)
            self.oLogger.debug("%s - forwards %s" % (strNodeId, {True: 'ok', False: 'failed'}[bCandidateOk]))

            if bCandidateOk:

                strStartId = lstForwardNodeIds[0]
                lstTrackA = lstForwardNodeIds
                dctResults[strStartId] = {'eventId'  : strStartId,
                                          'maxLength': len(lstTrackA),
                                          'tracks'   : [lstTrackA],
                                          }
                self.oLogger.debug("%s - valid candidate" % strStartId)

#        for strOutEdgeId in oGraph.out_arcs(strNodeId):
#            strTailId = oGraph.tail(strOutEdgeId)
#
#            #print " "*iLevel, strTailId
#
#            # ignore merging nodes
#            strKey = "%s--%s" % (strNodeId, strTailId)
#            if strKey not in dctEdges:
#                dctEdges[strKey] = True
#                self._forwardVisitor(strTailId, dctResults, dctEdges, iLevel=iLevel+1)

    def _forwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if oGraph.in_degree(strNodeId) != 1:
            return False
        # check for split
        if oGraph.out_degree(strNodeId) > 1:
            return False

        if oGraph.out_degree(strNodeId) > 0:
            strTailId = oGraph.tail(oGraph.out_arcs(strNodeId)[0])
            return self._forwardCheck(strTailId, lstNodeIds, iLevel=iLevel+1)
        else:
            return True


class ClassificationCellTracker(SplitCellTracker):

    OPTIONS = {"lstForwardLabels"        :   Option(None, doc=""),
               "lstBackwardLabels"       :   Option(None, doc=""),
               "iMaxInDegree"            :   Option(None, doc=""),
               "iMaxOutDegree"           :   Option(None, doc=""),
               "lstLabelTransitions"     :   Option(None),
               "bFollowOnlyOneCell"      :   Option(False),
               "bAllowOneDaughterCell"   :   Option(False),
               "iBackwardCheck"          :   Option(None, doc=""),
               "iForwardCheck"           :   Option(None, doc=""),

               "bForwardRangeMin"        :   Option(False, doc=""),
               "bBackwardRangeMin"       :   Option(False, doc=""),
               }

    def __init__(self, **dctOptions):
        super(ClassificationCellTracker, self).__init__(**dctOptions)
        self.bRunDotCmdRoot = False

    def _backwardCheck(self, strNodeId, lstNodeIds, iLevel=1):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if ((self.getOption('iBackwardRange') == -1 and oGraph.in_degree(strNodeId) == 0) or
            (self.getOption('bBackwardRangeMin') and iLevel >= self.getOption('iBackwardRange') and oGraph.in_degree(strNodeId) == 0) or
            (not self.getOption('bBackwardRangeMin') and iLevel >= self.getOption('iBackwardRange'))):
            return True
        if oGraph.out_degree(strNodeId) != 1:
            #logging.debug("     mooo out")
            return False
        # check for split
        if oGraph.in_degree(strNodeId) != 1:
            #logging.debug("     mooo in")
            return False

        oObject = oGraph.node_data(strNodeId)
        if iLevel > 1 and iLevel-1 <= self.getOption('iBackwardCheck') and not oObject.iLabel in self.getOption('lstBackwardLabels'):
            #logging.debug("     mooo label %d" % oObject.iLabel)
            return False

        strInEdgeId = oGraph.in_arcs(strNodeId)[0]
        #assert oGraph.in_arcs(strNodeId)) == 1
        strHeadId = oGraph.head(strInEdgeId)
        return self._backwardCheck(strHeadId, lstNodeIds, iLevel=iLevel+1)

    def _forwardCheck(self, strNodeId, lstNodeIds, iLevel=1, strFoundSplitId=None):
        oGraph = self._oGraph
        lstNodeIds.append(strNodeId)
        if ((self.getOption('iForwardRange') == -1 and oGraph.out_degree(strNodeId) == 0) or
            (self.getOption('bForwardRangeMin') and iLevel >= self.getOption('iForwardRange') and oGraph.out_degree(strNodeId) == 0) or
            (not self.getOption('bForwardRangeMin') and iLevel >= self.getOption('iForwardRange'))):
            return True
        if oGraph.in_degree(strNodeId) > self.getOption('iMaxInDegree'):
            #logging.debug("     mooo in")
            return False
        # check for split
        if oGraph.out_degree(strNodeId) > self.getOption('iMaxOutDegree') or oGraph.out_degree(strNodeId) == 0:
            #logging.debug("     mooo out")
            return False
#        elif oGraph.out_degree(strNodeId) == 2:
#            if strFoundSplitId is None:
#                strFoundSplitId = strNodeId
#            else:
#                logging.debug("     mooo split")
#                return False

        oObject = oGraph.node_data(strNodeId)
        if iLevel <= self.getOption('iForwardCheck') and not oObject.iLabel in self.getOption('lstForwardLabels'):
            #logging.debug("     mooo label %d" % oObject.iLabel)
            return False

        if (strFoundSplitId is None and
            oGraph.out_degree(strNodeId) > 1 and
            oGraph.out_degree(strNodeId) <= self.getOption('iMaxOutDegree')):
            logging.info("     FOUND SPLIT! %s" % strNodeId)
            strFoundSplitId = strNodeId
            lstNewNodeIds = []
            if self.getOption('bAllowOneDaughterCell'):
                bResult = False
            else:
                bResult = True
            for strOutEdgeId in oGraph.out_arcs(strNodeId):
                lstNewNodeIds.append([])
                strTailId = oGraph.tail(strOutEdgeId)
                if self.getOption('bAllowOneDaughterCell'):
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
        oGraph = self._oGraph

        if oGraph.out_degree(strNodeId) == 1 and oGraph.in_degree(strNodeId) == 1:
            oObject = oGraph.node_data(strNodeId)
            oObjectNext = oGraph.node_data(oGraph.tail(oGraph.out_arcs(strNodeId)[0]))

            bFound = False
            for tplCheck in self.getOption('lstLabelTransitions'):
                if (len(tplCheck) == 2 and
                    oObject.iLabel == tplCheck[0] and
                    oObjectNext.iLabel == tplCheck[1]):
                    bFound = True
                    break

            if bFound:
                bCandidateOk = True
                self.oLogger.debug("  found %6s" % strNodeId)

                if bCandidateOk:
                    lstBackwardNodeIds = []
                    bCandidateOk = self._backwardCheck(strNodeId,
                                                       lstBackwardNodeIds)
                    self.oLogger.debug("    %s - backwards %s    %s" % (strNodeId, {True: 'ok', False: 'failed'}[bCandidateOk], lstBackwardNodeIds))

                if bCandidateOk:
                    lstForwardNodeIds = []
                    strTailId = oGraph.tail(oGraph.out_arcs(strNodeId)[0])
                    bCandidateOk = self._forwardCheck(strTailId,
                                                      lstForwardNodeIds)
                    self.oLogger.debug("    %s - forwards %s    %s" % (strTailId, {True: 'ok', False: 'failed'}[bCandidateOk], lstForwardNodeIds))

                if bCandidateOk:

                    track_length = self.getOption('iBackwardRange') + self.getOption('iForwardRange')

                    lstBackwardNodeIds.reverse()
                    strStartId = lstBackwardNodeIds[0]
                    dctResults[strStartId] = {'eventId'  : strNodeId}

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

                        if self.getOption('bFollowOnlyOneCell'):
                            # take the first track from the list
                            lstTracks = [lstTracks[0]]

                        dctResults[strStartId].update({'splitId'  : lstForwardNodeIds[iSplitIdx-1],
                                                       'maxLength': track_length,
                                                       'tracks'   : lstTracks,
                                                       })
                    else:
                        lstNodeIds = lstBackwardNodeIds + lstForwardNodeIds
                        dctResults[strStartId].update({'maxLength': track_length,
                                                       'tracks'   : [lstNodeIds],
                                                       })
                    #print dctResults[strStartId]
                    self.oLogger.debug("  %s - valid candidate" % strStartId)

        #self.oLogger.debug("moo %s" % self.out_arcs(strNodeId))
        for strOutEdgeId in oGraph.out_arcs(strNodeId):
            strTailId = oGraph.tail(strOutEdgeId)
            if not strTailId in dctVisitedNodes:
                dctVisitedNodes[strTailId] = True
                self._forwardVisitor(strTailId, dctResults, dctVisitedNodes, iLevel=iLevel+1)


class ClassificationCellTracker2(ClassificationCellTracker):

    OPTIONS = {"bAllowOneDaughterCell"   :   Option(True),
               }

    def _forwardVisitor(self, strNodeId, dctResults, dctVisitedNodes, iLevel=0):
        oGraph = self._oGraph

        if oGraph.out_degree(strNodeId) == 1 and oGraph.in_degree(strNodeId) == 1:
            oObject = oGraph.node_data(strNodeId)
            oObjectNext = oGraph.node_data(oGraph.tail(oGraph.out_arcs(strNodeId)[0]))

            bFound = False
            for tplCheck in self.getOption('lstLabelTransitions'):
                if (len(tplCheck) == 2 and
                    oObject.iLabel == tplCheck[0] and
                    oObjectNext.iLabel == tplCheck[1]):
                    bFound = True
                    break

            if bFound:
                bCandidateOk = True
                self.oLogger.debug("  found %6s" % strNodeId)

                if bCandidateOk:
                    lstBackwardNodeIds = []
                    bCandidateOk = self._backwardCheck(strNodeId,
                                                       lstBackwardNodeIds)
                    self.oLogger.debug("    %s - backwards %s    %s" % (strNodeId, {True: 'ok', False: 'failed'}[bCandidateOk], lstBackwardNodeIds))

                if bCandidateOk:
                    lstForwardNodeIds = []
                    strTailId = oGraph.tail(oGraph.out_arcs(strNodeId)[0])
                    bCandidateOk = self._forwardCheck(strTailId,
                                                      lstForwardNodeIds)
                    self.oLogger.debug("    %s - forwards %s    %s" % (strTailId, {True: 'ok', False: 'failed'}[bCandidateOk], lstForwardNodeIds))

                if bCandidateOk:

                    track_length = self.getOption('iBackwardRange') + self.getOption('iForwardRange')

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

                        #lstLengths = [len(x) for x in lstTracks]
                        #assert allEqual(lstLengths)

                        #if self.getOption('bFollowOnlyOneCell'):
                        #    # take the first track from the list
                        #    lstTracks = [lstTracks[0]]

                        for cnt, track in enumerate(lstTracks):
                            new_start_id = '%s_%d' % (strStartId, cnt+1)
                            dctResults[new_start_id] = {'splitId'  : lstForwardNodeIds[iSplitIdx-1],
                                                        'eventId'  : strNodeId,
                                                        'maxLength': track_length,
                                                        'tracks'   : [track],
                                                        }
                    else:
                        lstNodeIds = lstBackwardNodeIds + lstForwardNodeIds
                        dctResults[strStartId] = {'splitId'  : None,
                                                  'eventId'  : strNodeId,
                                                  'maxLength': track_length,
                                                  'tracks'   : [lstNodeIds],
                                                  }
                    #print dctResults[strStartId]
                    self.oLogger.debug("  %s - valid candidate" % strStartId)

        # record the full trajectory in a liniearized way
        base = dctResults['_current']
        dctResults['_full'][base].append(strNodeId)
        depth = len(dctResults['_full'][base])

        #self.oLogger.debug("moo %s" % self.out_arcs(strNodeId))
        for idx, strOutEdgeId in enumerate(oGraph.out_arcs(strNodeId)):
            strTailId = oGraph.tail(strOutEdgeId)
            if not strTailId in dctVisitedNodes:
                dctVisitedNodes[strTailId] = True

                # make a copy of the list for the new branch
                if idx > 0:
                    dctResults['_full'].append(dctResults['_full'][base][:depth])
                    dctResults['_current'] += idx
                self._forwardVisitor(strTailId, dctResults, dctVisitedNodes, iLevel=iLevel+1)

#    @staticmethod
#    def getNodeIdFromComponents(frame,  obj_id, child_id=None):
#        return '%d_%s' % (frame, obj_id)
#
    @staticmethod
    def getComponentsFromNodeId(strNodeId):
        items = map(int, strNodeId.split('_'))
        frame, obj_id = items[:2]
        if len(items) < 3:
            return frame, obj_id
        else:
            branch_id = items[2]
            return frame, obj_id, branch_id

    def exportFullTracks(self, sep='\t'):

        strPathOut = os.path.join(self.strPathOut, 'full')
        shutil.rmtree(strPathOut, True)
        safe_mkdirs(strPathOut)

        feature_lookup = OrderedDict()
        feature_lookup['mean'] = 'n2_avg'
        feature_lookup['sd'] = 'n2_stddev'
        feature_lookup['size'] = 'roisize'

        for start_id, data in self.dctVisitorData.iteritems():

            for idx, track in enumerate(data['_full']):

                has_header = False
                line1 = []
                line2 = []
                line3 = []

                filename = self._formatFilename(nodeId=start_id, subPath='full', branchId=idx+1)
                f = file(filename, 'w')

                for node_id in track:
                    frame, obj_id = self.getComponentsFromNodeId(node_id)

                    prefix = [frame, self.oMetaData.get_timestamp_relative(self.origP, frame), obj_id]
                    prefix_names = ['frame', 'time', 'objID']
                    items = []

                    for channel in self._dctTimeChannels[frame].values():
                        for region_id in channel.region_names():

                            region = channel.get_region(region_id)

                            if obj_id in region:
                                #FIXME:
                                feature_lookup2 = feature_lookup.copy()
                                for k,v in feature_lookup2.iteritems():
                                    if not region.hasFeatureName(v):
                                        del feature_lookup2[k]

                                if not has_header:
                                    keys = ['classLabel', 'className']
                                    if channel.NAME == 'Primary':
                                        keys += ['centerX', 'centerY']
                                    keys += feature_lookup2.keys()
                                    line1 += [channel.NAME.upper()] * len(keys)
                                    line2 += [region_id] * len(keys)
                                    line3 += keys

                                obj = region[obj_id]
                                #print feature_lookup2.keys(), feature_lookup2.values()
                                #fn = region.getFeatureNames()
                                #print zip(fn, obj.aFeatures)
                                features = region.getFeaturesByNames(obj_id, feature_lookup2.values())
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


