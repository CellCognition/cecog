"""
writer.py

  Save a sklearn based support vector classifier to a hdf file.

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("SVCWriter", )


import h5py
import sklearn
import numpy as np

class SVCDataModel(object):
    """Data model to save a Support Vector classifier to hdf5.

    It defines attribute names, group names (paths) and constants.
    """

    # constants, strings strings should be the import path of
    # corresponding module
    OneClassSvm = "sklearn.svm.OneClassSvm"
    SupportVectorClassifier = "sklearn.svm.SVC"

    # attribute keys
    NAME = "name"
    LIB = "library"
    VERSION = "version"
    FEATURE_SELECTION = "feature_selection"
    DESCRIPTION = "description"

    CLASSIFIER_ROOT = "/classifiers"

    def __init__(self, name):
        self.name = name
        self.path = "%s/%s" %(self.CLASSIFIER_ROOT, name)
        self.parameters = "%s/parameters" %self.path
        self.training_set = "%s/training_set" %self.path
        self.classdef = "%s/class_definition" %self.path
        self.normalization = "%s/normalization" %self.path
        self.sample_info = "%s/sample_info" %self.path

        self.annotations = "%s/annotations" %self.path
        self.confmatrix = "%s/confusion_matrix" %self.path


class SVCWriter(object):

    # h5py file modes
    READWRITE = "r+"
    READONLY = "r"
    WRITE = "w"
    WRITEFAIL = "w-"
    READWRITECREATE = "a"

    def __init__(self, name, file_, compression="gzip", compression_opts=4,
                 description=None, remove_existing=False):
        assert isinstance(remove_existing, bool)

        self._compression = compression
        self._copts = compression_opts

        self.h5f = h5py.File(file_, self.WRITE)
        self.dmodel = SVCDataModel(name)

        if remove_existing:
            try:
                del self.h5f[self.dmodel.path]
            except KeyError:
                pass

        try:
            grp = self.h5f.create_group(self.dmodel.path)
        except ValueError as e:
            raise IOError("Classifer with name '%s' exists already" %name)

        grp.attrs[self.dmodel.NAME] = name
        grp.attrs[self.dmodel.LIB] = self.dmodel.SupportVectorClassifier
        grp.attrs[self.dmodel.VERSION] = sklearn.__version__

        if description is not None:
            grp.attrs[self.dmodel.DESCRIPTION] = description

    def flush(self):
        self.h5f.flush()

    def close(self):
        self.h5f.close()

    def saveTrainingSet(self, features, feature_names):
        dtype = [(str(fn), np.float32) for fn in feature_names]
        f2 = features.copy().astype(np.float32).view(dtype)
        dset = self.h5f.create_dataset(self.dmodel.training_set,
                                       data=f2,
                                       compression=self._compression,
                                       compression_opts=self._copts)

    def saveClassDef(self, classes, classifier_params=None):

        dt = [("name", "S64"), ("label", int), ("color", "S7")]
        classdef = np.empty(len(classes, ), dtype=dt)

        for i, class_  in enumerate(classes):
            classdef[i] = class_

        dset = self.h5f.create_dataset(self.dmodel.classdef,
                                       data=classdef,
                                       compression=self._compression,
                                       compression_opts=self._copts)

        if classifier_params is not None:
            # save classifier parameters
            for k, v in classifier_params.iteritems():
                if v is None:
                    dset.attrs[k] = str(v)
                else:
                    dset.attrs[k] = v

    def saveNormalization(self, preproc):

        dt = [("offset", np.float32), ("scale", np.float32), ("colmask", bool)]
        offset = preproc.mean.astype(np.float32)
        scale = preproc.std.astype(np.float32)
        norm = np.empty( (offset.size, ), dtype=dt)

        for i, line in enumerate(zip(offset, scale, preproc.mask)):
            norm[i] = line

        dset = self.h5f.create_dataset(self.dmodel.normalization, data=norm,
                                       compression=self._compression,
                                       compression_opts=self._copts)

    def saveSampleInfo(self, sample_info):

        dset = self.h5f.create_dataset(
            self.dmodel.sample_info, data=sample_info,
            compression=self._compression, compression_opts=self._copts)


    def saveAnnotations(self, labels):
        # max 256 classes!
        labels = labels.astype(np.uint8)
        dset = self.h5f.create_dataset(self.dmodel.annotations,
                                       data=labels,
                                       compression=self._compression,
                                       compression_opts=self._copts)

    def saveConfusionMatrix(self, confmat):
        dset = self.h5f.create_dataset(self.dmodel.confmatrix,
                                       data=confmat,
                                       compression=self._compression,
                                       compression_opts=self._copts)
