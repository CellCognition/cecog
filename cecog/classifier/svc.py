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


__all__ = ("SupportVectorClassifier", )


import sys
from os.path import join
from os.path import isfile
from os.path import dirname
from os.path import splitext
from os.path import basename
from multiprocessing import cpu_count
import mimetypes

import h5py
import numpy as np

from sklearn import svm
from sklearn.metrics import confusion_matrix
from sklearn.grid_search import GridSearchCV
from sklearn.cross_validation import StratifiedKFold

from .writer import SVCWriter
from .writer import SVCDataModel
from .preprocessor import ZScore2
from .preprocessor import PreProcessor
from .confusion_matrix import ConfusionMatrix
from .classdefinition import ClassDefinition


def njobs():
    if hasattr(sys, 'frozen'):
        return 1
    else:
        return cpu_count() - 1


class SupportVectorClassifier(object):

    SaveProbs = True
    Method = "support vector classifier"
    Library = "sklearn.svm.SVC"

    def __init__(self, file_, name=None, channels=None,
                 color_channel=None, load=False, mode="r"):
        super(SupportVectorClassifier, self).__init__()

        self._h5f = None
        self.name = name
        self.color_channel = color_channel
        self.channels = channels
        self.samples = list()
        self.dmodel = None

        # XXX leagacy - remove class_definition.txt from pipeline
        if mimetypes.guess_type(file_)[0] == "application/x-hdf":
            self.annotations_dir = join(dirname(file_), "annotations")
            self._from_hdf(file_, mode, load)
            self._file = file_
        else:
            self.annotations_dir = join(file_, "annotations")
            self._file = join(file_, basename(file_)+'.hdf')
            file_ = join(file_, ClassDefinition.Definition)
            self.classdef = ClassDefinition(np.recfromtxt(file_, comments=None))

    def _from_hdf(self, file_, mode, load):

        self._h5f = h5py.File(file_, mode)
        if self.name is None:
            self.name = basename(splitext(file_)[0])

        self.dmodel = SVCDataModel(self.name)
        self.classdef = ClassDefinition(self._h5f[self.dmodel.classdef].value)

        if load:
            self.load()
        else:
            self._pp = None
            self._clf = None
            self._fnames = None

    def exists(self):
        return isfile(str(self._file))

    @property
    def class_names(self):
        return self.classdef.names

    # rename to class_colors or just colors
    @property
    def hexcolors(self):
        return self.classdef.colors

    # XXX rename to masks
    @property
    def regions(self):
        if len(self.channels) == 1:
            return self.channels.values()[0]
        else:
            return self.channels.values()

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

    def sample_data(self):

        nsamples = len(self.samples)
        nfeatures = self.samples[0].aFeatures.size

        labels = np.empty(nsamples, dtype=int)
        features = np.empty((nsamples, nfeatures), dtype=float)

        for i, sample in enumerate(self.samples):
            labels[i] = sample.iLabel
            features[i] = sample.aFeatures

        return features, labels

    def save(self, name=None):

        features, labels = self.sample_data()
        pp = PreProcessor(features)
        confmat, est = self.grid_search(pp(features), labels)

        if name is None:
            name = basename(splitext(self._file)[0])

        # probability estimate needs to be enabled
        params = est.get_params()
        params["probability"] = True

        writer = SVCWriter(name, self._file)
        writer.saveTrainingSet(features, self.feature_names)
        writer.saveAnnotations(labels)
        writer.saveClassDef(self.classdef, params)
        writer.saveNormalization(pp)
        writer.saveConfusionMatrix(confmat)
#        writer.saveSampleInfo(sample_info)
        writer.close()

    def add_samples(self, samples):
        # overwrite feature_names  each time, who cares
        self._fnames = samples.feature_names
        self.samples.extend(samples.values())


    def load(self):
        norm = self.normalization
        self._pp = ZScore2(norm['offset'], norm['scale'], norm['colmask'])
        self._clf = svm.SVC(**self.params)
        tdata = self.training_data
        self._clf.fit(self._pp(tdata.view(np.float32)), self.annotations)
        self._fnames = tdata.dtype.names

    def close(self):
        self._h5f.close()

    @property
    def confmat(self):
        cm = ConfusionMatrix(self._h5f[self.dmodel.confmatrix].value)
        return cm

    @property
    def feature_names(self):

        if self._fnames is None:
            self._fnames = self._h5f[self.dmodel.training_set].dtype.names

        return self._fnames

    @property
    def training_data(self):
        return self._h5f[self.dmodel.training_set].value

    @property
    def annotations(self):
        return self._h5f[self.dmodel.annotations].value

    @property
    def normalization(self):
        return self._h5f[self.dmodel.normalization].value

    @property
    def feature_mask(self):
        return self._h5f[self.dmodel.normalization]["colmask"]

    @property
    def hyper_params(self):
        attrs =  self.params
        return attrs["C"], attrs["gamma"]

    @property
    def params(self):

        params = dict(self._h5f[self.dmodel.classdef].attrs)
        for k, v in params.items():
            if v == "None":
                params[k] = None
        return params

    @property
    def class_counts(self):
        counts = dict()
        ant = self._h5f[self.dmodel.annotations].value
        for l in self.classdef.labels.values():
            counts[l] = ant[ant==l].size

        return counts

    def predict(self, features):

        features = self._pp(features)
        proba = self._clf.predict_proba(features)

        labels = [self.classdef.names.keys()[i] for i in np.argmax(proba, axis=1)]
        probs = list()
        for prob in proba:
            probs.append(dict((l, p) for l, p in zip(self.classdef.names.keys(), prob)))

        return labels, probs
