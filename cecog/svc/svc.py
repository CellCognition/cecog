"""
svc.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("SVCTrainer", "SVCPredictor")

import sys
from os.path import basename, splitext, isfile, dirname, join
import numpy as np

import h5py
from sklearn import svm

from sklearn.metrics import confusion_matrix
from sklearn.grid_search import GridSearchCV
from sklearn.cross_validation import StratifiedKFold
from .preprocessor import PreProcessor
from .writer import SVCDataModel

from cecog.learning.learning import ClassDefinition
from cecog.learning.confusion_matrix import ConfusionMatrix
from .writer import SVCWriter

from multiprocessing import cpu_count


def njobs():
    if hasattr(sys, 'frozen'):
        return 1
    else:
        return cpu_count() - 1


class _SVC(object):

    def __init__(self, file_, name=None, channels=None, color_channel=None):

        super(_SVC, self).__init__()
        self._file = file_
        self.name = name
        self.color_channel = color_channel
        self.channels = channels
        self.annotations_dir = join(dirname(file_), "annotations")
        self.samples = list()

    def exists(self):
        return isfile(str(self._file))

    @property
    def class_names(self):
        return self.classdef.names

    @property
    def hexcolors(self):
        return self.classdef.colors

    @property
    def regions(self):
        if len(self.channels) == 1:
            return self.channels.values()[0]
        else:
            return self.channels.values()


class SVCTrainer(_SVC):

    def __init__(self, file_, *args, **kw):
        super(SVCTrainer, self).__init__(file_, *args, **kw)

        file_ = join(dirname(file_), ClassDefinition.Definition)
        self.classdef = ClassDefinition(np.recfromtxt(file_, comments=None))

    def grid_search(self, features, labels, kfold=5):

        C = np.logspace(-6, 6, 10)
        gamma = np.logspace(-6, 6, 10)
        param_grid = dict(gamma=gamma, C=C)

        cv = StratifiedKFold(y=labels, n_folds=kfold)
        grid = GridSearchCV(svm.SVC(), param_grid=param_grid, cv=cv,
                            n_jobs=njobs())

        if np.isnan(features).any():
            raise RuntimeError("There is a NAN in the feature table. "
                               "I can't proceed, sorry... "
                               "Rerun preprocessing and remove weird cells")

        grid.fit(features, labels)
        est = grid.best_estimator_

        predictions = est.predict(features)
        confmat = confusion_matrix(labels, predictions)

        return confmat, est

    def training_data(self):

        nsamples = len(self.samples)
        nfeatures = self.samples[0].aFeatures.size

        labels = np.empty(nsamples, dtype=int)
        features = np.empty((nsamples, nfeatures), dtype=float)

        for i, sample in enumerate(self.samples):
            labels[i] = sample.iLabel
            features[i] = sample.aFeatures

        return features, labels

    def save(self, name=None):

        features, labels = self.training_data()
        pp = PreProcessor(features)
        confmat, est = self.grid_search(pp(features), labels)

        if name is None:
            name = basename(splitext(self._file)[0])

        writer = SVCWriter(name, self._file)
        writer.saveTrainingSet(pp(features), self.feature_names)
        writer.saveAnnotations(labels)
        writer.saveClassDef(self.classdef, est.get_params())
        writer.saveNormalization(pp)
        writer.saveConfusionMatrix(confmat)
#        writer.saveSampleInfo(sample_info)
        writer.close()

    def add_samples(self, samples):
        # overwrite each time, who cares!
        self.feature_names = samples.feature_names
        self.samples.extend(samples.values())



class SVCPredictor(_SVC):

    def __init__(self, file_, name=None, *args, **kw):
        super(SVCPredictor, self).__init__(file_, name, *args, **kw)
        self._h5f = h5py.File(file_, "r")

        if self.name is None:
            self.name = basename(splitext(file_)[0])

        self.dmodel = SVCDataModel(self.name)
        self.classdef = ClassDefinition(self._h5f[self.dmodel.classdef].value)

    def close(self):
        self._h5f.close()

    @property
    def confmat(self):
        cm = ConfusionMatrix(self._h5f[self.dmodel.confmatrix].value)
        return cm

    @property
    def feature_names(self):
        return self._h5f[self.dmodel.training_set].dtype.names

    @property
    def normalization(self):
        return self._h5f[self.dmodel.normalization]

    @property
    def feature_mask(self):
        return self._h5f[self.dmodel.normalization]["colmask"]

    @property
    def hyper_params(self):
        attrs =  self._h5f[self.dmodel.classdef].attrs
        return attrs["C"], attrs["gamma"]

    @property
    def class_counts(self):
        counts = dict()
        ant = self._h5f[self.dmodel.annotations].value
        for l in self.classdef.labels.values():
            counts[l] = ant[ant==l].size

        return counts
