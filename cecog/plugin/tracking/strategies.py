"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

import os
import re
import numpy
from cecog import ccore
from cecog.gui.guitraits import (BooleanTrait,
                                 IntTrait,
                                 FloatTrait,
                                 StringTrait)


from cecog.plugin import stopwatch
from cecog.plugin.tracking.manager import _TrackingPlugin 

import math
from collections import OrderedDict

from cecog.logging import LoggerObject
from cecog.extensions.graphLib import Graph
from cecog import ccore   


class BaseTracker(LoggerObject):
    
    def __init__(self):
        super(BaseTracker, self).__init__()

    def _init(self):
        self.graph = Graph()
        self._frame_data = OrderedDict()

    def track_next_frame(self, frame, samples):
        raise NotImplementedError("ABC class")

    def clone_graph(self, timeholder, channel, region):
        """Clone the tracking graph with data from a different channel."""

        ngraph = Graph()

        # add nodes from other segmentation region
        for nodeid in self.graph.node_list():
            iframe, objid = self.split_nodeid(nodeid)[:2]
            sample = timeholder[iframe][channel].get_region(region)[objid]
            ngraph.add_node(nodeid, sample)

        for edge in self.graph.edges.values():
            ngraph.add_edge(*edge)

        return ngraph
    
    @staticmethod
    def node_id(frame, object_label):
        return '%d_%s' %(frame, object_label)

    @staticmethod
    def split_nodeid(nodeid):
        return tuple([int(i) for i in nodeid.split('_')])
    
    @property
    def start_frame(self):
        """Return the index of the first frame."""
        return min(self._frame_data.keys())

    @property
    def end_frame(self):
        """Returns the index of the last frame currently processed."""
        return max(self._frame_data.keys())

    def render_tracks(self, frame, size, n=5, thick=True, radius=3):
        img_conn = ccore.Image(*size)
        img_split = ccore.Image(*size)

        if n < 0 or frame-n+1 < self.start_frame:
            current = self.start_frame
            n = frame-current+1
        else:
            current = frame-n+1

        found = False
        for i in range(n):
            col = int(max(255.*(i+1)/n, 255))

            if current in self._frame_data:
                preframe = self.closest_preceding_frame(current)
                if preframe is not None:
                    found = True
                    for objIdP in self._frame_data[preframe]:
                        nodeIdP = self.node_id(preframe, objIdP)
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
                            ccore.drawFilledCircle(
                                ccore.Diff2D(*objC.oCenterAbs), radius, img_conn, col)
            current += 1

        if not found and frame in self._frame_data:
            for objId in self._frame_data[frame]:
                nodeId = self.node_id(frame, objId)
                obj = self.graph.node_data(nodeId)
                ccore.drawFilledCircle(ccore.Diff2D(*obj.oCenterAbs),
                                       radius, img_conn, col)

        return img_conn, img_split

class TrackingStructuredLearning(_TrackingPlugin, BaseTracker):

    LABEL = 'Structured Learning tracker'
    NAME = 'structured_earning_tracker'
    COLOR = '#FFFF00'
    DOC = ":additional_tracking_plugins"

    REQUIRES = None
    
    PARAMS = [('xy_distance', IntTrait(5, 0, 4000, label='Parameter Int')),
              ]
    
    def __init__(self, *args, **kwargs):
        _TrackingPlugin.__init__(self, *args, **kwargs)
        BaseTracker.__init__(self)

    def render_to_gui(self, panel):
        panel.add_input('xy_distance')
        panel.add_button("Execute something", self._my_execution)

    @stopwatch()
    def _run(self, *args, **kwargs):
        # the run function is actually not needed
        print args, kwargs
        return
    
    def track_next_frame(self, frame, samples):
        # To be implemented that's the iterative tracking part
        
        # Here samples of the current frame are just added to the graph structure
        self._frame_data.setdefault(frame, [])
        for label, sample in samples.iteritems():
            node_id = self.node_id(frame, label)
            self.graph.add_node(node_id, sample)
            self._frame_data[frame].append(label)

        # connect time point only if any object is present
        if len(self._frame_data[frame]) > 0:
            self.connect_nodes(frame)
    
    def _my_execution(self):
        # example on how to trigger an execution from within the bay
        print "my execution: with param 'xy_distance'=", self.params['xy_distance']
    
    
        
    
