"""
hmm.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['HmmSklearn']

from copy import deepcopy
import numpy as np

from cecog.errorcorrection import HmmBucket
from cecog.errorcorrection.hmm import estimator
from cecog.errorcorrection.hmm.skhmm import MultinomialHMM

class LabelMapper(object):
    """Map class labels to array index.

    One can define two different mappings:
    The first is used to map observation from tracks to array indices
    of e.g. a transition matrix of an hmm. The second one is used to map
    the class labels (from a svm class definition) to array indices.
    """

    def __init__(self, labels, class_labels):
        self._labels = labels
        self._class_labels = class_labels

    def label2index(self, labels):
        """Map arb. labels to [0, ..., n-1] that they can used as
        array index."""
        indices = np.empty(labels.shape, dtype=int)
        for index, label in enumerate(self._labels):
            indices[labels==label] = index
        return indices

    def index2labels(self, indices):
        """Reverse label index mapping."""
        labels = np.empty(indices.shape, dtype=int)
        for index, label in enumerate(self._labels):
            labels[indices==index] = label
        return labels

    def index_from_classdef(self, labels):
        """Maps labels from a class defintion to an array index.

        Basic functionality is the same as in 'labes2index' but a trajectory
        contains not necessarily  all class labels defined in the
        class defintion.
        """
        indices = np.empty(labels.shape, dtype=int)
        for index, label in enumerate(self._class_labels):
            indices[labels==label] = index
        return indices


class HMMCore(object):

    def __init__(self, dtable, channel, classdef, ecopts):
        super(HMMCore, self).__init__()
        self.dtable = dtable
        self.channel = channel
        self.classdef = classdef
        self.ecopts = ecopts

    def _get_estimator(self, probs, tracks):
        """Helper function to return the hmm-estimator instance i.e.

        - probability based estimator for svm classifier
        - transition count based estimator for unsupervied clustering

        There are 2 levels:
        1) inital estimate by counting or conditional probalilities, those
           values are used as inital trans, emis startprob for the
        2) Baum Welch algorithm.
        """

        states = np.unique(tracks)
        if self.ecopts.eventselection == self.ecopts.EVENTSELECTION_SUPERVISED:
            est = estimator.HMMProbBasedEsitmator(states, probs)
        else:
            est = estimator.HMMTransitionCountEstimator(states, tracks)
            probs = None # can't use probs for unsupervied learning yet

        # Baum Welch performs bad with bad start values
        est = estimator.HMMBaumWelchEstimator(
            states, est, tracks, probs)
        return est


class HmmSklearn(HMMCore):

    def __init__(self, *args, **kw):
        super(HmmSklearn, self).__init__(*args, **kw)

    def hmmc(self, est, labelmapper):
        """Return either the default constrain for the hidden markov model or
        the one that is provided by the options."""
        if self.ecopts.hmm_constrain[self.channel] is None:
            # default constrain for hidden markov model
            hmmc = estimator.HMMSimpleConstraint(est.nstates)
        else:

            hmmc = deepcopy(self.ecopts.hmm_constrain[self.channel])

            # if certain labels are not measured in a track, one
            # must remove their constraints.
            labels = labelmapper.index_from_classdef(
                labelmapper.index2labels(est.states))
            delstates = np.setdiff1d(np.arange(hmmc.nstates, dtype=int), labels)

            if len(delstates) > 0:
                hmmc.remove_spare_constraints(delstates)

        return hmmc

    def __call__(self):
        hmmdata = dict()

        for (name, tracks, probs, finfo) in  \
                self.dtable.iterby(self.ecopts.sortby, True):
            labelmapper = LabelMapper(np.unique(tracks),
                                      self.classdef.class_names.keys())

            if tracks is probs is finfo is None:
                hmmdata[name] = None
                continue

            probs = probs[:, :, labelmapper.index_from_classdef(np.unique(tracks))]
            est = self._get_estimator(probs, labelmapper.label2index(tracks))
            est.constrain(self.hmmc(est, labelmapper))

            # ugly sklearn
            hmm_ = MultinomialHMM(n_components=est.nstates)
            hmm_.startprob_ = est.startprob
            hmm_.transmat_ = est.trans
            hmm_.emissionprob_ = est.emis
            # line below may improve the performance if
            # e.g. on class (apo) is not present
            # hmm_.emissionprob_ = est.mean_probs*est.emis

            tracks2 = []
            for track in labelmapper.label2index(tracks):
                tracks2.append(hmm_.predict(track))
            tracks2 = labelmapper.index2labels(np.array(tracks2, dtype=int))

            bucket = HmmBucket(tracks,
                               tracks2,
                               est.startprob,
                               est.emis,
                               est.trans,
                               self.dtable.groups(self.ecopts.sortby, name),
                               tracks.shape[0],
                               self.ecopts.timelapse, finfo)
            hmmdata[name] = bucket
        return hmmdata
