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
import sklearn.hmm as hmm

from cecog.errorcorrection import HmmBucket
from cecog.errorcorrection.hmm import estimator


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
        """

        if self.ecopts.eventselection == self.ecopts.EVENTSELECTION_SUPERVISED:
            return estimator.HMMProbBasedEsitmator(probs)
        else:
            states = np.array(self.classdef.class_names.keys())
            return estimator.HMMTransitionCountEstimator(tracks, states)


class HmmSklearn(HMMCore):

    def __init__(self, *args, **kw):
        super(HmmSklearn, self).__init__(*args, **kw)

    def hmmc(self, est):
        """Return either the default constrain for the hidden markov model or
        the one that is provided by the options."""
        if self.ecopts.hmm_constrain[self.channel] is None:
            # default constrain for hidden markov model
            hmmc = estimator.HMMSimpleLeft2RightConstraint(est.nstates)
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
            hmm_ = hmm.MultinomialHMM(n_components=est.nstates)
            hmm_._set_startprob(est.startprob)
            hmm_._set_transmat(est.trans)
            hmm_._set_emissionprob(est.emis)

            # trackwise error correction
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
