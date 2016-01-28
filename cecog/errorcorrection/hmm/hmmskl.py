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
from cecog.errorcorrection import HmmBucket
from cecog.errorcorrection.hmm import HmmCore
from cecog.errorcorrection.hmm import estimator
from cecog.errorcorrection.hmm import LabelMapper
from cecog.learning.hmm import MultinomialHMM


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

        for (name, tracks, probs, objids, coords) in  \
                self.dtable.iterby(self.ecopts.sortby, True):
            if tracks is probs is None:
                hmmdata[name] = None
                continue

            labelmapper = LabelMapper(np.unique(tracks),
                                      self.classdef.names.keys())

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
                               objids,
                               coords,
                               self.ecopts.timelapse)
            hmmdata[name] = bucket
        return hmmdata
