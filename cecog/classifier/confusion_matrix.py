"""
confusion_matrix.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import numpy as np


class ConfusionMatrix(object):
    """Store a confusion matrix and to store and compute associated values."""

    def __init__(self, conf):
        """
        @param conf: squared matrix with manual annotations (gold-standard)
          along the rows and predicted values along the columns
        @type conf: numpy array
        """
        assert conf.ndim == 2
        assert conf.shape[0] == conf.shape[1]
        self.conf = conf
        reg = 1.0e-10

        # true-positives
        self.tp = np.diag(self.conf)
        # false-positives
        self.fp = np.sum(self.conf, axis=0) - self.tp
        # false-negatives
        self.fn = np.sum(self.conf, axis=1) - self.tp
        # true-negatives
        self.tn = np.sum(self.conf) - self.tp - self.fn - self.fp

        # sensitivity
        self.se = self.tp / np.asarray(self.tp + self.fn + reg, np.float)
        self.sensitivity = self.se

        # specificity
        self.sp = self.tn / np.asarray(self.tn + self.fp + reg, np.float)
        self.specificity = self.sp

        # accuracy
        self.ac = (self.tp + self.tn) / \
                  np.asarray(self.tp + self.tn + self.fp + self.fn + reg,
                                np.float)

        # positive prediction value (also precision)
        self.ppv = self.tp / np.asarray(self.tp + self.fp + reg, np.float)
        self.precision = self.ppv

        # negative prediction value
        self.npv = self.tn / np.asarray(self.tn + self.fn + reg, np.float)
        # samples
        self.samples = self.tp + self.fn

        # average values weighted by sample number
        nan = -np.isnan(self.se)
        self.wav_se = np.average(self.se[nan], weights=self.samples[nan])
        nan = -np.isnan(self.sp)
        self.wav_sp = np.average(self.sp[nan], weights=self.samples[nan])
        nan = -np.isnan(self.ppv)
        self.wav_ppv = np.average(self.ppv[nan], weights=self.samples[nan])
        nan = -np.isnan(self.npv)
        self.wav_npv = np.average(self.npv[nan], weights=self.samples[nan])
        nan = -np.isnan(self.ac)
        self.wav_ac = np.average(self.ac[nan], weights=self.samples[nan])

        # average values (not weighted by sample number)
        self.av_se = np.average(self.se[-np.isnan(self.se)])
        self.av_sp = np.average(self.sp[-np.isnan(self.sp)])
        self.av_ppv = np.average(self.ppv[-np.isnan(self.ppv)])
        self.av_npv = np.average(self.npv[-np.isnan(self.npv)])
        self.av_ac = np.average(self.ac[-np.isnan(self.ac)])

        # average accuracy per class
        self.ac_class = self.av_ac

        # accuracy per item (true-positives divided by all decisions)
        self.ac_sample = np.sum(self.tp) / np.sum(self.samples + reg,
                                                        dtype=np.float)

    def __len__(self):
        return self.conf.shape[0]

    def  __getitem__(self, *args, **kw):
        return self.conf.__getitem__(*args, **kw)
