"""
hmmestimator.py

Esitmators for Hidden Markov Models.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from os.path import join
import numpy as np

# py2app demands import hooks like this and it sucks
import lxml.objectify
import lxml.etree
import lxml._elementpath

from cecog.tc3 import normalize
from cecog.environment import find_resource_dir


class HMMConstraintCore(object):

    def __init__(self, nstates):
        super(HMMConstraintCore, self).__init__()
        self.nstates = nstates


class HMMSimpleLeft2RightConstraint(HMMConstraintCore):
    """"Simplest constraint on an Hidden Markov Models
    1) number of emission is equal to the number of states
    2) equal start probabilities
    3) simple left 2 right Models
    """

    def __init__(self, nstates):
        super(HMMSimpleLeft2RightConstraint, self).__init__(nstates)
        self.trans = np.eye(nstates)
        for i in xrange(nstates):
            try:
                self.trans[i, i+1] = 1
            except IndexError:
                self.trans[i, 0] = 1

        self.emis= np.eye(nstates)
        self.start = np.ones(nstates, dtype=float)/nstates


class HMMSimpleConstraint(HMMConstraintCore):
    """Simple Constraint for Hidden Markov Models

    1) all state transitions are allowed
    2) all states are allowed as start states
    3) emissions with just a little noise
    """

    def __init__(self, nstates):
        super(HMMSimpleConstraint, self).__init__(nstates)
        self.trans = np.ones((nstates, nstates))
        self.emis = np.ones((nstates, nstates))
        self.start = np.ones(nstates)


class HMMConstraint(HMMConstraintCore):

    def __init__(self, filename):

        with open(filename, 'r') as fp:
            xml = lxml.objectify.fromstring(fp.read())
            self.validate(xml)
            self.nsymbols = int(xml.n_emissions)
            nstates = int(xml.n_states)

            self.start = np.fromstring(str(xml.start_probabilities),
                                       dtype=float, sep=" ")

            self.trans = np.fromstring(str(xml.transition_matrix), dtype=float,
                                       sep=" ")
            self.trans.shape = nstates, nstates

            self.emis = np.fromstring(str(xml.emission_matrix), dtype=float,
                                      sep=" ")
            self.emis.shape = nstates, self.nsymbols
        super(HMMConstraint, self).__init__(nstates)

    def validate(self, xml):
        schemafile = join(find_resource_dir(), "schemas", "hmm_constraint.xsd")
        schema_doc =  lxml.etree.parse(schemafile)
        return lxml.etree.XMLSchema(schema_doc).assertValid(xml)

    def remove_spare_constraints(self, indices):
        """Remove rows and columns from the masks for transition, emission and
        start probablity matrices.
        """
        self.start = np.delete(self.start, indices)
        self.emis = np.delete(self.emis, indices, axis=0)
        self.emis = np.delete(self.emis, indices, axis=1)
        self.trans = np.delete(self.trans, indices, axis=0)
        self.trans = np.delete(self.trans, indices, axis=1)


class HMMEstimator(object):
    """Setup a (naive) default hidden markov (left-to-right model)

    Default model for e.g. three states:

    # transition matrix
    A = ((0.9, 0.1, 0.0),
         (0.0, 0.9. 0.1),
         (0.1, 0.0, 0.9))

    # emission matrix
    B = ((1, 0, 0),
         (0, 1, 0),
         (0, 0, 1))

    # start probabilities
    PI = (1, 0, 0)
    """
    def __init__(self, states):
        super(HMMEstimator, self).__init__()
        self.states = states

        self._estimate_trans()
        self._estimate_emis()
        self._estimate_startprob()

    @property
    def nstates(self):
        return self.states.size

    def _estimate_trans(self):
        self._trans = 0.9*np.eye(self.nstates)
        for i, row in enumerate(self.trans):
            try:
                row[i+1] = 0.1
            except IndexError:
                row[0] = 0.1

    @property
    def _emission_noise(self):
        return 0.03

    def _estimate_emis(self):
        self._emis = np.eye(self.nstates) + self._emission_noise
        self._emis = normalize(self._emis, axis=1, eps=0.0)

    def _estimate_startprob(self):
        self._startprob = np.zeros(self.nstates)
        self._startprob[0] = 1.0

    @property
    def trans(self):
        return self._trans

    @property
    def emis(self):
        return self._emis

    @property
    def startprob(self):
        return self._startprob

    def constrain(self, hmmc):
        self._trans = normalize(hmmc.trans*self._trans, axis=1, eps=0.0)
        self._startprob = normalize(hmmc.start*self._startprob, eps=0.0)
        self._emis = normalize(hmmc.emis*self._emis, axis=1, eps=0.0)


class HMMProbBasedEstimator(HMMEstimator):
    """Estimate a hidden markov model from using the prediction
    probabilities from an arbitrary classifier.
    """

    # number of frames to consider as noise
    NOISE_FACTOR = 1.0

    def __init__(self, states, probs, tracks):
        self._probs = probs
        self._tracks = tracks
        super(HMMProbBasedEstimator, self).__init__(states)

    @property
    def _emission_noise(self):
        return self.NOISE_FACTOR/self._probs.shape[1]/self.nstates

    def _estimate_trans(self):
        super(HMMProbBasedEstimator, self)._estimate_trans()
        self._trans[:] = 0.0
        for i in xrange(self._probs.shape[0]): # tracks
            for j in xrange(1, self._probs.shape[1], 1): # frames
                prob0 = self._probs[i, j-1, :]
                prob1 = self._probs[i, j, :]
                condprob = np.matrix(prob0).T*np.matrix(prob1)
                self._trans += condprob
        self._trans = normalize(self._trans, axis=1, eps=0.0)

    def _estimate_startprob(self):
        super(HMMProbBasedEstimator, self)._estimate_startprob()
        self._startprob[:] = 0.0
        self._startprob = self._probs[:, 0, :].sum(axis=0)
        self._startprob = normalize(self._startprob, eps=0.0)

        # using weights takes only classes into accout that appear into
        # the first frame
        # weights = np.bincount(np.argmax(self._probs[:,0,:], axis=1),
        #                       minlength=self.nstates).astype(float)
        # weights /= weights.sum()
        # self._startprob = normalize(self._startprob*weights, eps=0.0)


    def _estimate_emis(self):
        """Estimate the emission matrix by calculating the mean prediction
        probabiliy for each class. The result is normalized row wise.
        """
        mprobs = np.zeros((self.nstates, self.nstates))

        probs = self._probs.reshape((-1, self.nstates))
        tracks = self._tracks.flatten()

        for i in xrange(self.nstates):
            mprobs[i, :] = probs[tracks == i].mean(axis=0)

        self._emis = normalize(mprobs, axis=1)


class HMMTransitionCountEstimator(HMMEstimator):

    # a noise factor fo 1 considers one frame as noise
    NOISE_FACTOR = 1.0

    def __init__(self, states, tracks):
        self._tracks = tracks
        super(HMMTransitionCountEstimator, self).__init__(states)

    @property
    def _emission_noise(self):
        return self.NOISE_FACTOR/self._tracks.shape[1]/self.nstates

    def _estimate_trans(self):
        """Estimates the transition probaility by counting."""
        super(HMMTransitionCountEstimator, self)._estimate_trans()
        self._trans[:] = 0.0
        index_of = lambda label: np.where(self.states==label)[0][0]
        _tracks = self._tracks.flatten()

        for i, label in enumerate(_tracks):
            for state in self.states:
                try:
                    if (_tracks[i+1] == state):
                        self._trans[index_of(label), index_of(state)] += 1.0
                        continue
                except IndexError:
                    pass

        self._trans =  normalize(self._trans, axis=1, eps=0.0)
        return self._trans

    def _estimate_startprob(self):
        super(HMMTransitionCountEstimator, self)._estimate_startprob()
        self.startprob[:] = 0.0

        index_of = lambda label: np.where(self.states==label)[0][0]
        counts =  np.bincount(self._tracks[:, 0].flatten())
        for label in np.unique(self._tracks[:, 0]):
            self.startprob[index_of(label)] = counts[label]

        self._startprob = normalize(self._startprob, eps=0.0)
        return self._startprob
