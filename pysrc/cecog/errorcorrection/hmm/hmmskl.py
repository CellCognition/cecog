"""
skhmm.py

fixes some issues of sklearn.hmm

1) Epsilon value in the normalize function
2) check_input_symbols is disabled (returns always True)
3) fit method returns list of log-likelihoods
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["HmmSklearn"]


import numpy as np
from sklearn import hmm
from sklearn.utils.extmath import logsumexp

from cecog.tc3 import normalize
from cecog.errorcorrection import HmmBucket
from cecog.errorcorrection.hmm import HmmCore
from cecog.errorcorrection.hmm import estimator
from cecog.errorcorrection.hmm import LabelMapper


EPS = 1e-99
decoder_algorithms = ("viterbi", "map")


class MultinomialHMM(hmm.MultinomialHMM):
    """Subclass of sklearns MultinomialHMM. It fixes numerical issues and
    and overwrite the method check_input_symbols. Furhter the fit method
    return the learning curve (log-likelihood) after each iteration."""

    def __init__(self, *args, **kw):
        super(MultinomialHMM, self).__init__(*args, **kw)

    def _get_startprob(self, *args, **kw):
        return super(MultinomialHMM, self)._get_startprob(*args, **kw)

    def _set_startprob(self, startprob):
        if startprob is None:
            startprob = np.tile(1.0 / self.n_components, self.n_components)
        else:
            startprob = np.asarray(startprob, dtype=np.float)

        if not np.alltrue(startprob):
            startprob = normalize(startprob, eps=EPS)

        if len(startprob) != self.n_components:
            raise ValueError('startprob must have length n_components')
        if not np.allclose(np.sum(startprob), 1.0):
            raise ValueError('startprob must sum to 1.0')

        self._log_startprob = np.log(np.asarray(startprob).copy())

    startprob_ = property(_get_startprob, _set_startprob)

    def _get_transmat(self, *args, **kw):
        return super(MultinomialHMM, self)._get_transmat(*args, **kw)

    def _set_transmat(self, transmat):

        if transmat is None:
            transmat = np.tile(1.0 / self.n_components,
                               (self.n_components, self.n_components))

        if not np.alltrue(transmat):
            transmat = normalize(transmat, axis=1, eps=EPS)

        if (np.asarray(transmat).shape \
            != (self.n_components, self.n_components)):
            raise ValueError('transmat must have shape '
                             '(n_components, n_components)')


        if not np.all(np.allclose(np.sum(transmat, axis=1), 1.0)):
            raise ValueError('Rows of transmat must sum to 1.0')

        self._log_transmat = np.log(np.asarray(transmat).copy())
        underflow_idx = np.isnan(self._log_transmat)
        self._log_transmat[underflow_idx] = -np.inf

    transmat_ = property(_get_transmat, _set_transmat)

    def _check_input_symbols(self, obs):
        return True

    def fit(self, obs):

        # same implementation as in sklearn, but returns the learning curve
        if self.algorithm not in decoder_algorithms:
            self._algorithm = "viterbi"

        self._init(obs, self.init_params)

        logprob = []
        for i in range(self.n_iter):
            # Expectation step
            stats = self._initialize_sufficient_statistics()
            curr_logprob = 0
            for seq in obs:
                framelogprob = self._compute_log_likelihood(seq)
                lpr, fwdlattice = self._do_forward_pass(framelogprob)
                bwdlattice = self._do_backward_pass(framelogprob)
                gamma = fwdlattice + bwdlattice
                posteriors = np.exp(gamma.T - logsumexp(gamma, axis=1)).T
                curr_logprob += lpr
                self._accumulate_sufficient_statistics(
                    stats, seq, framelogprob, posteriors, fwdlattice,
                    bwdlattice, self.params)
            logprob.append(curr_logprob)

            # Check for convergence.
            if i > 0 and abs(logprob[-1] - logprob[-2]) < self.thresh:
                break

            # Maximization step
            self._do_mstep(stats, self.params)

        return logprob


class HMMBaumWelchEstimator(estimator.HMMEstimator):
    """Baum-Welch estimator based on sklearn MultinomialHMM"""

    def __init__(self, states, estimator, tracks):
        # tracks have been mapped to array indices already
        super(HMMBaumWelchEstimator, self).__init__(states)
        self._trans = estimator.trans
        self._emis = estimator.emis
        self._startprob = estimator.startprob

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


class HmmSklearn(HmmCore):

    def __init__(self, *args, **kw):
        super(HmmSklearn, self).__init__(*args, **kw)

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
        if self.ecopts.eventselection == self.ecopts.EVENTSELECTION_SUPERVISED \
                and probs is not None:
            est = estimator.HMMProbBasedEstimator(states, probs, tracks)
        else:
            est = estimator.HMMTransitionCountEstimator(states, tracks)
            probs = None # can't use probs for unsupervied learning yet

        # Baum Welch performs bad with bad start values
        # if self.ecopts.hmm_algorithm == self.ecopts.HMM_BAUMWELCH:
        est = HMMBaumWelchEstimator(states, est, tracks)

        return est


    def __call__(self):
        hmmdata = dict()

        for (name, tracks, probs, objids) in  \
                self.dtable.iterby(self.ecopts.sortby, True):
            if tracks is probs is None:
                hmmdata[name] = None
                continue

            labelmapper = LabelMapper(np.unique(tracks),
                                      self.classdef.class_names.keys())

            # np.unique -> sorted ndarray
            idx = labelmapper.index_from_classdef(np.unique(tracks))
            idx.sort()
            # no prediction probabilities available
            if probs is not None:
                probs = probs[:, :, idx]
            est = self._get_estimator(probs, labelmapper.label2index(tracks))
            est.constrain(self.hmmc(est, labelmapper))

            # ugly sklearn
            hmm_ = MultinomialHMM(n_components=est.nstates)
            hmm_.startprob_ = est.startprob
            hmm_.transmat_ = est.trans
            hmm_.emissionprob_ = est.emis

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
                               objids[:, 0], # startids
                               self.ecopts.timelapse)
            hmmdata[name] = bucket
        return hmmdata
