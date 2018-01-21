"""
eventseleciton.py

Module supervised event selection based on class label
transitions.
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
from scipy import stats
from matplotlib import mlab
from sklearn.cluster import KMeans
from collections import defaultdict

from cecog.colors import rgb2hex, BINARY_CMAP
from cecog.logging import LoggerObject
from cecog.analyzer.tracker import Tracker


# TODO: Recursion limit has to be set higher than 1000,
#       due to the current implementation of _forward_visitor(),
#       which calls for 'full' tracks itself recursively for each
#       node_id. In case of long time_lapse movies this might be
#       more than 1000 (default python rec limit)
import sys
sys.setrecursionlimit(10000)

class EventSelectionCore(LoggerObject):
    """Parent for all transition based event selection classes."""
    def __init__(self, graph, transitions, forward_range, backward_range,
                 forward_labels, backward_labels, forward_check, backward_check,
                 max_in_degree, max_out_degree, allow_one_daughter_cell):
        super(EventSelectionCore, self).__init__()

        self.graph = graph
        self.transitions = transitions
        self.forward_range = forward_range
        self.backward_range = backward_range
        self.forward_labels = forward_labels
        self.backward_labels = backward_labels
        self.forward_check = forward_check
        self.backward_check = backward_check
        self.max_in_degree = max_in_degree
        self.max_out_degree = max_out_degree
        self.allow_one_daughter_cell = allow_one_daughter_cell
        self.visitor_data = dict()

    def iterevents(self):
        for results in self.visitor_data.itervalues():
            for start_id, event_data in results.iteritems():
                yield start_id, event_data

    def itertracks(self):
        for startid, eventdata in self.iterevents():
            if isinstance(eventdata, dict):
                for track in eventdata['tracks']:
                    yield startid, track

    def start_nodes(self):
        """Return all start nodes i.e. nodes without incoming edges."""
        start_nodes = [node_id for node_id in self.graph.node_list()
                       if self.graph.in_degree(node_id) == 0]
        start_nodes.sort(key=lambda x: Tracker.split_nodeid(x)[0])
        return start_nodes

    def _is_transition(self, sample, sample2):
        """Test for label transitions."""
        for (label1, label2) in self.transitions:
            if sample.iLabel == label1 and sample2.iLabel == label2:
                return True
        return False

    def data_matrix(self):
        """Returns a matrix where the rows represent a sample and the column
        the corresponding feature vector.
        """
        data = []
        nodes = np.array(self.graph.node_list(), dtype=str)
        for node in nodes:
            obj = self.graph.node_data(node)
            data.append(obj.aFeatures)
        data = np.array(data)
        assert data.shape[0] == nodes.size
        return data, nodes

    @property
    def track_length(self):
        return self.backward_range + self.forward_range

    def _split_nodes(self, nodes):
        # XXX use the tracking graph to identiy splits
        # ie. graph.out_degree!!!!
        return [i for i, n in enumerate(nodes) if isinstance(n, list)]

    def centers(self):
        """Return the a list of the object centers for each track."""
        centers = dict()
        for startid, eventdata in self.iterevents():
            if startid in ['_full_tracks', '_current_branch']:
                continue
            data = list()
            for nodeids in zip(*eventdata['tracks']):
                for nodeid in nodeids:
                    obj = self.graph.node_data(nodeid)
                    frame = Tracker.split_nodeid(nodeid)[0]
                    data.append((int(frame), obj.iId, obj.oCenterAbs))
            centers[startid] = data
        return centers

    def find_events(self):

        start_ids = self.start_nodes()
        self.logger.debug("tracking: start nodes %d %s" % (len(start_ids), start_ids))
        visited_nodes = defaultdict(lambda: False)

        # linearaize full tracks
        for start_id in start_ids:
            self.logger.debug("root ID %s" %start_id)
            try:
                self.visitor_data[start_id] = {'_current_branch': 0, '_full_tracks' : [[]]}
                self._linearize(start_id, self.visitor_data[start_id], visited_nodes)
            except RuntimeError as e:
                if e.message.startswith('maximum recursion'):
                    raise RuntimeError(('linearization failed: maximum '
                                        'recursion reached in _linearize()'))
                else:
                    raise

        # find events in these full tracks
        for start_id in start_ids:
            self.logger.debug("root ID %s" % start_id)
            try:
                self._extract_events_from_linearized_tracks(self.visitor_data[start_id])
            except RuntimeError as e:
                if e.message.startswith('maximum recursion'):
                    raise RuntimeError(('linearization failed: maximum '
                                        'recursion reached in _linearize()'))
                else:
                    raise


    def _linearize(self, nodeid, results, visited_nodes, level=0):
        """Record the full trajectory in a liniearized fashion."""

        # get current branch index
        base = results['_current_branch']
        # append current node to it
        results['_full_tracks'][base].append(nodeid)
        # get current track legnth
        depth = len(results['_full_tracks'][base])
        # iterate over all successors
        for i, out_edgeid in enumerate(self.graph.out_arcs(nodeid)):
            tailid = self.graph.tail(out_edgeid)
            # check if node has been visited by other track already
            if  not visited_nodes[tailid]:
                visited_nodes[tailid] = True
                # make a copy of the list for the new branch(es)
                if i > 0:
                    results['_full_tracks'].append(results['_full_tracks'][base][:depth])
                    results['_current_branch'] += 1
                # recurse
                self._linearize(tailid, results, visited_nodes, level=level+1)


    def _extract_events_from_linearized_tracks(self, tracks):
        for each_branch in tracks['_full_tracks']:
            t_idx = 0
            while t_idx < len(each_branch):
                nodeid = each_branch[t_idx]
                degrees = (self.graph.out_degree(nodeid), self.graph.in_degree(nodeid))
                if degrees in ((1, 1), (1, 0)):

                    sample = self.graph.node_data(nodeid)
                    successor = self.graph.node_data(self.graph.tail(self.graph.out_arcs(nodeid)[0]))

                    if self._is_transition(sample, successor):
                        is_candidate = True
                        self.logger.debug("  found %6s" %nodeid)

                        if is_candidate:
                            backward_nodes = []
                            is_candidate = self._backward_check(nodeid, backward_nodes)
                            self.logger.debug("    %s - backwards %s    %s"
                                              %(nodeid, {True: 'ok', False: 'failed'}[is_candidate],
                                                backward_nodes))

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
                                tracks_ = []
                                for split in forward_nodes[first_split]:
                                    track_nodes = backward_nodes + forward_nodes[:first_split] + split
                                    if len(track_nodes) == track_length:
                                        tracks_.append(track_nodes)

                                for i, track in enumerate(tracks_):
                                    new_start_id = '%s_%d' % (startid, i+1)
                                    tracks[new_start_id] = {'splitId': forward_nodes[first_split-1],
                                                             'eventId': nodeid,
                                                             'maxLength': track_length,
                                                             'tracks': [track],
                                                             # keep value at which index the two daugther
                                                             # tracks differ due to a split event
                                                             'splitIdx' : first_split + len(backward_nodes)}
                                    t_idx += track_length-1

                            else:
                                track_nodes = backward_nodes + forward_nodes
                                tracks[startid] = {'splitId': None,
                                                    'eventId': nodeid,
                                                    'maxLength': track_length,
                                                    'tracks': [track_nodes]}
                                t_idx += track_length - 1
                            self.logger.debug("  %s - valid candidate" %startid)
                t_idx += 1

    def _forward_check(self, *args, **kw):
        raise NotImplementedError

    def _backward_check(self, *args, **kw):
        raise NotImplementedError


class EventSelection(EventSelectionCore):

    def __init__(self, graph, transitions, forward_range, backward_range,
                 forward_labels, backward_labels,
                 export_features=False, max_in_degree=1, max_out_degree=1,
                 backward_check=False, forward_check=False, backward_range_min=-1,
                 forward_range_min=-1, allow_one_daughter_cell=True):
        super(EventSelection, self).__init__( \
            graph, transitions, forward_range, backward_range, forward_labels,
            backward_labels, forward_check, backward_check, max_in_degree,
            max_out_degree, allow_one_daughter_cell)

        self.backward_range_min = backward_range_min
        self.forward_range_min = forward_range_min
        self.export_features = export_features

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
                                                  level=level+1,
                                                  found_splitid=found_splitid)
                else:
                    result &= self._forward_check(tailid, new_nodeids[-1],
                                                  level=level+1,
                                                  found_splitid=found_splitid)
            nodeids.append(new_nodeids)
            return result
        else:
            out_edgeid = self.graph.out_arcs(nodeid)[0]
            tailid = self.graph.tail(out_edgeid)
            return self._forward_check(tailid, nodeids,
                                       level=level+1, found_splitid=found_splitid)
