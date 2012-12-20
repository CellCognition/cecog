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

from os.path import join, isdir, exists, splitext, isfile, basename
from collections import OrderedDict

import numpy
import svm

from pdk.fileutils import safe_mkdirs
from pdk.iterator import flatten
from pdk.map import dict_append_list
#from pdk.attributemanagers import (get_attribute_values,
#                                   set_attribute_values)

from cecog.learning.util import SparseWriter, ArffWriter, ArffReader
from cecog.learning.classifier import LibSvmClassifier as Classifier
from cecog.util.util import rgbToHex
from cecog.util.logger import LoggerObject
from cecog.util.util import makedirs

class ConfusionMatrix(object):
    """Simple holder to store a confusion matrix and to store and compute
    associated values.
    """

    def __init__(self, conf):
        """
        @param conf: squared matrix with manual annotations (gold-standard)
          along the rows and predicted values along the columns
        @type conf: numpy array
        """
        assert conf.ndim == 2
        assert conf.shape[0] == conf.shape[1]
        self.conf = conf
        reg = 0.0000000001

        # true-positives
        self.tp = numpy.diag(self.conf)
        # false-positives
        self.fp = numpy.sum(self.conf, axis=0) - self.tp
        # false-negatives
        self.fn = numpy.sum(self.conf, axis=1) - self.tp
        # true-negatives
        self.tn = numpy.sum(self.conf) - self.tp - self.fn - self.fp

        # sensitivity
        self.se = self.tp / numpy.asarray(self.tp + self.fn + reg, numpy.float)
        self.sensitivity = self.se

        # specificity
        self.sp = self.tn / numpy.asarray(self.tn + self.fp + reg, numpy.float)
        self.specificity = self.sp

        # accuracy
        self.ac = (self.tp + self.tn) / \
                  numpy.asarray(self.tp + self.tn + self.fp + self.fn + reg,
                                numpy.float)

        # positive prediction value (also precision)
        self.ppv = self.tp / numpy.asarray(self.tp + self.fp + reg, numpy.float)
        self.precision = self.ppv

        # negative prediction value
        self.npv = self.tn / numpy.asarray(self.tn + self.fn + reg, numpy.float)
        # samples
        self.samples = self.tp + self.fn

        # average values weighted by sample number
        nan = -numpy.isnan(self.se)
        self.wav_se = numpy.average(self.se[nan], weights=self.samples[nan])
        nan = -numpy.isnan(self.sp)
        self.wav_sp = numpy.average(self.sp[nan], weights=self.samples[nan])
        nan = -numpy.isnan(self.ppv)
        self.wav_ppv = numpy.average(self.ppv[nan], weights=self.samples[nan])
        nan = -numpy.isnan(self.npv)
        self.wav_npv = numpy.average(self.npv[nan], weights=self.samples[nan])
        nan = -numpy.isnan(self.ac)
        self.wav_ac = numpy.average(self.ac[nan], weights=self.samples[nan])

        # average values (not weighted by sample number)
        self.av_se = numpy.average(self.se[-numpy.isnan(self.se)])
        self.av_sp = numpy.average(self.sp[-numpy.isnan(self.sp)])
        self.av_ppv = numpy.average(self.ppv[-numpy.isnan(self.ppv)])
        self.av_npv = numpy.average(self.npv[-numpy.isnan(self.npv)])
        self.av_ac = numpy.average(self.ac[-numpy.isnan(self.ac)])

        # average accuracy per class
        self.ac_class = self.av_ac

        # accuracy per item (true-positives divided by all decisions)
        self.ac_sample = numpy.sum(self.tp) / numpy.sum(self.samples + reg,
                                                        dtype=numpy.float)

    def __len__(self):
        return self.conf.shape[0]

    def export(self, filename, sep='\t', mapping=None):
        f = file(filename, 'w')

        #data = self.ac.copy()
        overall = numpy.asarray([numpy.sum(self.samples),
                                 self.av_ac, self.av_se, self.av_sp,
                                 self.av_ppv, self.av_npv])
        woverall = numpy.asarray([numpy.sum(self.samples),
                                  self.wav_ac, self.wav_se, self.wav_sp,
                                  self.wav_ppv, self.wav_npv])
        data = numpy.vstack((self.samples,
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
    def from_pairs(cls, pairs, mapping):
        '''
        Constructs a ConfusionMatrix object from a list of pairs of the form
        (true label, predicted label).
        Requires a mapping from original labels to new labels in a way that new
        labels are ordered from 0 to k-1, for k classes

        @param pairs: list of pairs (tuples) in the form
          (true label, predicted label)
        @type pairs: sequence
        @param mapping: mapping of original to new labels
        @type mapping: dict

        @return: ConfusionMatrix
        '''
        k = len(mapping)
        conf = numpy.zeros((k, k))
        for l, v in pairs:
            l2 = mapping[int(l)]
            v2 = mapping[int(v)]
            conf[l2,v2] += 1
        return cls(conf)

    @classmethod
    def from_lists(cls, labels, predictions, mapping):
        '''
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
        '''
        return cls.from_pairs(zip(labels, predictions), mapping)


class BaseLearner(LoggerObject):

    # directory substructure
    ANNOTATIONS = 'annotations'
    DATA = 'data'
    SAMPLES = 'samples'
    CONTROLS = 'controls'

    def __init__(self, strEnvPath, strChannelId, strRegionId,
                 color_channel=None, prcs_channel=None):
        super(BaseLearner, self).__init__()

        self.name = basename(strEnvPath)
        self.color_channel = color_channel
        self.prcs_channel = prcs_channel

        self.strEnvPath = strEnvPath
        self.strChannelId = strChannelId
        self.strRegionId = strRegionId

        self.strArffFileName = 'features.arff'
        self.strSparseFileName ='features.sparse'
        self.strDefinitionFileName = 'class_definition.txt'
        self.filename_pickle = ' learner.pkl'
        self.lstFeatureNames = None

        self._class_definitions = []

        self.dctImageObjects = OrderedDict()
        self.dctFeatureData = OrderedDict()
        self.dctClassNames = {}
        self.dctClassLabels = {}
        self.dctHexColors = {}
        self.dctSampleNames = {}
        self.initEnv()

    @property
    def strEnvPath(self):
        return self._env_dir

    @strEnvPath.deleter
    def strEnvPath(self):
        del self._env_dir

    @strEnvPath.setter
    def strEnvPath(self, path):
        self._env_dir = path
        self.dctEnvPaths = {self.SAMPLES: join(path, "samples"),
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
            data[name] = numpy.asarray(data[name])
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


    def initEnv(self):
        env_path = self.strEnvPath
        if not isdir(env_path):
            raise IOError(("Classifier environment path '%s' does not exist." \
                           %env_path))
        for strName, strPath in self.dctEnvPaths.iteritems():
            makedirs(strPath)

    def getPath(self, strName):
        path = self.dctEnvPaths[strName]
        if not exists(path):
            os.mkdir(path)
        return path

    def loadDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.strDefinitionFileName
        if path is None:
            path = self.strEnvPath

        f = open(join(path, filename), "rb")
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
        f.close()

    def saveDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.strDefinitionFileName
        if path is None:
            path = self.strEnvPath
        f = open(join(path, filename), "wb")
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        for class_name in self.lstClassNames:
            class_label = self.dctClassLabels[class_name]
            color = self.dctHexColors[class_name]
            writer.writerow([class_label, class_name, color])
        f.close()

    def exportRanges(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = os.path.splitext(self.strArffFileName)[0]
            strFileName += '.range'
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']

        all_features = numpy.asarray(flatten(self.dctFeatureData.values()))
        features_min = numpy.min(all_features, 0)
        features_max = numpy.max(all_features, 0)

        f = file(os.path.join(strFilePath, strFileName), 'w')
        f.write('x\n')
        f.write('-1 1\n')
        for idx, (m1, m2) in enumerate(zip(features_min, features_max)):
            f.write('%d %.10e %.10e\n' % (idx+1, m1, m2))
        f.close()

    def importFromArff(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.strArffFileName
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']

        oReader = ArffReader(os.path.join(strFilePath, strFileName))
        self.dctFeatureData = oReader.dctFeatureData
        self.dctClassNames = oReader.dctClassNames
        self.dctClassLabels = oReader.dctClassLabels
        self.lstFeatureNames = oReader.lstFeatureNames
        self.dctHexColors = oReader.dctHexColors
        self.hasZeroInsert = oReader.hasZeroInsert

    def check(self):
        filename = splitext(self.strArffFileName)[0]
        result = {'path_env': self.strEnvPath,
                  'path_data': self.dctEnvPaths['data'],
                  'path_samples': self.dctEnvPaths['samples'],
                  'path_annotations': self.dctEnvPaths['annotations'],
                  'model': join(self.dctEnvPaths['data'], '%s.model' %filename),
                  'range': join(self.dctEnvPaths['data'], '%s.range' %filename),
                  'conf': join(self.dctEnvPaths['data'], '%s.confusion.txt' %filename),
                  'arff': join(self.dctEnvPaths['data'], self.strArffFileName),
                  'definition': join(self.strEnvPath, self.strDefinitionFileName),
                  # result of validity checks
                  'has_path_data': isdir(self.dctEnvPaths['data']),
                  'has_path_samples': isdir(self.dctEnvPaths['samples']),
                  'has_path_annotations': isdir(self.dctEnvPaths['annotations']),
                  'has_model': isfile(join(self.dctEnvPaths['data'], '%s.model' % filename)),
                  'has_range': isfile(join(self.dctEnvPaths['data'], '%s.range' % filename)),
                  'has_conf': isfile(join(self.dctEnvPaths['data'], '%s.confusion.txt' % filename)),
                  'has_arff': isfile(join(self.dctEnvPaths['data'], self.strArffFileName)),
                  'has_definition': isfile(join(self.strEnvPath, self.strDefinitionFileName))}
        return result

    def exportToArff(self, path=None, filename=None):
        if filename is None:
            filename = self.strArffFileName
        if path is None:
            path = self.dctEnvPaths['data']

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
            directory = self.dctEnvPaths['data']

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
            strFilePath = self.dctEnvPaths['data']
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
            strFilePath = self.dctEnvPaths['data']
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


        self.classifier = Classifier(self.dctEnvPaths['data'], self.logger,
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
        labels = numpy.asarray(labels)
        samples = numpy.asarray(samples)
        if normalize:
            lo = numpy.min(samples, 0)
            hi = numpy.max(samples, 0)
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
        filter_idx = numpy.array([], numpy.int32)
        features = numpy.asarray(self.lstFeatureNames)
        feature_idx = numpy.arange(len(features))
        for data in self.dctFeatureData.itervalues():
            filter_idx = numpy.append(filter_idx, feature_idx[numpy.any(numpy.isnan(data), 0)])
        filter_idx = numpy.unique(filter_idx)
        if apply:
            for name in self.dctFeatureData:
                self.dctFeatureData[name] = numpy.delete(self.dctFeatureData[name], filter_idx, 1)
            self.lstFeatureNames = numpy.delete(features, filter_idx).tolist()
        return features[filter_idx]

    def train(self, c, g, probability=True, compensation=True,
              path=None, filename=None, save=True):
        if filename is None:
            filename = splitext(self.strArffFileName)[0]
            filename += '.model'
        if path is None:
            path = self.dctEnvPaths['data']
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
            path = self.dctEnvPaths['data']

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
            path = self.dctEnvPaths['data']

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
            conf = ConfusionMatrix(numpy.asarray(conf_array))
        return log2c, log2g, conf

    def _calculateCompensation(self, labels):
        ulabels = numpy.unique(labels)
        count = numpy.bincount(labels)[ulabels]
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

    def applyObjects(self, images):
        for image in images:
            self.dctImageObjects[image.sample_id] = image
            class_name = self.dctClassNames[image.iLabel]
            dict_append_list(self.dctFeatureData, class_name, image.aFeatures)
            dict_append_list(self.dctSampleNames, class_name, image.sample_id)

if __name__ ==  "__main__":
    learner = CommonClassPredictor(strEnvPath='/Users/miheld/data/Classifiers/H2b_20x_MD_exp911_DG')
    learner.importFromArff()
    c, g, conf = learner.importConfusion()
    #learner.statsFromConfusion(conf)
