"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

import os
import csv

from os.path import join, isdir, splitext, isfile
from collections import OrderedDict

from matplotlib.colors import ListedColormap, rgb2hex
from matplotlib import mpl

import numpy as np
import svm

from cecog.colors import unsupervised_cmap
from cecog.learning.confusion_matrix import ConfusionMatrix
from cecog.learning.util import SparseWriter, ArffWriter, ArffReader
from cecog.learning.classifier import LibSvmClassifier as Classifier
from cecog.util.logger import LoggerObject
from cecog.util.util import makedirs
from cecog.learning.classifier import GaussianMixtureModel

class LearnerFiles(object):
    # to collect the file names at one place
    ARFF = 'features.arff'
    SPARSE ='features.sparse'
    DEFINITION = 'class_definition.txt'


class ClassDefinitionCore(object):

    def __init__(self, *args, **kw):
        self.feature_names = None
        self.hexcolors = dict()
        self.class_labels = dict()
        self.class_names = OrderedDict()

    @property
    def n_classes(self):
        return len(self.class_names)

    @property
    def normalize(self):
        """Return a matplotlib normalization instance to the class lables
        corretly mapped to the colors"""
        return mpl.colors.Normalize(vmin=0,
                                    vmax=max(self.class_names.keys()))


class ClassDefinitionUnsup(ClassDefinitionCore):
    """Unsupervised class definition has hard wired class labels and
    a destinct colormap to make it easy distinguishable from user defined
    class definitions.
    """

    SAVE_PROBS = False

    def __init__(self, nclusters, *args, **kw):
        super(ClassDefinitionUnsup, self).__init__(*args, **kw)
        self.nclusters = nclusters
        self.colormap = unsupervised_cmap(self.nclusters)
        # dummy attribute to recyle export function in timeholder
        self.classifier = GaussianMixtureModel()

        for i in xrange(self.nclusters):
            name = "cluster-%d" %i
            self.class_labels[name] = i
            self.class_names[i] = name
            self.hexcolors[name] = rgb2hex(self.colormap(i))


class ClassDefinition(ClassDefinitionCore):
    """Class definition based on a recarray return from a ch5 file"""

    def __init__(self, classes, *args, **kw):
        super(ClassDefinition, self).__init__(*args, **kw)
        for (label, name, color) in classes:
            self.class_labels[name] = label
            self.class_names[label] = name
            self.hexcolors[name] = color

        colors = ["#ffffff"]*(max(self.class_names)+1)
        for k, v in self.class_names.iteritems():
            colors[k] = self.hexcolors[v]
        self.colormap = ListedColormap(colors, 'cmap-from-table')


