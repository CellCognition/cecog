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

__all__ = ["EventSelection", "UnsupervisedEventSelection"]

import numpy as np
from scipy import stats
from matplotlib import mlab
from sklearn.cluster import KMeans

from cecog.colors import rgb2hex, unsupervised_cmap, BINARY_CMAP
from cecog.util.logger import LoggerObject
from cecog.analyzer.tracker import Tracker
from cecog.tc3 import TC3EventFilter
from cecog.tc3 import TemporalClustering



### TODO: Recursion limit has to be set higher than 1000,
###       due to the current implementation of _forward_visitor(),
###       which calls for 'full' tracks itself recursively for each
###       node_id. In case of long time_lapse movies this might be
###       more than 1000 (default python rec limit)
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
            if startid in ['_full', '_current']:
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
        self.logger.debug("tracking: start nodes %d %s" %(len(start_ids),
                                                          start_ids))
        visited_nodes = dict()
        for start_id in start_ids:
            self.visitor_data[start_id] = {'_current': 0, '_full' : [[]]}
            self.logger.debug("root ID %s" %start_id)
            try:
                self._forward_visitor(start_id, self.visitor_data[start_id],
                                      visited_nodes)
            except RuntimeError as e:
                if e.message.startswith('maximum recursion'):
                    raise RuntimeError(('eventselection failed: maximum '
                                        'recursion reached in _forward_visitor()'))
                else:
                   raise(e)


    def _forward_visitor(self, nodeid, results, visited_nodes, level=0):

        if self.graph.out_degree(nodeid) == 1 and \
                self.graph.in_degree(nodeid) == 1:
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
                    results['_current'] += 1
                self._forward_visitor(tailid, results, visited_nodes, level=level+1)

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

