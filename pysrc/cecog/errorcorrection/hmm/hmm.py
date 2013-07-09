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

import os
import numpy as np
import sklearn.hmm as hmm
from cecog.errorcorrection.hmm import estimator
from cecog.tc3 import normalize

from cecog.plots import trajectories

class HMM(object):

    def __init__(self, dtable, channel, classdef, outdir, ecopts):
        super(HMM, self).__init__()
        self.dtable = dtable
        self.channel = channel
        self.classdef = classdef
        self.outdir = outdir
        self.ecopts = ecopts

    def __call__(self):

        np.set_printoptions(precision=2, linewidth=100)

        for (name, tracks, probs) in self.dtable.iterby(self.ecopts.sortby):
            est = estimator.HMMProbBasedEsitmator(probs)
            if self.ecopts.constrain_graph:
                cfile = self.ecopts.constrain_files[self.channel]
                hmmc = estimator.HMMConstraint(cfile)
                est.constrain(hmmc)
                hmm_ = hmm.MultinomialHMM(n_components=est.nstates)

                # ugly sklearn
                hmm_._set_startprob(est.startprob)
                hmm_._set_transmat(est.trans)
                hmm_._set_emissionprob(est.emis)

                # trackwise error correction
                tracks2 = []
                for track in self.classdef.label2index(tracks):
                    tracks2.append(hmm_.predict(track))
                tracks2 = self.classdef.index2labels(np.array(tracks2, dtype=int))

                fig = trajectories(tracks, labels=(3,4), title='svm',
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize)
                fig.savefig('/Users/hoefler/pdf/%s-svm.pdf' %name)
                fig = trajectories(tracks2, labels=(3,4), title='hmm',
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize)
                fig.savefig('/Users/hoefler/pdf/%s-hmm.pdf' %name)

        # model_params = DHmmParams(dhmm.emissionprob_, dhmm.transmat_)
        # data = TC3Container('DHMM', model_params, labels)
        # return data
