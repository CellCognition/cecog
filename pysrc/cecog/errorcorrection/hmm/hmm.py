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

import numpy as np
from cecog.errorcorrection.hmm import estimator

class HMM(object):

    def __init__(self, dtable, channel, classdef, outdir, ecopts):
        super(HMM, self).__init__()
        self.dtable = dtable
        self.channel = channel
        self.classdef = classdef
        self.outdir = outdir
        self.ecopts = ecopts

    def __call__(self):

        np.set_printoptions(precision=2)
        for (name, labels, probs) in self.dtable.iterpos():
            est = estimator.HMMProbBasedEsitmator(probs)
            if self.ecopts.constrain_graph:
                cfile = self.ecopts.constrain_files[self.channel]
                hmmc = estimator.HMMConstraint(cfile)
                est.constrain(hmmc)

                print est.startprob
                print est.trans
                print est.emis
