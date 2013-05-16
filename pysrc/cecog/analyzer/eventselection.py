"""
eventseleciton.py

Module supervised and unsupervised event selection based on class label
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

from cecog.util.logger import LoggerObject
from cecog.analyzer.tracker import Tracker

class EventSelectionError(Exception):
    pass

class EventSelectionCore(LoggerObject):
    """Parent for all transition based event selection classes."""
    def __init__(self, graph, transitions, forward_range, backward_range):
        super(EventSelectionCore, self).__init__()

        self.graph = graph
        self.visitor_data = dict()
        self.transitions = transitions
        self.forward_range = forward_range
        self.backward_range = backward_range

    def iterevents(self):
        for results in self.visitor_data.itervalues():
            for start_id, event_data in results.iteritems():
                yield start_id, event_data

    def start_nodes(self):
        """Return all start nodes i.e. nodes without incoming edges."""
        start_nodes = [node_id for node_id in self.graph.node_list()
                       if self.graph.in_degree(node_id) == 0]
        start_nodes.sort(key=lambda x: Tracker.split_nodeid(x)[0])
        return start_nodes

    def _is_transition(self, sample, sample2):
        """Test for label transitions."""
        for (label1, label2) in self.transitions:
            assert isinstance(label1, int)
            assert isinstance(label2, int)
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

    # XXX rewrite this function
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


class EventSelection(EventSelectionCore):

    def __init__(self, graph, transitions, backward_range, forward_range,
                 forward_labels, backward_labels,
                 export_features=False, max_in_degree=1, max_out_degree=2,
                 backward_check=False, forward_check=False, backward_range_min=-1,
                 forward_range_min=-1, allow_one_daughter_cell=True):
        super(EventSelection, self).__init__(graph, transitions,
                                             forward_range, backward_range)

        self.backward_range_min = backward_range_min
        self.forward_range_min = forward_range_min
        self.max_in_degree = max_in_degree
        self.max_out_degree = max_out_degree
        self.forward_labels = forward_labels
        self.backward_labels = backward_labels
        self.export_features = export_features
        self.backward_check = backward_check
        self.forward_check = forward_check
        self.allow_one_daughter_cell = allow_one_daughter_cell


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

            if self._is_transition(sample, successor):
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


class UnsupervisedEventSelection(EventSelectionCore):

    def __init__(self, graph, forward_range, backward_range,
                 transitions=((0, 1), ), varfrac=0.99, max_in_degree=1,
                 max_out_degree=1):
        super(UnsupervisedEventSelection, self).__init__( \
            graph, forward_range, backward_range, transitions)

        self.graph = graph
        self.visitor_data = dict()
        self.transitions = transitions
        self.forward_range = forward_range
        self.backward_range = backward_range
        self.varfrac = varfrac # variance fraction
        self.max_in_degree = max_in_degree


    def find_events(self, *args, **kw):
        self.binary_classification()
        return super(UnsupervisedEventSelection, self).find_events(*args, **kw)

    def binary_classification(self):
        """Perform an initial binary classifcation to distinguish between
        mitotic and non-mitotic objects/cells.

        Three steps of binary classifcation are:
        1) data pre processing
           - remove features columns that contain zeros (Qing did not say why!)
           - calculate the z-score
           - perform a pca and keep only feature that contribute a certain
             fraction of the variance.
        2) kmeans clustering (at least 5 initialisation, emperically determined)
        3) assing mitotic labels (0 means "non-mitotic", 1 "mitotic")
             The assumption is that non-mitotic cell are the larger population.
        """

        # features of all objects/samples/cells
        data_obj = []
        for node in self.graph.node_list():
            obj = self.graph.node_data(node)
            data_obj.append(obj.aFeatures)
        data = np.array(data_obj)

        if data.shape[0] <= data.shape[1]:
            msg = ("Not enough objects in data set to proceed",
                   "Number of object is smaller than the number of features",
                   "(%d <= %d)" %tuple(data.shape))
            raise EventSelectionError(msg)

        # delete columns with zeros
        ind = np.where(data==0)[1]
        data = np.delete(data, ind, 1)

        # FIXME dimension and axis for zscore calculation
        # the axes for zscoring needs to be defined!!!
        data_zs = stats.zscore(data)
        # sss.zscore(self.remove_constant_columns(data))
        pca = mlab.PCA(data_zs)
        # XXX take the minimum to make it more readable
        num_features = np.nonzero(np.cumsum(pca.fracs) > self.varfrac)[0][0]
        data_pca = pca.project(data_zs)[:, 0:num_features]

        # just for debugging
        # bcfname = os.path.join(self.strPathOut, 'init_bc.csv')
        # numpy.savetxt(bcfname, data_pca, delimiter=",")

        km = KMeans(n_clusters=2, n_init=5)
        labels = km.fit_predict(data)

        # assign labels, 0 for non-mitotic, 1 for mitotic
        # from now on labels a biologial meaning
        if labels[labels==1].size > labels[labels==0].size:
            labels = np.where(labels, 0, 1)

        for i, node in enumerate(self.graph.node_list()):
            obj = self.graph.node_data(node)
            obj = labels[i]

        import pdb; pdb.set_trace()

    def _forward_visitor(self, *args, **kw):
        return super(UnsupervisedEventSelection, self)._forward_visitor(*args, **kw)

    def _backward_check(self, node_id, node_ids, level=1):
        node_ids.append(node_id)

        if ((self.backward_range == -1 and self.graph.in_degree(node_id) == 0) or
            (level >= self.backward_range and self.graph.in_degree(node_id) == 0) or
            (level >= self.backward_range)):
            return True

        if self.graph.out_degree(node_id) != 1:
            return False
        # check for split
        if self.graph.in_degree(node_id) != 1:
            return False

        label = self.graph.node_data(node_id).iLabel
        if level > 1 and level-1 <= 1 and not label == 0:
            return False

        edge_id = self.graph.in_arcs(node_id)[0]
        head_id = self.graph.head(edge_id)
        return self._backward_check(head_id, node_ids, level=level+1)

    def _forward_check(self, node_id, node_ids, level=1):
        node_ids.append(node_id)

        if ((self.forward_range == -1 and self.graph.out_degree(node_id) == 0) or
            (level >= self.forward_range and self.graph.out_degree(node_id) == 0) or
            (level >= self.forward_range)):
            return True

        if self.graph.in_degree(node_id) > self.max_in_degree:
            return False

        # check for split
        if self.graph.out_degree(node_id) > self.max_out_degree or \
                self.graph.out_degree(node_id) == 0:
            return False