class BaseLearner(LoggerObject):

    XML = "xml"
    SAVE_PROBS = True

    # directory substructure
    _subdirs = ('annotations', 'data', 'samples', 'controls')

    def __init__(self, clf_dir, name, channels, color_channel=None,
                 has_zero_insert=False):
        super(BaseLearner, self).__init__()
        self.add_stream_handler(self._lvl.INFO)
        self._clf_dir = None

        if clf_dir is not None:
            if not os.path.isdir(clf_dir):
                raise IOError("Classifier path '%s' does not exist." %clf_dir)
            self.clf_dir = clf_dir

        self.name = name
        self.color_channel = color_channel
        self.channels = channels

        self.arff_file = LearnerFiles.ARFF
        self.sparse_file = LearnerFiles.SPARSE
        self.definitions_file = LearnerFiles.DEFINITION
        self._feature_names = None

        self._class_definitions = []
        self.feature_data = OrderedDict()
        self.class_names = OrderedDict()
        self.class_labels = {}
        self.has_zero_insert = has_zero_insert
        self.hexcolors = {}
        self.sample_names = {}

    @property
    def regions(self):
        if len(self.channels) == 1:
            return self.channels.values()[0]
        else:
            return self.channels.values()

    @property
    def feature_names(self):
        return self._feature_names

    @feature_names.setter
    def feature_names(self, feature_names):
        self._feature_names = feature_names
        #assert self._feature_names == feature_names

    def delete_feature_names(self, indices):
        """Remove feature names given a list of indices."""
        features = np.asarray(self._feature_names)
        self._feature_names = np.delete(features, indices).tolist()

        self.logger.info(("Following features evaluated to NaN"
                         "and have been removed: %s" %str(features[indices])))
        return features[indices]

    @property
    def clf_dir(self):
        return self._clf_dir

    @clf_dir.deleter
    def clf_dir(self):
        del self._clf_dir

    @clf_dir.setter
    def clf_dir(self, path):

        if not isdir(path):
            raise IOError("Path to classifier '%s' does not exist." %path)

        self._clf_dir = path
        for dir_ in self._subdirs:
            subdir = join(path, dir_)
            setattr(self, "%s_dir" %dir_, subdir)
            makedirs(subdir)

    # kind of a workaround for loading class definitons
    def unset_clf_dir(self):
        self._clf_dir = None

    @property
    def n_classes(self):
        return len(self.class_names)

    def clear(self):
        self.dctFeatureData.clear()
        self.class_names.clear()
        self.class_labels.clear()
        self.feature_names = []
        self.hexcolors.clear()
        self.sample_names.clear()

    @property
    def names2samples(self):
        return dict([(n, len(self.feature_data.get(n, [])))
                     for n in self.class_names.values()])

    def loadDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.definitions_file
        if path is None:
            path = self.clf_dir

        with open(join(path, filename), "rb") as f:
            reader = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            self.class_names.clear()
            self.class_labels.clear()
            self.hexcolors.clear()
            for row in reader:
                label = int(row[0])
                name = row[1]
                color = row[2]
                self.class_names[label] = name
                self.class_labels[name] = label
                self.hexcolors[name] = color

    def saveDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.definitions_file
        if path is None:
            path = self.clf_dir
        with open(join(path, filename), "wb") as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            for class_name in self.class_names.values():
                class_label = self.class_labels[class_name]
                color = self.hexcolors[class_name]
                writer.writerow([class_label, class_name, color])

    def exportRanges(self, path=None, fname=None):
        if fname is None:
            fname = splitext(self.arff_file)[0] + '.range'
        if path is None:
            path = self.data_dir

        all_features = np.vstack(self.feature_data.values())
        features_min = np.min(all_features, 0)
        features_max = np.max(all_features, 0)

        with open(join(path, fname), 'w') as fp:
            fp.write('x\n')
            fp.write('-1 1\n')
            for idx, (m1, m2) in enumerate(zip(features_min, features_max)):
                fp.write('%d %.10e %.10e\n' % (idx+1, m1, m2))


    def importFromArff(self, path=None, filename=None):
        if filename is None:
            filename = self.arff_file
        if path is None:
            path = self.data_dir

        oReader = ArffReader(join(path, filename))
        self.feature_data = oReader.dctFeatureData
        self.class_names.update(oReader.dctClassNames)
        self.class_labels.update(oReader.dctClassLabels)
        self.feature_names = oReader.lstFeatureNames
        self.hexcolors = oReader.dctHexColors
        self.has_zero_insert = oReader.hasZeroInsert

    def check(self):
        filename = splitext(self.arff_file)[0]
        result = {'path_env': self.clf_dir,
                  'path_data': self.data_dir,
                  'path_samples': self.samples_dir,
                  'path_annotations': self.annotations_dir,
                  'model': join(self.data_dir, '%s.model' %filename),
                  'range': join(self.data_dir, '%s.range' %filename),
                  'conf': join(self.data_dir, '%s.confusion.txt' %filename),
                  'arff': join(self.data_dir, self.arff_file),
                  'definition': join(self.clf_dir, self.definitions_file),
                  # result of validity checks
                  'has_path_data': isdir(self.data_dir),
                  'has_path_samples': isdir(self.data_dir),
                  'has_path_annotations': isdir(self.data_dir),
                  'has_model': isfile(join(self.data_dir, '%s.model' %filename)),
                  'has_range': isfile(join(self.data_dir, '%s.range' %filename)),
                  'has_conf': isfile(join(self.data_dir, '%s.confusion.txt' %filename)),
                  'has_arff': isfile(join(self.data_dir, self.arff_file)),
                  'has_definition': isfile(join(self.clf_dir, self.definitions_file))}
        return result

    def exportToArff(self, path=None, filename=None):
        if filename is None:
            filename = self.arff_file
        if path is None:
            path = self.data_dir

        writer = ArffWriter(join(path, filename),
                            self._feature_names,
                            self.class_labels,
                            dctHexColors=self.hexcolors,
                            hasZeroInsert=self.has_zero_insert)
        writer.writeAllFeatureData(self.feature_data)
        writer.close()

    def exportToSparse(self, directory=None, filename=None):
        if filename is None:
            filename = self.sparse_file
        if directory is None:
            directory = self.data_dir

        try:
            writer = SparseWriter(join(directory, filename),
                                  self._feature_names,
                                  self.class_labels)
            writer.writeAllFeatureData(self.feature_data)
        finally:
            writer.close()

    def importSampleNames(self, path=None, filename=None):
        if strFileName is None:
            strFileName = os.path.splitext(self.arff_file)[0]
            strFileName = '%s.samples.txt' % strFileName
        if strFilePath is None:
            strFilePath = self.data_dir
        f = file(os.path.join(strFilePath, strFileName), 'r')
        self.sample_names = {}
        for line in f:
            class_name, file_name = line.strip().split('\t')
            if class_name in self.class_labels:
                if not class_name in self.sample_names:
                    self.sample_names[class_name] = []
            self.sample_names[class_name].append(file_name)
        f.close()

    def exportSampleNames(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = splitext(self.arff_file)[0]
            strFileName = '%s.samples.txt' % strFileName
        if strFilePath is None:
            strFilePath = self.data_dir
        f = file(os.path.join(strFilePath, strFileName), 'w')
        for class_name, samples in self.sample_names.iteritems():
            for sample_name in samples:
                f.write('%s\t%s\n' % (class_name, sample_name))
        f.close()

    def export(self):
        self.exportToArff()
        self.exportToSparse()
        self.exportSampleNames()


class CommonClassPredictor(BaseLearner):

    def __init__(self, *args, **kw):
        super(CommonClassPredictor, self).__init__(*args, **kw)
        self.strModelPrefix = "features"
        self.classifier = None
        self.nan_features = []

    def has_nan_features(self):
        for data in self.feature_data.itervalues():
            if np.any(np.isnan(data)):
                return True
        return False

    def loadClassifier(self, model_prefix="features"):
        self.classifier = Classifier(self.data_dir,
                                     svm_prefix=model_prefix,
                                     has_zero_insert=self.has_zero_insert)
        self.bProbability = self.classifier.probability

    def predict(self, aFeatureData, feature_names):
        # ensurse to get the right fearues in the right order
        # FIX what if NaN's are in in feature data
        dctNameLookup = dict([(name,i) for i,name in enumerate(feature_names)])
        lstRequiredFeatureData = [aFeatureData[dctNameLookup[x]]
                                  for x in self._feature_names]
        return self.classifier(lstRequiredFeatureData)

    def getData(self, normalize=True):
        labels = []
        samples = []
        for name, data in self.feature_data.iteritems():
            label = self.class_labels[name]
            labels += [label] * len(data)
            samples += data.tolist()
        labels = np.asarray(labels)
        samples = np.asarray(samples)
        if normalize:
            lo = np.min(samples, 0)
            hi = np.max(samples, 0)
            # scale between -1 and +1
            samples = 2.0 * (samples - lo) / (hi - lo + 0.0000001) - 1.0
        # FIXME: stupid libSVM conversions
        labels = map(int, labels)
        samples = samples.tolist()
        return labels, samples

    def filter_nans(self, apply=False):
        """Find features with NA values in the data set and remove features
        from the data and corresponding feature names returns the list of
        removed feature names.
        """

        filter_idx = np.array([], int)
        feature_idx = np.arange(len(self._feature_names), dtype=int)

        for data in self.feature_data.itervalues():
            filter_idx = np.append(filter_idx, feature_idx[np.any(np.isnan(data), 0)])
        filter_idx = np.unique(filter_idx)

        if apply:
            for name in self.feature_data:
                self.feature_data[name] = np.delete(self.feature_data[name],
                                                      filter_idx, 1)
            if filter_idx.size > 0:
                self.nan_features = self.delete_feature_names(filter_idx)
        return self.nan_features

    def train(self, c, g, probability=True, compensation=True,
              path=None, filename=None, save=True):
        if filename is None:
            filename = splitext(self.arff_file)[0]
            filename += '.model'
        if path is None:
            path = self.data_dir
        param = svm.svm_parameter(kernel_type=svm.RBF,
                                  C=c, gamma=g,
                                  probability=1 if probability else 0)

        labels, samples = self.getData(normalize=True)

        # because we train the SVM with dict we need to redefine the zero-insert
        self.has_zero_insert = False
        if not self.classifier is None:
            self.classifier.setOption('hasZeroInsert', True)

        if compensation:
            weight, weight_label = self._calculateCompensation(labels)
            param.weight = weight
            param.weight_label = weight_label
            param.nr_weight = len(weight)

        problem = svm.svm_problem(labels, samples)
        model = svm.svm_model(problem, param)
        if save:
            model.save(os.path.join(path, filename))
        return problem, model

    def exportConfusion(self, log2c, log2g, conf, path=None, filename=None):
        if filename is None:
            filename = splitext(self.arff_file)[0]
            filename += '.confusion.txt'
        if path is None:
            path = self.data_dir

        with open(join(path, filename), "w") as f:
            f.write('log2(C) = %f\n' % log2c)
            f.write('log2(g) = %f\n' % log2g)
            f.write('accuracy = %f\n' % conf.ac_sample)
            f.write('\n')
            f.write('confusion matrix (absolute)\n')
            f.write('\t%s\n' %'\t'.join([str(k) for k in self.class_names.keys()]))

            for label, row in zip(self.class_names.keys(), conf.conf):
                f.write( ('%d\t' %label) + '\t'.join(['%d' %i for i in row]))
                f.write('\n')

    def importConfusion(self, path=None, filename=None):
        if filename is None:
            filename = os.path.splitext(self.arff_file)[0]
            filename += '.confusion.txt'
        if path is None:
            path = self.data_dir

        with open(join(path, filename), "Ur") as f:
            log2c = float(f.readline().split('=')[1].strip())
            log2g = float(f.readline().split('=')[1].strip())
            f.readline()
            f.readline()
            f.readline()
            f.readline()
            conf_array = []
            for line in f:
                line = line.strip()
                if len(line) == 0:
                     break
                items = map(int, map(float, line.split('\t')[1:]))
                conf_array.append(items)
            conf = ConfusionMatrix(np.asarray(conf_array))
        return log2c, log2g, conf

    def _calculateCompensation(self, labels):
        ulabels = np.unique(labels)
        count = np.bincount(labels)[ulabels]
        weight = (float(len(labels)) - count) / count
        weight_label = map(int, ulabels)
        return weight, weight_label

    def gridSearch(self, fold=5, c_info=None, g_info=None,
                   probability=False, compensation=True):
        best_accuracy = 0
        best_l2c = None
        best_l2g = None
        best_conf = None
        n = None
        for n,l2c,l2g,conf in self.iterGridSearchSVM(c_info=c_info, g_info=g_info,
                                                     fold=fold,
                                                     probability=probability,
                                                     compensation=compensation):
            accuracy = conf.ac_sample
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_l2c = l2c
                best_l2g = l2g
                best_conf = conf
        return n, best_l2c, best_l2g, best_conf

    def iterGridSearchSVM(self, c_info=None, g_info=None, fold=5,
                          probability=False, compensation=True):
        swap = lambda a,b: (b,a)
        if not c_info is None and len(c_info) >= 3:
            c_begin, c_end, c_step = c_info[:3]
        else:
            c_begin, c_end, c_step = -5,  15, 2
        if c_end < c_begin:
            c_begin, c_end = swap(c_begin, c_end)
        c_step = abs(c_step)

        if not g_info is None and len(g_info) >= 3:
            g_begin, g_end, g_step = g_info[:3]
        else:
            g_begin, g_end, g_step = -15, 3, 2
        if g_end < g_begin:
            g_begin, g_end = swap(g_begin, g_end)
        g_step = abs(g_step)

        labels, samples = self.getData(normalize=True)
        problem = svm.svm_problem(labels, samples)

        if compensation:
            weight, weight_label = self._calculateCompensation(labels)

        n = (c_end - c_begin) / c_step + 1
        n *= (g_end - g_begin) / g_step + 1

        l2c = c_begin
        while l2c <= c_end:
            l2g = g_begin
            while l2g <= g_end:

                param = svm.svm_parameter(kernel_type=svm.RBF,
                                          C=2.**l2c, gamma=2.**l2g,
                                          probability=1 if probability else 0)
                if compensation:
                    param.weight = weight
                    param.weight_label = weight_label
                    param.nr_weight = len(weight)

                predictions = svm.cross_validation(problem, param, fold)
                predictions = map(int, predictions)

                conf = ConfusionMatrix.from_lists(labels, predictions,
                                                  self.class_names.keys())
                yield n, l2c, l2g, conf

                l2g += g_step
            l2c += c_step

class CommonObjectLearner(BaseLearner):

    def __init__(self, *args, **kw):
        super(CommonObjectLearner, self).__init__(*args, **kw)

    def set_training_data(self, training_set):
        self.feature_names = training_set.feature_names
        nfeatures = training_set.n_features

        for obj_label, sample in training_set.iteritems():
            class_name = self.class_names[sample.iLabel]

            if sample.aFeatures.size != nfeatures:
                msg = ('Incomplete feature set found (%d/%d): skipping sample '
                       'class: %s, object label %s, files: %s'
                       %(sample.aFeatures.size, nfeatures, class_name,
                         obj_label, str(sample.file)))
                self.logger.warning(msg)
                continue

            try:
                self.feature_data[class_name].extend([sample.aFeatures])
            except KeyError:
                self.feature_data[class_name] = [sample.aFeatures]
            try:
                self.sample_names[class_name].extend([sample.file])
            except KeyError:
                self.sample_names[class_name] = [sample.file]


if __name__ ==  "__main__":
    import sys
    if isdir(sys.argv[1]):
        learner = CommonClassPredictor(sys.argv[1])
        learner.importFromArff()
#        c, g, conf = learner.importConfusion()
    else:
        raise IOError("%s\n is not a valid directory" %sys.argv[1])
    #learner.statsFromConfusion(conf)
