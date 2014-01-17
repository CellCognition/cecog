"""
hmmtde.py

Hiddem Markov Model with time dependent emissions.
(Replacement for the old R-code)

Unfortunately the R code contain some adhoc assumptions like the
emission matrix as unit matrix.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['HmmTde']


import numpy as np
from cecog.tc3 import normalize
from cecog.errorcorrection import HmmBucket
from cecog.errorcorrection.hmm import HmmCore
from cecog.errorcorrection.hmm import estimator
from cecog.errorcorrection.hmm import LabelMapper


class TdeEstimator(estimator.HMMProbBasedEstimator):

    def __init__(self, *args, **kw):
        super(TdeEstimator, self).__init__(*args, **kw)

    @property
    def _emission_noise(self):
        # adhoc assumption
        return 0.001

    def _estimate_emis(self):
        """This emission is an adhoc-assumtiopn!"""
        self._emis = normalize(np.eye(self.nstates) + self._emission_noise,
                               eps=0.0)


class HmmTde(HmmCore):
    """Hidden Markov model that uses a time dependend emission."""

    def __init__(self, *args, **kw):
        super(HmmTde, self).__init__(*args, **kw)

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
        est = TdeEstimator(states, probs, tracks)

        return est

    def decode(self, tracks, probs, est):
        tracks2 = np.empty(tracks.shape, dtype=int)

        for i, track in enumerate(tracks):
            ntracks = len(tracks)
            nframes = len(tracks[0])
            emis = np.zeros((nframes, est.nstates))

            P  = np.zeros((nframes, est.nstates))
            # first row doesn't get updated later
            bp = np.zeros((nframes, est.nstates), dtype=int) - 1
            P2 = np.zeros((est.nstates, est.nstates))


            # setup the time dependend emssion matrix
            for j in xrange(est.nstates):
                emis += np.tile(est.emis[:, j], (nframes, 1))* \
                    np.tile(probs[i, :, j], (est.nstates, 1)).T

            P[0, ] = est.startprob*emis[0, :]
            # loop over frames
            for fi in xrange(1, nframes, 1):
                # loop over hidden states
                for ni in xrange(est.nstates):
                    P2[ni, :] = P[fi-1, ni] * est.trans[ni, :]*emis[fi, :]

                for ni in xrange(est.nstates):
                    P[fi, ni] = P2[:, ni].max()
                    bp[fi, ni] = np.argmax(P2[:, ni])

            tracks2[i, nframes-1] = np.argmax(P[nframes-1, :])
            for fi in xrange(nframes-1, 0, -1):
                tracks2[i, fi-1] = bp[fi, tracks2[i, fi]]

        return tracks2

    def __call__(self):
        hmmdata = dict()

        for (name, tracks, probs, finfo) in  \
                self.dtable.iterby(self.ecopts.sortby, True):
            if tracks is probs is finfo is None:
                hmmdata[name] = None
                continue

            labelmapper = LabelMapper(np.unique(tracks),
                                      self.classdef.class_names.keys())

            # np.unique -> sorted ndarray
            idx = labelmapper.index_from_classdef(np.unique(tracks))
            idx.sort()
            probs = probs[:, :, idx]
            est = self._get_estimator(probs, labelmapper.label2index(tracks))
            est.constrain(self.hmmc(est, labelmapper))

            tracks2 = self.decode(tracks, probs, est)
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
