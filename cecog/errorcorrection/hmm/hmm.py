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

__all__ = ['HmmCore', 'LabelMapper']

from copy import deepcopy
import numpy as np

from cecog.errorcorrection.hmm import estimator


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


class HmmCore(object):

    def __init__(self, dtable, channel, classdef, ecopts):
        super(HmmCore, self).__init__()
        self.dtable = dtable
        self.channel = channel
        self.classdef = classdef
        self.ecopts = ecopts

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
