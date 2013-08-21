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


import numpy as np

from cecog.errorcorrection import HmmBucket
from cecog.errorcorrection.hmm import estimator
from cecog.errorcorrection.hmm.skhmm import MultinomialHMM

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

        if self.ecopts.eventselection == self.ecopts.EVENTSELECTION_SUPERVISED:
            est = estimator.HMMProbBasedEsitmator(probs)
        else:
            states = np.array(self.classdef.class_names.keys())
            est = estimator.HMMTransitionCountEstimator(tracks, states)

        # Baum Welch performs bad with bad start values
        est = estimator.HMMBaumWelchEstimator(
            est, self.classdef.label2index(tracks))
        return est

class HmmSklearn(HMMCore):

    def __init__(self, *args, **kw):
        super(HmmSklearn, self).__init__(*args, **kw)

    def hmmc(self, est):
        """Return either the default constrain for the hidden markov model or
        the one that is provided by the options."""
        if self.ecopts.hmm_constrain[self.channel] is None:
            # default constrain for hidden markov model
            hmmc = estimator.HMMSimpleConstraint(est.nstates)
        else:
            hmmc = self.ecopts.hmm_constrain[self.channel]
        return hmmc

    def __call__(self):
        hmmdata = dict()

        for (name, tracks, probs, finfo) in  \
                self.dtable.iterby(self.ecopts.sortby, True):
            if tracks is probs is finfo is None:
                hmmdata[name] = None
                continue
            est = self._get_estimator(probs, tracks)
            est.constrain(self.hmmc(est))

            # ugly sklearn
            hmm_ = MultinomialHMM(n_components=est.nstates)
            hmm_.startprob_ = est.startprob
            hmm_.transmat_ = est.trans
            hmm_.emissionprob_ = est.emis

            tracks2 = []
            for track in self.classdef.label2index(tracks):
                tracks2.append(hmm_.predict(track))
            tracks2 = self.classdef.index2labels(np.array(tracks2, dtype=int))

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