class TrackingNearestNeighbor(_TrackingPlugin, BaseTracker):

    LABEL = 'Nearest Neighbor tracker'
    NAME = 'nearest_neighbor_tracker'
    COLOR = '#FFFF00'
    DOC = ":additional_tracking"

    REQUIRES = None

    PARAMS = [('max_object_distance', IntTrait(21, 0, 4000, label='Max object x-y distance')),
              ('max_frame_gap', IntTrait(3, 0, 7, label='Max time-point gap')),
              ('max_split_objects', IntTrait(2, 0, 7, label='Max split events')),
          ]
    
    def __init__(self, *args, **kwargs):
        _TrackingPlugin.__init__(self, *args, **kwargs)
        BaseTracker.__init__(self)

    @stopwatch()
    def _run(self, *args, **kwargs):
        # of no interest here. Use track_next_frame(..)
        print args, kwargs
        return
    
    def render_to_gui(self, panel):
        panel.add_group(None,
                       [('max_object_distance', (0,0,1,1)),
                        ('max_frame_gap', (0,1,1,1)),
                        ('max_split_objects', (1,0,1,1)),
                        ], link='tracking', label='Tracking')    

    def track_next_frame(self, frame, samples):
        self._frame_data.setdefault(frame, [])
        for label, sample in samples.iteritems():
            node_id = self.node_id(frame, label)
            self.graph.add_node(node_id, sample)
            self._frame_data[frame].append(label)

        # connect time point only if any object is present
        if len(self._frame_data[frame]) > 0:
            self.connect_nodes(frame)
            

    def closest_preceding_frame(self, frame):
        """Return the preceding frame or None if the gap between the to frames
        is larget than max_frame_gap."""

        frames = self._frame_data.keys()
        icurrent = frames.index(frame)

        pre_frame = None
        if (0 < icurrent < len(frames)):
            pre_frame = frames[icurrent-1]
        if pre_frame is not None and (frame - pre_frame) > self.params['max_frame_gap']:
            pre_frame = None
        return pre_frame
        
    def connect_nodes(self, iT):
        max_dist2 = math.pow(self.params['max_object_distance'], 2)
        bReturnSuccess = False

        # search all nodes in the previous frame
        # if there is an empty frame, look for the closest frame
        # that contains objects. For this go up to iMaxTrackingGap
        # into the past.
        iPreviousT = self.closest_preceding_frame(iT)

        if iPreviousT is not None:
            bReturnSuccess = True
            dctMerges = {}
            dctSplits = {}

            # for all nodes in this layer
            for iObjIdP in self._frame_data[iPreviousT]:

                strNodeIdP = self.node_id(iPreviousT, iObjIdP)
                oImageObjectP = self.graph.node_data(strNodeIdP)

                lstNearest = []

                for iObjIdC in self._frame_data[iT]:
                    strNodeIdC = self.node_id(iT, iObjIdC)
                    oImageObjectC = self.graph.node_data(strNodeIdC)
                    dist = oImageObjectC.squaredMagnitude(oImageObjectP)

                    # take all candidates within a certain distance
                    if dist < max_dist2:
                        lstNearest.append((dist, strNodeIdC))

                # lstNearest is the list of nodes in the current frame
                # whose distance to the previous node is smaller than the
                # fixed threshold.
                if len(lstNearest) > 0:
                    # sort ascending by distance (first tuple element)
                    lstNearest.sort(key=lambda x: x[0])

                    # take only a certain number as merge candidates (the N closest)
                    # and split candidates (this number is identical).
                    for dist, strNodeIdC in lstNearest[:self.params['max_split_objects']]:
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
                    self.graph.add_edge(nodes[0][1], id_c)
                    found_connection = True
                else:
                    # If there are several candidates (previous objects fulfilling the condition)
                    # take those candidates in the previous frame that have only one possible
                    # predecessor.
                    for dist, id_p in nodes:
                        if len(dctSplits[id_p]) == 1:
                            self.graph.add_edge(id_p, id_c)
                            found_connection = True

                # if there was no connection found, take the closest predecessor,
                # unless there is none.
                if not found_connection:
                    if len(nodes) > 0:
                        self.graph.add_edge(nodes[0][1], id_c)

        return iPreviousT, bReturnSuccess
        