"""
transitional.py

Class for transitional (supervised) event selection
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["EventSelection"]

import numpy as np

from cecog.util.logger import LoggerObject
from cecog.analyzer.tracker import Tracker

class EventSelection(LoggerObject):

    def __init__(self, graph, transitions, forward_labels, backward_labels,
                 backward_range=-1, forward_range=-1, export_features=False,
                 compression=False, max_in_degree=1, max_out_degree=2,
                 backward_check=False, forward_check=False,
                 backward_range_min=-1, forward_range_min=-1,
                 allow_one_daughter_cell=True):
        super(EventSelection, self).__init__()

        self.graph = graph
        self.visitor_data = dict()
        self.transitions = transitions
        self.forward_labels = forward_labels
        self.backward_labels = backward_labels
        self.forward_range = forward_range
        self.backward_range = backward_range
        self.export_features = export_features
        self.compression = compression
        self.max_in_degree = max_in_degree
        self.max_out_degree = max_out_degree
        self.backward_range_min = backward_range_min
        self.forward_range_min = forward_range_min
        self.backward_check = backward_check
        self.forward_check = forward_check
        self.allow_one_daughter_cell = allow_one_daughter_cell

    def start_nodes(self):
        """Return all start nodes i.e. nodes without incoming edeges."""
        start_nodes = [node_id for node_id in self.graph.node_list()
                       if self.graph.in_degree(node_id) == 0]
        start_nodes.sort(key=lambda x: Tracker.split_nodeid(x)[0])
        return start_nodes

    def find_events(self, start_ids=None):
        if start_ids is None:
            start_ids = self.start_nodes()

        self.logger.debug("tracking: start nodes %d %s" %(len(start_ids),
                                                          start_ids))
        visited_nodes = dict()
        for start_id in start_ids:
            self.visitor_data[start_id] = {'_current': 0, '_full' : [[]]}
            self.logger.debug("root ID %s" %start_id)
            self._forward_visitor(start_id, self.visitor_data[start_id],
                                 visited_nodes)

    def iterevents(self):
        for results in self.visitor_data.itervalues():
            for start_id, event_data in results.iteritems():
                yield start_id, event_data

    def bboxes(self, size=None, border=0):
        bboxes = {}
        for startid, eventdata in self.iterevents():
            if startid  in ['_full', '_current']:
                continue
            data = []
            for nodeids in zip(*eventdata['tracks']):
                nodeid = nodeids[0]
                frame = Tracker.split_nodeid(nodeid)[0]
                objids = [Tracker.split_nodeid(n)[1] for n in nodeids]
                objects = [self.graph.node_data(n) for n in nodeids]

                minX = min([obj.oRoi.upperLeft[0] for obj in objects])
                minY = min([obj.oRoi.upperLeft[1] for obj in objects])
                maxX = max([obj.oRoi.lowerRight[0] for obj in objects])
                maxY = max([obj.oRoi.lowerRight[1] for obj in objects])
                width  = maxX - minX + 1
                height = maxY - minY + 1
                centerX = int(round(np.average([obj.oCenterAbs[0] for obj in objects])))
                centerY = int(round(np.average([obj.oCenterAbs[1] for obj in objects])))
                data.append((frame, centerX, centerY, width, height, objids))
            data1 = np.array(data, 'O')
            if not size is None and len(size) == 2:
                diffX = int(size[0] / 2)
                diffY = int(size[1] / 2)
            else:
                diffX = int(max(data1[:,3])/2 + border)
                diffY = int(max(data1[:,4])/2 + border)
            # convert to float to for numpy float64 type
            timedata = [(int(d[0]),
                         (d[1] - diffX,
                          d[2] - diffY,
                          d[1] + diffX - 1 + size[0] %2,
                          d[2] + diffY - 1 + size[1] %2),
                         d[5]) for d in data1]
            bboxes[startid] = timedata
        return bboxes

    def _is_event(self, sample, sample2):
        """Test for label transitions."""
        for (label1, label2) in self.transitions:
            if sample.iLabel == label1 and sample2.iLabel == label2:
                return True
        return False

    @property
    def track_length(self):
        return self.backward_range + self.forward_range

    def _split_nodes(self, nodes):
        # XXX use the tracking graph to identiy splits
        # ie. graph.out_degree!!!!
        return [i for i, n in enumerate(nodes) if isinstance(n, list)]

    def _backward_check(self, nodeid, nodeids, level=1):
        nodeids.append(nodeid)
        if ((self.backward_range == -1 and self.graph.in_degree(nodeid) == 0) or
            (self.backward_range_min and level >= self.backward_range and  \
                 self.graph.in_degree(nodeid) == 0) or
            (not self.backward_range_min  and level >= self.backward_range)):
            return True

        # check for splits
        if self.graph.out_degree(nodeid) != 1:
            return False
        if self.graph.in_degree(nodeid) != 1:
            return False

        sample = self.graph.node_data(nodeid)
        if level > 1 and level-1 <= self.backward_check and not \
                sample.iLabel in self.backward_labels:
            return False

        edgeid = self.graph.in_arcs(nodeid)[0]
        headid = self.graph.head(edgeid)
        return self._backward_check(headid, nodeids, level=level+1)

    def _forward_check(self, nodeid, nodeids, level=1, found_splitid=None):
        nodeids.append(nodeid)
        if ((self.forward_range == -1 and self.graph.out_degree(nodeid) == 0) or
            (self.forward_range_min and level >= self.forward_range and \
                 self.graph.out_degree(nodeid) == 0) or
            (not self.forward_range_min and level >= self.forward_range)):
            return True

        # check for splits
        if self.graph.in_degree(nodeid) > self.max_in_degree:
            return False
        if self.graph.out_degree(nodeid) > self.max_out_degree or \
        self.graph.out_degree(nodeid) == 0:
            return False

        sample = self.graph.node_data(nodeid)
        if level <= self.forward_check and not sample.iLabel in self.forward_labels:
            return False

        if (found_splitid is None and
            self.graph.out_degree(nodeid) > 1 and
            self.graph.out_degree(nodeid) <= self.max_out_degree):
            self.logger.info("     FOUND SPLIT! %s" %nodeid)
            found_splitid = nodeid
            new_nodeids = []
            if self.allow_one_daughter_cell:
                result = False
            else:
                result = True
            for edgeid in self.graph.out_arcs(nodeid):
                new_nodeids.append([])
                tailid = self.graph.tail(edgeid)
                if self.allow_one_daughter_cell:
                    result |= self._forward_check(tailid, new_nodeids[-1],
                                                  level=level+1, found_splitid=found_splitid)
                else:
                    result &= self._forward_check(tailid, new_nodeids[-1],
                                                  level=level+1, found_splitid=found_splitid)
            nodeids.append(new_nodeids)
            return result
        else:
            out_edgeid = self.graph.out_arcs(nodeid)[0]
            tailid = self.graph.tail(out_edgeid)
            return self._forward_check(tailid, nodeids,
                                       level=level+1, found_splitid=found_splitid)

    def _forward_visitor(self, nodeid, results, visited_nodes, level=0):

        if self.graph.out_degree(nodeid) == 1 and self.graph.in_degree(nodeid) == 1:
            sample = self.graph.node_data(nodeid)
            successor = self.graph.node_data(
                self.graph.tail(self.graph.out_arcs(nodeid)[0]))

            if self._is_event(sample, successor):
                is_candidate = True
                self.logger.debug("  found %6s" %nodeid)

                if is_candidate:
                    backward_nodes = []
                    is_candidate = self._backward_check(nodeid, backward_nodes)
                    self.logger.debug("    %s - backwards %s    %s"
                                      %(nodeid, {True: 'ok', False: 'failed'}[is_candidate], backward_nodes))

                if is_candidate:
                    forward_nodes = []
                    tailid = self.graph.tail(self.graph.out_arcs(nodeid)[0])
                    is_candidate = self._forward_check(tailid, forward_nodes)
                    self.logger.debug("    %s - forwards %s    %s"
                                      %(tailid, {True: 'ok', False: 'failed'}[is_candidate], forward_nodes))

                if is_candidate:
                    track_length = self.track_length
                    backward_nodes.reverse()
                    startid = backward_nodes[0]

                    # searching for split events and linearize split tracks
                    splits = self._split_nodes(forward_nodes)
                    if len(splits) > 0:
                        # take only the first split event
                        first_split = splits[0]
                        tracks = []
                        for split in forward_nodes[first_split]:
                            track_nodes = backward_nodes + forward_nodes[:first_split] + split
                            if len(track_nodes) == track_length:
                                tracks.append(track_nodes)

                        for i, track in enumerate(tracks):
                            new_start_id = '%s_%d' % (startid, i+1)
                            results[new_start_id] = {'splitId': forward_nodes[first_split-1],
                                                     'eventId': nodeid,
                                                     'maxLength': track_length,
                                                     'tracks': [track],
                                                     # keep value at which index the two daugther
                                                     # tracks differ due to a split event
                                                     'splitIdx' : first_split + len(backward_nodes)}
                    else:
                        track_nodes = backward_nodes + forward_nodes
                        results[startid] = {'splitId': None,
                                            'eventId': nodeid,
                                            'maxLength': track_length,
                                            'tracks': [track_nodes]}
                    # print dctResults[strStartId]
                    self.logger.debug("  %s - valid candidate" %startid)

        # record the full trajectory in a liniearized way
        base = results['_current']
        results['_full'][base].append(nodeid)
        depth = len(results['_full'][base])

        for i, out_edgeid in enumerate(self.graph.out_arcs(nodeid)):
            tailid = self.graph.tail(out_edgeid)
            if tailid not in visited_nodes:
                visited_nodes[tailid] = True

                # make a copy of the list for the new branch
                if i > 0:
                    results['_full'].append(results['_full'][base][:depth])
                    results['_current'] += i
                self._forward_visitor(tailid, results, visited_nodes, level=level+1)
