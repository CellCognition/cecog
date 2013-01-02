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
import copy

from os.path import join, isdir, splitext, isfile, basename
from collections import OrderedDict

import numpy as np
import svm

from cecog.learning.confusion_matrix import ConfusionMatrix
from cecog.learning.util import SparseWriter, ArffWriter, ArffReader
from cecog.learning.classifier import LibSvmClassifier as Classifier
from cecog.util.util import rgbToHex
from cecog.util.logger import LoggerObject
from cecog.util.util import makedirs

class BaseLearner(LoggerObject):

    # directory substructure
    ANNOTATIONS = 'annotations'
    DATA = 'data'
    SAMPLES = 'samples'
    CONTROLS = 'controls'

    def __init__(self, clf_dir, color_channel, region,
                 prcs_channel=None):
        super(BaseLearner, self).__init__()
        self._cld_dir = None

        self.color_channel = color_channel
        self.prcs_channel = prcs_channel

        self.clf_dir = clf_dir
        self.region = region

        self.strArffFileName = 'features.arff'
        self.strSparseFileName ='features.sparse'
        self.strDefinitionFileName = 'class_definition.txt'
#        self.filename_pickle = 'learner.pkl'
        self.lstFeatureNames = None

        self._class_definitions = []

        self.dctImageObjects = OrderedDict()
        self.dctFeatureData = OrderedDict()
        self.dctClassNames = {}
        self.dctClassLabels = {}
        self.dctHexColors = {}
        self.dctSampleNames = {}

        if clf_dir is not None:
            self.name = basename(clf_dir)
            self.makedirs()

    @property
    def clf_dir(self):
        return self._clf_dir

    @clf_dir.deleter
    def clf_dir(self):
        del self._clf_dir

    @clf_dir.setter
    def clf_dir(self, path):
        if path is None:
            return
        self._clf_dir = path
        self._subdirs = {self.SAMPLES: join(path, "samples"),
                         self.ANNOTATIONS : join(path, self.ANNOTATIONS),
                         self.DATA: join(path, "data"),
                         self.CONTROLS: join(path, "controls")}

    @property
    def lstClassDefinitions(self):
        return self._class_definitions

    @lstClassDefinitions.deleter
    def lstClassDefinitions(self):
        del self._class_definitions

    @lstClassDefinitions.setter
    def lstClassDefinitions(self, definitions):
        for class_description in definitions:
            name = class_description['name']
            label = class_description['label']
            color = class_description['color']

            # FIXME: folders not supported yet!
            # what is it good for?
            try:
                folders = class_description["folders"]
            except KeyError:
                folders = [name]

            # and what is this good for
            self.dctClassNames[label] = name
            self.dctClassLabels[name] = label
            self.dctHexColors[name] = rgbToHex(*color)

    def clear(self):
        self.dctFeatureData.clear()
        self.dctClassNames.clear()
        self.dctClassLabels.clear()
        self.lstFeatureNames = None
        self.dctHexColors.clear()
        self.dctSampleNames.clear()
        self.dctImageObjects.clear()

    def mergeClasses(self, info, mapping):
        newl = copy.deepcopy(self)

        newl.dctClassNames = {}
        newl.dctClassLabels = {}
        newl.dctHexColors = {}
        for label, name, color in info:
            newl.dctClassNames[label] = name
            newl.dctClassLabels[name] = label
            newl.dctHexColors[name] = color
        data = OrderedDict()
        for new_label, label_list in mapping.iteritems():
            new_name = newl.dctClassNames[new_label]
            if not new_name in data:
                data[new_name] = []
            for old_label in label_list:
                old_name = self.dctClassNames[old_label]
                data[new_name].extend(self.dctFeatureData[old_name])
        for name in data:
            data[name] = np.asarray(data[name])
        newl.dctFeatureData = data
        return newl

    @property
    def lstClassNames(self):
        return [self.dctClassNames[x] for x in self.lstClassLabels]

    @property
    def lstClassLabels(self):
        return sorted(self.dctClassNames.keys())

    @property
    def iClassNumber(self):
        return len(self.dctClassNames)

    @property
    def lstHexColors(self):
        return [self.dctHexColors[x] for x in self.lstClassNames]

    @property
    def names2samples(self):
        return dict([(n, len(self.dctFeatureData.get(n, [])))
                     for n in self.lstClassNames])

    @property
    def l2nl(self):
        """Converts a label into a new label
        (new labels are continuous from 0..number of classes
        """
        return dict([(l,i) for i,l in enumerate(self.lstClassLabels)])

    @property
    def nl2l(self):
        """Converts a new label into the original label"""
        return dict([(i,l) for i,l in enumerate(self.lstClassLabels)])

    def makedirs(self):
        env_path = self.clf_dir
        if not isdir(env_path):
            raise IOError(("Classifier environment path '%s' does not exist." \
                           %env_path))
        for name, path in self._subdirs.iteritems():
            setattr(self, "%s_dir" %name, path)
            makedirs(path)

    # XXX replace subdir function
    def subdir(self, directory):
        return self._subdirs[directory]

    def loadDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.strDefinitionFileName
        if path is None:
            path = self.clf_dir

        with open(join(path, filename), "rb") as f:
            reader = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            self.dctClassNames.clear()
            self.dctClassLabels.clear()
            self.dctHexColors.clear()
            for row in reader:
                label = int(row[0])
                name = row[1]
                color = row[2]
                self.dctClassNames[label] = name
                self.dctClassLabels[name] = label
                self.dctHexColors[name] = color

    def saveDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.strDefinitionFileName
        if path is None:
            path = self.clf_dir
        with open(join(path, filename), "wb") as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            for class_name in self.lstClassNames:
                class_label = self.dctClassLabels[class_name]
                color = self.dctHexColors[class_name]
                writer.writerow([class_label, class_name, color])

    def exportRanges(self, path=None, fname=None):
        if fname is None:
            fname = splitext(self.strArffFileName)[0] + '.range'
        if path is None:
            path = self._subdirs['data']

        all_features = np.vstack(self.dctFeatureData.values())
        features_min = np.min(all_features, 0)
        features_max = np.max(all_features, 0)

        with open(join(path, fname), 'w') as fp:
            fp.write('x\n')
            fp.write('-1 1\n')
            for idx, (m1, m2) in enumerate(zip(features_min, features_max)):
                fp.write('%d %.10e %.10e\n' % (idx+1, m1, m2))


    def importFromArff(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.strArffFileName
        if strFilePath is None:
            strFilePath = self._subdirs['data']

        oReader = ArffReader(os.path.join(strFilePath, strFileName))
        self.dctFeatureData = oReader.dctFeatureData
        self.dctClassNames = oReader.dctClassNames
        self.dctClassLabels = oReader.dctClassLabels
        self.lstFeatureNames = oReader.lstFeatureNames
        self.dctHexColors = oReader.dctHexColors
        self.hasZeroInsert = oReader.hasZeroInsert

    def check(self):
        filename = splitext(self.strArffFileName)[0]
        result = {'path_env': self.clf_dir,
                  'path_data': self._subdirs['data'],
                  'path_samples': self._subdirs['samples'],
                  'path_annotations': self._subdirs['annotations'],
                  'model': join(self._subdirs['data'], '%s.model' %filename),
                  'range': join(self._subdirs['data'], '%s.range' %filename),
                  'conf': join(self._subdirs['data'], '%s.confusion.txt' %filename),
                  'arff': join(self._subdirs['data'], self.strArffFileName),
                  'definition': join(self.clf_dir, self.strDefinitionFileName),
                  # result of validity checks
                  'has_path_data': isdir(self._subdirs['data']),
                  'has_path_samples': isdir(self._subdirs['samples']),
                  'has_path_annotations': isdir(self._subdirs['annotations']),
                  'has_model': isfile(join(self._subdirs['data'], '%s.model' % filename)),
                  'has_range': isfile(join(self._subdirs['data'], '%s.range' % filename)),
                  'has_conf': isfile(join(self._subdirs['data'], '%s.confusion.txt' % filename)),
                  'has_arff': isfile(join(self._subdirs['data'], self.strArffFileName)),
                  'has_definition': isfile(join(self.clf_dir, self.strDefinitionFileName))}
        return result

    def exportToArff(self, path=None, filename=None):
        if filename is None:
            filename = self.strArffFileName
        if path is None:
            path = self._subdirs['data']

        writer = ArffWriter(join(path, filename),
                            self.lstFeatureNames,
                            self.dctClassLabels,
                            dctHexColors=self.dctHexColors,
                            hasZeroInsert=self.hasZeroInsert)
        writer.writeAllFeatureData(self.dctFeatureData)
        writer.close()

    def exportToSparse(self, directory=None, filename=None):
        if filename is None:
            filename = self.strSparseFileName
        if directory is None:
            directory = self._subdirs['data']

        try:
            writer = SparseWriter(join(directory, filename),
                                  self.lstFeatureNames,
                                  self.dctClassLabels)
            writer.writeAllFeatureData(self.dctFeatureData)
        finally:
            writer.close()

    def importSampleNames(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = os.path.splitext(self.strArffFileName)[0]
            strFileName = '%s.samples.txt' % strFileName
        if strFilePath is None:
            strFilePath = self._subdirs['data']
        f = file(os.path.join(strFilePath, strFileName), 'r')
        self.dctSampleNames = {}
        for line in f:
            class_name, file_name = line.strip().split('\t')
            if class_name in self.dctClassLabels:
                if not class_name in self.dctSampleNames:
                    self.dctSampleNames[class_name] = []
            self.dctSampleNames[class_name].append(file_name)
        f.close()

    def exportSampleNames(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = splitext(self.strArffFileName)[0]
            strFileName = '%s.samples.txt' % strFileName
        if strFilePath is None:
            strFilePath = self._subdirs['data']
        f = file(os.path.join(strFilePath, strFileName), 'w')
        for class_name, samples in self.dctSampleNames.iteritems():
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

    def loadClassifier(self):
        if self.strModelPrefix is None:
            strModelPrefix = splitext(self.strSparseFileName)[0]
        else:
            strModelPrefix = self.strModelPrefix


        self.classifier = Classifier(self._subdirs['data'], self.logger,
                                     strSvmPrefix=strModelPrefix,
                                     hasZeroInsert=self.hasZeroInsert)
        self.bProbability = self.classifier.bProbability

    def predict(self, aFeatureData, lstFeatureNames):
        dctNameLookup = dict([(name,i) for i,name in enumerate(lstFeatureNames)])
        lstRequiredFeatureData = [aFeatureData[dctNameLookup[x]]
                                  for x in self.lstFeatureNames]
        return self.classifier(lstRequiredFeatureData)

    def getData(self, normalize=True):
        labels = []
        samples = []
        for name, data in self.dctFeatureData.iteritems():
            label = self.dctClassLabels[name]
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

    def filterData(self, apply=False):
        """
        find features with NA values in the data set and remove features from the data and corresponding feature names
        returns the list of removed feature names
        """
        filter_idx = np.array([], np.int32)
        features = np.asarray(self.lstFeatureNames)
        feature_idx = np.arange(len(features))
        for data in self.dctFeatureData.itervalues():
            filter_idx = np.append(filter_idx, feature_idx[np.any(np.isnan(data), 0)])
        filter_idx = np.unique(filter_idx)
        if apply:
            for name in self.dctFeatureData:
                self.dctFeatureData[name] = np.delete(self.dctFeatureData[name], filter_idx, 1)
            self.lstFeatureNames = np.delete(features, filter_idx).tolist()
        return features[filter_idx]

    def train(self, c, g, probability=True, compensation=True,
              path=None, filename=None, save=True):
        if filename is None:
            filename = splitext(self.strArffFileName)[0]
            filename += '.model'
        if path is None:
            path = self._subdirs['data']
        param = svm.svm_parameter(kernel_type=svm.RBF,
                                  C=c, gamma=g,
                                  probability=1 if probability else 0)

        labels, samples = self.getData(normalize=True)

        # because we train the SVM with dict we need to redefine the zero-insert
        self.hasZeroInsert = False
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
            filename = splitext(self.strArffFileName)[0]
            filename += '.confusion.txt'
        if path is None:
            path = self._subdirs['data']

        with open(join(path, filename), "w") as f:
            f.write('log2(C) = %f\n' % log2c)
            f.write('log2(g) = %f\n' % log2g)
            f.write('accuracy = %f\n' % conf.ac_sample)
            f.write('\n')
            conf_array = conf.conf
            rows, cols = conf_array.shape
            f.write('confusion matrix (absolute)\n')
            f.write('%s\n' % '\t'.join([''] + ['%d' % self.nl2l[nl]
                                               for nl in range(cols)]))
            for r in range(rows):
                f.write('%s\n' % '\t'.join([str(self.nl2l[r])] +
                                           [str(conf_array[r,c])
                                            for c in range(cols)]))

    def importConfusion(self, path=None, filename=None):
        if filename is None:
            filename = os.path.splitext(self.strArffFileName)[0]
            filename += '.confusion.txt'
        if path is None:
            path = self._subdirs['data']

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
        #print len(labels), len(samples)
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

                #print n,c,g
                conf = ConfusionMatrix.from_lists(labels, predictions, self.l2nl)
                yield n, l2c, l2g, conf

                l2g += g_step
            l2c += c_step

class CommonObjectLearner(BaseLearner):

    def __init__(self, *args, **kw):
        super(CommonObjectLearner, self).__init__(*args, **kw)

    def setFeatureNames(self, feature_names):
        if self.lstFeatureNames is None:
            self.lstFeatureNames = feature_names
        assert self.lstFeatureNames == feature_names

    def applyObjects(self, image_objects):
        for obj in image_objects:
            self.dctImageObjects[obj.sample_id] = obj
            class_name = self.dctClassNames[obj.iLabel]
            try:
                self.dctFeatureData[class_name].extend([obj.aFeatures])
            except KeyError:
                self.dctFeatureData[class_name] = [obj.aFeatures]

            try:
                self.dctSampleNames[class_name].extend(obj.sample_id)
            except KeyError:
                self.dctSampleNames[class_name] = [obj.sample_id]


class MergedChannelLearner(BaseLearner):

    def __init__(self, *args, **kw):
        super(MergedChannelLearner, self).__init__(*args, **kw)


if __name__ ==  "__main__":
    import sys
    if isdir(sys.argv[1]):
        learner = CommonClassPredictor(sys.argv[1])
        learner.importFromArff()
        c, g, conf = learner.importConfusion()
        import pdb; pdb.set_trace()
    else:
        raise IOError("%s\n is not a valid directory" %sys.argv[1])
    #learner.statsFromConfusion(conf)
