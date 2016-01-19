# -*- coding: utf-8 -*-
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

    def export(self, filename, sep='\t', mapping=None):
        f = file(filename, 'w')

        #data = self.ac.copy()
        overall = np.asarray([np.sum(self.samples),
                                 self.av_ac, self.av_se, self.av_sp,
                                 self.av_ppv, self.av_npv])
        woverall = np.asarray([np.sum(self.samples),
                                  self.wav_ac, self.wav_se, self.wav_sp,
                                  self.wav_ppv, self.wav_npv])
        data = np.vstack((self.samples,
                             self.ac, self.se, self.sp,
                             self.ppv, self.npv))
        data2 = data.swapaxes(0,1)
        f.write('%s\n' % sep.join(['Class', 'Samples',
                                   'AC', 'SE', 'SP', 'PPV', 'NPV']))
        for idx, items in enumerate(data2):
            c = idx if mapping is None else mapping[idx]
            f.write('%s\n' % sep.join(map(str, [c]+list(items))))
        f.write('%s\n' % sep.join(map(str, ['overall']+list(overall))))
        f.write('%s\n' % sep.join(map(str, ['woverall']+list(woverall))))
        f.write('\nAccuracy per sample%s%.2f\n' % (sep, self.ac_sample*100.))
        f.close()

    @classmethod
    def from_pairs(cls, pairs, class_labels):
        """
        Constructs a ConfusionMatrix object from a list of pairs of the form
        (true label, predicted label).

        Requires a list of class labels in the same order as labels should appear
        in the confusion matrix.

        @param pairs: list of pairs (tuples) in the form
          (true label, predicted label)
        @type pairs: sequence
        @param mapping: mapping of original to new labels
        @type mapping: dict

        @return: ConfusionMatrix
        """

        k = len(class_labels)
        conf = np.zeros((k, k))
        for l, v in pairs:
            l2 = class_labels.index(l)
            v2 = class_labels.index(v)
            conf[l2, v2] += 1
        return cls(conf)

    @classmethod
    def from_lists(cls, labels, predictions, class_labels):
        """
        Constructs a ConfusionMatrix object from two lists of labels.
        Requires a mapping from original labels to new labels in a way that new
        labels are ordered from 0 to k-1, for k classes

        @param labels: true labels (gold-standard)
        @type labels: sequence
        @param predictions: predicted labels
        @type predictions: sequence
        @param mapping: mapping of original to new labels
        @type mapping: dict

        @return: ConfusionMatrix
        """
        return cls.from_pairs(zip(labels, predictions), class_labels)
