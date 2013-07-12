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


class HmmSklearn(object):

    def __init__(self, dtable, channel, classdef, ecopts):
        super(HmmSklearn, self).__init__()
        self.dtable = dtable
        self.channel = channel
        self.classdef = classdef
        self.ecopts = ecopts

    def __call__(self):
        np.set_printoptions(precision=2, linewidth=100)
        hmmdata = dict()

        for (name, tracks, probs) in self.dtable.iterby(self.ecopts.sortby):
            est = estimator.HMMProbBasedEsitmator(probs)
            if self.ecopts.constrain_graph:
                cfile = self.ecopts.constrain_files[self.channel]
                hmmc = estimator.HMMConstraint(cfile)
                est.constrain(hmmc)

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

                bucket = HmmBucket(tracks, tracks2,
                                   est.startprob, est.emis, est.trans,
                                   self.dtable.groups(self.ecopts.sortby, name),
                                   tracks.shape[0])
                hmmdata[name] = bucket
        return hmmdata
