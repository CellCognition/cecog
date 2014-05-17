"""
tracker.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['Tracker']

import math
from collections import OrderedDict

from cecog.util.logger import LoggerObject
from cecog.extensions.graphLib import Graph
from cecog import ccore


class Tracker(LoggerObject):

    __slots__ = ['graph', '_frame_data','max_object_distance',
                 'max_node_degree', 'max_frame_gap']

    def __init__(self, max_object_distance=50, max_node_degree=3,
                 max_frame_gap=3):
        super(Tracker, self).__init__()

        if max_frame_gap < 1 or not isinstance(max_frame_gap, int):
            raise ValueError("max_frame_gap must be a positive integer")
        self.graph = Graph()
        self._frame_data = OrderedDict()

        self.max_frame_gap = max_frame_gap
        self.max_object_distance = max_object_distance
        self.max_node_degree = max_node_degree

    @property
    def start_frame(self):
        """Return the index of the first frame."""
        return min(self._frame_data.keys())

    @property
    def end_frame(self):
        """Returns the index of the last frame currently processed."""
        return max(self._frame_data.keys())

    # rename function to frames
    @property
    def frames(self):
        """Returns a dict with frame indices as keys and lists of
        samples as values."""
        return self._frame_data

    @staticmethod
    def node_id(frame, object_label):
        return '%d_%s' %(frame, object_label)

    @staticmethod
    def split_nodeid(nodeid):
        return tuple([int(i) for i in nodeid.split('_')])

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
        if pre_frame is not None and (frame - pre_frame) > self.max_frame_gap:
            pre_frame = None
        return pre_frame

    def clone_graph(self, timeholder, channel, region):
        """Clone the tracking graph with data from a different channel."""

        ngraph = Graph()

        # add nodes from other segmentation region
        for nodeid in self.graph.node_list():
            iframe, objid = Tracker.split_nodeid(nodeid)[:2]
            sample = timeholder[iframe][channel].get_region(region)[objid]
            ngraph.add_node(nodeid, sample)

        for edge in self.graph.edges.values():
            ngraph.add_edge(*edge)

        return ngraph

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

    def connect_nodes(self, iT):
        max_dist2 = math.pow(self.max_object_distance, 2)
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
                    for dist, strNodeIdC in lstNearest[:self.max_node_degree]:
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