class UnsupervisedEventSelection(EventSelectionCore):

    def __init__(self, graph, transitions, forward_range, backward_range,
                 forward_labels, backward_labels, forward_check,
                 backward_check, num_clusters, min_cluster_size,
                 allow_one_daughter_cell=True, varfrac=0.99, max_in_degree=1,
                 max_out_degree=2):

        # requierements for the binary classification
        assert (transitions == np.array((0, 1))).all()
        assert forward_labels == (1, )
        assert backward_labels == (0, )

        super(UnsupervisedEventSelection, self).__init__( \
            graph, transitions, forward_range, backward_range, forward_labels,
            backward_labels, forward_check, backward_check, max_in_degree,
            max_out_degree, allow_one_daughter_cell)

        self.varfrac = varfrac # variance fraction
        self.num_clusters = num_clusters
        self.min_cluster_size = min_cluster_size
        self.tc3data = None

    def _filter_nans(self, data, nodes):
        """Delete columns from data that contain NAN delete items from
        node list accordingly."""

        nans = np.isnan(data)
        col_nans = np.unique(np.where(nans)[1])
        return np.delete(data, col_nans, axis=1), np.delete(nodes, col_nans)

    def _save_class_labels(self, labels, nodes, probabilities,
                           prefix='unsupervised'):
        cmap = unsupervised_cmap(self.num_clusters)

        # clear labels from binary classification
        for node in self.graph.node_list():
            obj = self.graph.node_data(node)
            obj.iLabel = None
            obj.strClassName = None
            obj.strHexColor = None
            obj.dctProb.clear()

        for node, label, probs in zip(nodes, labels.flatten(), probabilities):
            obj = self.graph.node_data(node)
            obj.iLabel = label
            obj.strClassName = "%s-%d" %(prefix, label)
            obj.dctProb = dict((i, v) for i, v in enumerate(probs))
            rgb = cmap(label)
            obj.strHexColor = rgb2hex(rgb)

    def _delete_tracks(self, trackids):
        """Delete tracks by trackid from visitor_data"""
        for startid, results in self.visitor_data.items():
            for trackid in results.keys():
                if trackid in trackids:
                    del self.visitor_data[startid][trackid]

    def _aligned_tracks(self, datadict):
        """Return trackwise aligned matrices of feature data, labels, node ids.
        Shape of matrices ntracks by nframes (by nfreatures).
        """

        data = []
        labels = []
        nodes = []
        trackids = []
        for trackid, track in self.itertracks():
            data.append([datadict[n] for n in track])
            labels.append([self.graph.node_data(n).iLabel for n in track])
            nodes.append(track)
            trackids.append(trackid)
        # take care of array shape,  n_tracks by n_frames by n_features
        # (after pca)
        nodes = np.array(nodes)
        labels = np.array(labels, dtype=int).reshape(nodes.shape)
        data = np.array(data)
        trackids = np.array(trackids)

        return data, labels, nodes, trackids

    def find_events(self):
        data, nodes = self.preprocess()
        self.binary_classification(data)
        super(UnsupervisedEventSelection, self).find_events()

        # pca data, labels after binary classification nodes
        _datadict = dict([(n, f) for n, f in zip(nodes, data)])
        trackdata, labels, tracknodes, trackids = self._aligned_tracks(_datadict)
        event_tolerance = 2  # this parameter might be obsolete!!!
        ues = TC3EventFilter(labels, self.track_length, self.backward_range,
                             event_tolerance, self.num_clusters)

        labels = ues()
        trackdata = ues.delete(trackdata)
        tracknodes = ues.delete(tracknodes)
        trackids_ = ues.delete(trackids)

        self._delete_tracks(np.setdiff1d(trackids, trackids_))
        self.tc3data = self.tc3_analysis(labels, trackdata, tracknodes)

    def preprocess(self):
        """Preprocess data for further analysis

        1) remove columns with zeros
        2) remove columns with NAN's
        3) z-score data
        4) perform pca
        """

        data, nodes = self.data_matrix()

        #import pdb; pdb.set_trace()
        if data.shape[0] <= data.shape[1]:
            msg = ("Not enough objects in data set to proceed",
                   "Number of object is smaller than the number of features",
                   "(%d <= %d)" %tuple(data.shape))
            raise EventSelectionError(msg)

        # delete columns with zeros
        ind = np.where(data==0)[1]
        data = np.delete(data, ind, 1)

        # remove columns with nans
        data, nodes = self._filter_nans(data, nodes)

        data_zs = stats.zscore(data)
        # sss.zscore(self.remove_constant_columns(data))
        pca = mlab.PCA(data_zs)
        # XXX take the minimum to make it more readable
        num_features = np.nonzero(np.cumsum(pca.fracs) > self.varfrac)[0][0]
        data_pca = pca.project(data_zs)[:, 0:num_features]
        return data_pca, nodes

    def binary_classification(self, data):
        """Perform an initial binary classifcation to distinguish between
        mitotic and non-mitotic objects/cells.

        1) Perform kmeans clustering (at least 5 initialisation,
           emperically determined)
        2) and assing mitotic labels (0 means "non-mitotic", 1 "mitotic")
           assuming is that non-mitotic cell are the larger population.
        """

        km = KMeans(n_clusters=2, n_init=5)
        labels = km.fit_predict(data)

        # assign labels, 0 for non-mitotic, 1 for mitotic
        # from now on labels a biologial meaning
        binary_class_names = {0: "non-mitotic", 1: "mitotic"}
        if labels[labels==1].size > labels[labels==0].size:
            labels = np.where(labels, 0, 1)

        for i, node in enumerate(self.graph.node_list()):
            obj = self.graph.node_data(node)
            obj.iLabel = labels[i]
            obj.strClassName = binary_class_names[obj.iLabel]
            obj.strHexColor = rgb2hex(BINARY_CMAP(obj.iLabel), mpl=True)
            obj.dctProb.update({0:np.nan, 1:np.nan})

    def tc3_analysis(self, labels, trackdata, nodes=None):

        ntracks, nframes, nfeatures = trackdata.shape
        trackdata = trackdata.reshape((ntracks*nframes, nfeatures))

        tc = TemporalClustering(nframes, ntracks, self.num_clusters, labels)
        tc3 = tc.tc3_clustering(trackdata, self.min_cluster_size)

        gmm = tc.tc3_gmm(trackdata, tc3.labels.flatten())

        tc3data = dict()
        tc3data["Binary classification"] = labels
        tc3data["TC3"] = tc3.labels
        tc3data["TC3 GMM"] = gmm.labels

        if nodes is not None:
            self._save_class_labels(gmm.labels.flatten(), nodes.flatten(),
                                    gmm.parameters.probabilities, prefix='gmm')

        return tc3data

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

    def _forward_check(self, node_id, node_ids, level=1, found_splitid=None):
        node_ids.append(node_id)

        if ((self.forward_range == -1 and self.graph.out_degree(node_id) == 0) or
            (level >= self.forward_range and self.graph.out_degree(node_id) == 0) or
            (level >= self.forward_range)):
            return True

        if self.graph.in_degree(node_id) > self.max_in_degree:
            return False

        if self.graph.out_degree(node_id) > self.max_out_degree or \
                self.graph.out_degree(node_id) == 0:
            return False

        sample = self.graph.node_data(node_id)
        # check class labels in post duration
        if level <= self.forward_check and not sample.iLabel in self.forward_labels:
            return False

        if (found_splitid is None and
            self.graph.out_degree(node_id) > 1 and
            self.graph.out_degree(node_id) <= self.max_out_degree):
            self.logger.info("     FOUND SPLIT! %s" %node_id)
            found_splitid = node_id
            new_node_ids = []
            if self.allow_one_daughter_cell:
                result = False
            else:
                result = True
            for edgeid in self.graph.out_arcs(node_id):
                new_node_ids.append([])
                tailid = self.graph.tail(edgeid)
                if self.allow_one_daughter_cell:
                    result |= self._forward_check(tailid, new_node_ids[-1],
                                                  level=level+1,
                                                  found_splitid=found_splitid)
                else:
                    result &= self._forward_check(tailid, new_node_ids[-1],
                                                  level=level+1,
                                                  found_splitid=found_splitid)
            node_ids.append(new_node_ids)
            return result
        else:
            out_edgeid = self.graph.out_arcs(node_id)[0]
            tailid = self.graph.tail(out_edgeid)
            return self._forward_check(tailid, node_ids,
                                       level=level+1, found_splitid=found_splitid)
