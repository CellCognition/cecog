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
from cecog.errorcorrection.hmm.skhmm import MultinomialHMM


class HMMSimpleLeft2RightConstraint(object):
    """"Simplest constraint on an Hidden Markov Models
    1) number of emission is equal to the number of states
    2) equal start probabilities
    3) simple left 2 right Models
    """

    def __init__(self, nstates):
        self.trans = np.eye(nstates)
        for i in xrange(nstates):
            try:
                self.trans[i, i+1] = 1
            except IndexError:
                self.trans[i, 0] = 1

        self.emis= np.eye(nstates)
        self.start = np.ones(nstates, dtype=float)/nstates


class HMMSimpleConstraint(object):
    """Simple Constraint for Hidden Markov Models

    1) all state transitions are allowed
    2) all states are allowed as start states
    3) emissions with just a little noise
    """

    def __init__(self, nstates):
        self.trans = np.ones((nstates, nstates))
        self.emis = np.ones((nstates, nstates))
        self.start = np.ones(nstates)


class HMMConstraint(object):

    def __init__(self, filename):

        with open(filename, 'r') as fp:
            xml = lxml.objectify.fromstring(fp.read())
            self.validate(xml)
            self.nsymbols = int(xml.n_emissions)
            self.nstates = int(xml.n_states)

            self.start = np.fromstring(str(xml.start_probabilities),
                                       dtype=float, sep=" ")

            self.trans = np.fromstring(str(xml.transition_matrix), dtype=float,
                                       sep=" ")
            self.trans.shape = self.nstates, self.nstates

            self.emis = np.fromstring(str(xml.emission_matrix), dtype=float,
                                      sep=" ")
            self.emis.shape = self.nstates, self.nsymbols

    def validate(self, xml):
        schemafile = join(find_resource_dir(), "schemas", "hmm_constraint.xsd")
        schema_doc =  lxml.etree.parse(schemafile)
        return lxml.etree.XMLSchema(schema_doc).assertValid(xml)


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
    def __init__(self, nstates):
        super(HMMEstimator, self).__init__()
        self.nstates = nstates

        self._estimate_trans()
        self._estimate_emis()
        self._estimate_startprob()


    def _estimate_trans(self):
        self._trans = 0.9*np.eye(self.nstates)
        for i, row in enumerate(self.trans):
            try:
                row[i+1] = 0.1
            except IndexError:
                row[0] = 0.1

    @property
    def _emission_noise(self):
        return 0.05

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


class HMMProbBasedEsitmator(HMMEstimator):
    """Estimate a hidden markov model from using the prediction
    probabilities from an arbitrary classifier.
    """

    # number of frames to consider as noise
    N_NOISE_FRAMES = 2.0

    def __init__(self, probs):
        self._probs = probs
        nstates = probs.shape[-1]
        super(HMMProbBasedEsitmator, self).__init__(nstates)

    @property
    def _emission_noise(self):
        return self.N_NOISE_FRAMES/self._probs.shape[1]

    def _estimate_trans(self):
        super(HMMProbBasedEsitmator, self)._estimate_trans()
        self._trans[:] = 0.0
        for i in xrange(self._probs.shape[0]):
            for j in xrange(1, self._probs.shape[1]-1, 1):
                prob0 = self._probs[i, j, :]
                prob1 = self._probs[i, j+1, :]
                condprob = np.matrix(prob0).T*np.matrix(prob1)
                self._trans += condprob

        self._trans = normalize(self._trans, axis=1, eps=0.0)

    def _estimate_startprob(self):
        super(HMMProbBasedEsitmator, self)._estimate_startprob()
        self._startprob[:] = 0.0
        for i in xrange(self._probs.shape[0]):
            self._startprob += self._probs[i, 1, :]

        self._startprob = normalize(self._startprob, eps=0.0)


class HMMTransitionCountEstimator(HMMEstimator):

    # number of frames to consider as noise
    N_NOISE_FRAMES = 2.0

    def __init__(self, tracks, states):
        self._tracks = tracks
        self._states = states
        super(HMMTransitionCountEstimator, self).__init__(states.size)

    @property
    def _emission_noise(self):
        return self.N_NOISE_FRAMES/self._tracks.shape[1]

    def _estimate_trans(self):
        """Estimates the transition probaility by counting."""

        super(HMMTransitionCountEstimator, self)._estimate_trans()
        self._trans[:] = 0.0
        index_of = lambda label: np.where(self._states==label)[0][0]
        _tracks = self._tracks.flatten()
        for i, label in enumerate(_tracks):
            for state in self._states:
                try:
                    if (_tracks[i+1] == state) and (label >= state):
                        self._trans[index_of(state), index_of(label)] += 1.0
                except IndexError:
                    pass

        # make transisition cyclic
        self._trans[-1, 0] = self._trans[0,-1]
        self._trans =  normalize(self._trans, axis=1, eps=0.0)
        return self._trans

    def _estimate_startprob(self):
        super(HMMTransitionCountEstimator, self)._estimate_startprob()
        self.startprob[:] = 0.0
        counts =  np.bincount(self._tracks[:, 0].flatten())
        for i, c in enumerate(counts):
            self.startprob[i] = c
        self._startprob = normalize(self._startprob, eps=0.0)
        return self._startprob

class HMMBaumWelchEstimator(HMMEstimator):

    def __init__(self, estimator, tracks):
        super(HMMBaumWelchEstimator, self).__init__(estimator.nstates)
        # the initialisation is essential!
        hmm_ = MultinomialHMM(n_components=estimator.nstates,
                              transmat=estimator.trans,
                              startprob=estimator.startprob,
                              n_iter=1000,
                              init_params="")
        hmm_.emissionprob_ = estimator.emis

        hmm_.fit(tracks)

        self._trans = hmm_.transmat_
        self._emis = hmm_.emissionprob_
        self._startprob = hmm_.startprob_
