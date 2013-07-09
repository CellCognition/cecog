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

import numpy as np

# py2app demands import hooks like this, and it sucks
import lxml.objectify
import lxml.etree
import lxml._elementpath

from cecog.tc3 import normalize


class HMMConstraint(object):

    def __init__(self, filename):

        with open(filename, 'r') as fp:
            xml = lxml.objectify.fromstring(fp.read())
            self.nsymbols = int(xml.numberOfClasses)
            self.nstates = int(xml.numberOfHiddenStates)
            self.start = np.fromstring(str(xml.startNodes), dtype=int, sep=" ")
            self.trans = np.fromstring(str(xml.transitionGraph), dtype=int,
                                       sep=" ")
            self.trans.shape = self.nstates, self.nstates

            self.emis = np.fromstring(str(xml.emissionMatrix), dtype=float,
                                      sep=" ")
            self.emis.shape = self.nstates, self.nsymbols
            self.emis += float(xml.emissionMatrix.attrib['epsilon'])

            # FIXME, try to not use this option for error correction
            h2s0 = np.fromstring(str(xml.hiddenNode2ClassificationNode.current),
                                 dtype=int, sep=' ')
            h2s1 = np.fromstring(str(xml.hiddenNode2ClassificationNode.next),
                                 dtype=int, sep=' ')

            self.hidden2state = h2s1[np.argsort(h2s0)]


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

    def _estimate_emis(self):
        self._emis = np.eye(self.nstates)

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
        self._trans = normalize(hmmc.trans*self._trans, axis=1)
        self._startprob = normalize(hmmc.start*self._startprob)
        self._emis = normalize(hmmc.emis, axis=1)


class HMMProbBasedEsitmator(HMMEstimator):
    """Estimate a hidden markov model from using the prediction
    probabilities from an arbitrary classifier"""

    def __init__(self, probs):
        self._probs = probs
        nstates = probs.shape[-1]
        super(HMMProbBasedEsitmator, self).__init__(nstates)

    def _estimate_trans(self):
        super(HMMProbBasedEsitmator, self)._estimate_trans()
        self._trans[:] = 0.0
        for i in xrange(self._probs.shape[0]):
            for j in xrange(1, self._probs.shape[1]-1, 1):
                prob0 = self._probs[i, j, :]
                prob1 = self._probs[i, j+1, :]
                condprob = np.matrix(prob0).T*np.matrix(prob1)
                self._trans += condprob

        self._trans = normalize(self._trans, axis=1)

    def _estimate_startprob(self):
        super(HMMProbBasedEsitmator, self)._estimate_startprob()
        self._startprob[:] = 0.0
        for i in xrange(self._probs.shape[0]):
            self._startprob += self._probs[i, 1, :]

        self._startprob = normalize(self._startprob)
