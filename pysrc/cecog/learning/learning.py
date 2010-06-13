"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

#-------------------------------------------------------------------------------
# standard library imports:
#

import os, \
       re, \
       csv, \
       copy

#-------------------------------------------------------------------------------
# extension module imports:
#

import numpy
import svm


from pdk.options import Option
from pdk.optionmanagers import OptionManager
#from pdk.containers.tablefactories import newTable
#from pdk.containers.tableio import exportTable
from pdk.ordereddict import OrderedDict
from pdk.fileutils import safe_mkdirs
from pdk.iterator import flatten
from pdk.map import dict_append_list
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)

#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog.learning.util import SparseWriter, ArffWriter, ArffReader
from cecog.learning.classifier import LibSvmClassifier
from cecog.util.util import rgbToHex, LoggerMixin
#from cecog.ccore import SingleObjectContainer


#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#



#-------------------------------------------------------------------------------
# classes:
#

class BaseLearner(LoggerMixin, OptionManager):

    OPTIONS = {"strEnvPath" :          Option(".", callback="_onEnvPath"),
               "lstClassDefinitions" : Option([], callback="_onDefineClasses"),
               "strArffFileName" :     Option("features.arff"),
               "strSparseFileName" :   Option("features.sparse"),
               "strDefinitionFileName" :   Option("class_definition.txt"),
               "filename_pickle" :     Option("learner.pkl"),
              }

    __attributes__ = ['dctFeatureData',
                      'dctSampleData',
                      'dctClassNames',
                      'dctClassLabels',
                      'lstFeatureNames',
                      'dctHexColors',
                      'dctEnvPaths',
                      'dctImageObjects']

    def __init__(self, **options):
        self.dctFeatureData = OrderedDict()
        self.dctClassNames = {}
        self.dctClassLabels = {}
        self.lstFeatureNames = None
        self.dctHexColors = {}
        self.dctSampleNames = {}
        self.dctEnvPaths = {}
        self.hasZeroInsert = True
        self.dctImageObjects = OrderedDict()

        super(BaseLearner, self).__init__(**options)

    def __getstate__(self):
        dctState = get_attribute_values(self)
        return dctState

    def __setstate__(self, state):
        set_attribute_values(self, state)

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
        '''
        convert a label into a new label
        (new labels are continuous from 0..number of classes
        '''
        return dict([(l,i) for i,l in enumerate(self.lstClassLabels)])

    @property
    def nl2l(self):
        '''
        convert a new label into the original label
        '''
        return dict([(i,l) for i,l in enumerate(self.lstClassLabels)])


    #def getFeaturesByName(self, featureName):


    def initEnv(self):
        env_path = self.getOption('strEnvPath')
        if not os.path.isdir(env_path):
            raise IOError("Classifier environment path '%s' does not exist." %
                          env_path)
        for strName, strPath in self.dctEnvPaths.iteritems():
            safe_mkdirs(strPath)

    def _onDefineClasses(self, lstClassDefinitions):
        for dctClassDescription in lstClassDefinitions:
            strClassName = dctClassDescription['name']
            iClassLabel  = dctClassDescription['label']
            tplColor     = dctClassDescription['color']

            # FIXME: folders not supported yet!!!
            if ('folders' not in dctClassDescription or
                dctClassDescription['folders'] is None or
                len(dctClassDescription['folders']) == 0):
                lstFolders = [strClassName]
            else:
                lstFolders = dctClassDescription['folders']

            self.dctClassNames[iClassLabel] = strClassName
            self.dctClassLabels[strClassName] = iClassLabel
            self.dctHexColors[strClassName] = rgbToHex(*tplColor)


    def _onEnvPath(self, strEnvPath):
        self.dctEnvPaths = {'samples' :    os.path.join(strEnvPath, "samples"),
                            'annotations': os.path.join(strEnvPath, "annotations"),
                            'data':        os.path.join(strEnvPath, "data"),
                            'controls':    os.path.join(strEnvPath, "controls"),
                       }

    def getPath(self, strName):
        return self.dctEnvPaths[strName]

    def loadDefinition(self, path=None, filename=None):
        if filename is None:
            filename = self.getOption('strDefinitionFileName')
        if path is None:
            path = self.getOption('strEnvPath')
        f = open(os.path.join(path, filename), "r")
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

    def exportRanges(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = os.path.splitext(self.getOption('strArffFileName'))[0]
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
            f.write('%d %f %f\n' % (idx+1, m1, m2))
        f.close()

    def importFromArff(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.getOption('strArffFileName')
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']

        oReader = ArffReader(os.path.join(strFilePath, strFileName))
        self.dctFeatureData = oReader.dctFeatureData
        self.dctClassNames = oReader.dctClassNames
        self.dctClassLabels = oReader.dctClassLabels
        self.lstFeatureNames = oReader.lstFeatureNames
        self.dctHexColors = oReader.dctHexColors
        self.hasZeroInsert = oReader.hasZeroInsert
        #print self.dctClassLabels
        #print self.dctClassNames
        #print self.dctFeatureData.keys()

    def check(self):
        filename = os.path.splitext(self.getOption('strArffFileName'))[0]
        result = {'path_env' : self.getOption('strEnvPath'),
                  'path_data' : self.dctEnvPaths['data'],
                  'path_samples' : self.dctEnvPaths['samples'],
                  'path_annotations' : self.dctEnvPaths['annotations'],
                  'model' : os.path.join(self.dctEnvPaths['data'], '%s.model' % filename),
                  'range' : os.path.join(self.dctEnvPaths['data'], '%s.range' % filename),
                  'conf' : os.path.join(self.dctEnvPaths['data'], '%s.confusion.txt' % filename),
                  'arff' : os.path.join(self.dctEnvPaths['data'], self.getOption('strArffFileName')),
                  'definition' : os.path.join(self.getOption('strEnvPath'), self.getOption('strDefinitionFileName')),
                  }
        result.update({'has_path_data' : os.path.isdir(self.dctEnvPaths['data']),
                       'has_path_samples' : os.path.isdir(self.dctEnvPaths['samples']),
                       'has_path_annotations' : os.path.isdir(self.dctEnvPaths['annotations']),
                       'has_model' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], '%s.model' % filename)),
                       'has_range' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], '%s.range' % filename)),
                       'has_conf' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], '%s.confusion.txt' % filename)),
                       'has_arff' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], self.getOption('strArffFileName'))),
                       'has_definition' : os.path.isfile(os.path.join(self.getOption('strEnvPath'), self.getOption('strDefinitionFileName'))),
                       }
                      )
        return result


    def exportToArff(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.getOption('strArffFileName')
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']

        print self.hasZeroInsert
        oWriter = ArffWriter(os.path.join(strFilePath, strFileName),
                             self.lstFeatureNames,
                             self.dctClassLabels,
                             dctHexColors=self.dctHexColors,
                             hasZeroInsert=self.hasZeroInsert)
        oWriter.writeAllFeatureData(self.dctFeatureData)
        oWriter.close()

    def exportToSparse(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.getOption('strSparseFileName')
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']

        oWriter = SparseWriter(os.path.join(strFilePath, strFileName),
                               self.lstFeatureNames,
                               self.dctClassLabels)
        oWriter.writeAllFeatureData(self.dctFeatureData)
        oWriter.close()

    def importSampleNames(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = os.path.splitext(self.getOption('strArffFileName'))[0]
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
            strFileName = os.path.splitext(self.getOption('strArffFileName'))[0]
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



class ClassTrainer(BaseLearner):

    OPTIONS = {"strImgRePattern" : Option("^(?P<id_string>.+?)__img\..+?$"),
               "strMskRePattern" : Option("^(?P<id_string>.+?)__msk\..+?$"),
               }

    def __init__(self, **options):
        super(ClassTrainer, self).__init__(**options)

    def importSamples(self, strObjectRootPath=None):
        if strObjectRootPath is None:
            strObjectRootPath = self.dctEnvPaths['samples']

        self.dctContainers = {}

        self.oLogger.info("\n*** importing class samples ***\n")

        oRegexImg = re.compile(self.getOption("strImgRePattern"), re.I)
        oRegexMsk = re.compile(self.getOption("strMskRePattern"), re.I)

        for iClassLabel, strClassName in self.dctClassNames.iteritems():

            self.dctContainers[strClassName] = []
            self.oLogger.info(" * class '%s', ID %d" % (strClassName, iClassLabel))

            for strSampleFolder in [strClassName]:
                strBaseDir = os.path.join(self.dctEnvPaths['samples'], strSampleFolder)
                self.oLogger.info("    - subclass %s, dir '%s'" % (strSampleFolder, strBaseDir))
                lstDir = os.listdir(strBaseDir)
                strFilenameImg = None
                strFilenameMsk = None
                strFilenameId = None
                bKeepLoop = True
                while bKeepLoop:
                    # break the loop if no candidate for (img,msk)-pair is found
                    bKeepLoop = False
                    for strItem in lstDir[:]:
                        if strFilenameImg is None:
                            oMatch = oRegexImg.match(strItem)
                            if not oMatch is None:
                                strFoundId = oMatch.group('id_string')
                                if strFilenameId is None or strFoundId == strFilenameId:
                                    strFilenameImg = os.path.join(strBaseDir, strItem)
                                    lstDir.remove(strItem)
                                    strFilenameId = strFoundId
                                    bKeepLoop = True
                                    break
                        elif strFilenameMsk is None:
                            oMatch = oRegexMsk.match(strItem)
                            if not oMatch is None:
                                strFoundId = oMatch.group('id_string')
                                if strFilenameId is None or strFoundId == strFilenameId:
                                    strFilenameMsk = os.path.join(strBaseDir, strItem)
                                    lstDir.remove(strItem)
                                    strFilenameId = strFoundId
                                    bKeepLoop = True
                                    break
                    if (not strFilenameImg is None and not strFilenameMsk is None):
                        self.oLogger.debug("       (%s, %s)" % (os.path.split(strFilenameImg)[1],
                                                                os.path.split(strFilenameMsk)[1]))

                        oContainer = SingleObjectContainer(strFilenameImg, strFilenameMsk)

                        # FIXME: track image filenames (object origin)
                        self.dctContainers[strClassName].append(oContainer)
                        strFilenameId = None
                        strFilenameImg = None
                        strFilenameMsk = None

                self.oLogger.info("    - %d samples" % len(self.dctContainers[strClassName]))
                self.oLogger.info("")


    def extractFeaturesFromSamples(self,
                                   lstFeatureCategories,
                                   lstHaralickCategories,
                                   lstHaralickDistances,
                                   lstFilterFeatures = []):

        self.oLogger.info("\n*** extracting features from samples ***\n")
        iObjectCount = 0
        for strClassName, lstContainer in self.dctContainers.iteritems():
            self.dctFeatureData[strClassName] = []

            iClassLabel = self.dctClassLabels[strClassName]

            self.oLogger.info(" * class '%s', ID %s, samples: %d" % (strClassName, iClassLabel, len(lstContainer)))
            iObjectCount += len(lstContainer)

            for oContainer in lstContainer:
                self.extractFeatures(oContainer, lstFeatureCategories,
                                     lstHaralickCategories, lstHaralickDistances)

                # add all FeatureNames from the object to the list and filter names out
                dctObjectFeatureData = oContainer.getObjects()[1].getFeatures()
                if self.lstFeatureNames is None or len(self.lstFeatureNames) == 0:
                    self.lstFeatureNames = [strFeatureName
                                            for strFeatureName in dctObjectFeatureData.keys()
                                            if strFeatureName not in lstFilterFeatures]
                    self.oLogger.debug("   feature names: %s" % self.lstFeatureNames)
                    #logging.debug("   dctFeature: %s" % dctFeature)

                # finally selected feature data
                lstFeatureData = [dctObjectFeatureData[strFeatureName]
                                  for strFeatureName in self.lstFeatureNames]

                self.dctFeatureData[strClassName].append(lstFeatureData)

        for strClassName in self.dctFeatureData:
            self.dctFeatureData[strClassName] = numpy.asarray(self.dctFeatureData[strClassName], numpy.float32)

        self.oLogger.info("\n*** total objects: %d  (average %.1f per class)" %
                          (iObjectCount, iObjectCount / float(len(self.dctClassNames))))


class ClassPredictor(BaseLearner):

    OPTIONS = {"clsClassifier" :  Option(LibSvmClassifier,
                                         doc="", autoInitialize=False),
               "strModelPrefix" : Option('features'),
              }

    __attributes__ = ['oClassifier']


    def __init__(self, **options):
        super(ClassPredictor, self).__init__(**options)
        self.oClassifier = None
        self.initializeOption('clsClassifier')

    def loadClassifier(self):
        if self.getOption('strModelPrefix') is None:
            strModelPrefix = os.path.splitext(self.getOption('strSparseFileName'))[0]
        else:
            strModelPrefix = self.getOption('strModelPrefix')

        clsClassifier = self.getOption('clsClassifier')
        self.oClassifier = clsClassifier(self.dctEnvPaths['data'], self.oLogger,
                                         strSvmPrefix=strModelPrefix,
                                         hasZeroInsert=self.hasZeroInsert)
        self.bProbability = self.oClassifier.bProbability

    def predict(self, aFeatureData, lstFeatureNames):
        dctNameLookup = dict([(name,i) for i,name in enumerate(lstFeatureNames)])
        lstRequiredFeatureData = [aFeatureData[dctNameLookup[x]]
                                  for x in self.lstFeatureNames]
        #lstRequiredFeatureData = aFeatureData
        return self.oClassifier(lstRequiredFeatureData)

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
            lo = numpy.amin(samples, 0)
            hi = numpy.amax(samples, 0)
            # scale between -1 and +1
            samples = 2.0 * (samples - lo) / (hi - lo) - 1.0
        # FIXME: stupid libSVM conversions
        #labels = map(int, labels)
        samples = [dict([(i+1, float(v))
                         for i,v in enumerate(items)
                         if not numpy.isnan(v)])
                   for items in samples]
        return labels, samples

    def train(self, c, g, probability=True, compensation=True,
              path=None, filename=None, save=True):
        if filename is None:
            filename = os.path.splitext(self.getOption('strArffFileName'))[0]
            filename += '.model'
        if path is None:
            path = self.dctEnvPaths['data']
        param = svm.svm_parameter(kernel_type=svm.RBF,
                                  C=c, gamma=g,
                                  probability=1 if probability else 0)

        labels, samples = self.getData(normalize=True)
        # because we train the SVM with dict we need to redefine the zero-insert
        self.hasZeroInsert = True
        if not self.oClassifier is None:
            self.oClassifier.setOption('hasZeroInsert', True)

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
            filename = os.path.splitext(self.getOption('strArffFileName'))[0]
            filename += '.confusion.txt'
        if path is None:
            path = self.dctEnvPaths['data']
        f = file(os.path.join(path, filename), 'w')
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
#        f.write('\n')
#        f.write('confusion matrix (relative)\n')
#        conf_norm = conf.swapaxes(0,1) / numpy.array(numpy.sum(conf, 1),
#                                                     numpy.float)
#        conf_norm = conf_norm.swapaxes(0,1)
#        f.write('%s\n' % '\t'.join([''] + [str(self.nl2l[nl])
#                                           for nl in range(cols)]))
#        for r in range(rows):
#            f.write('%s\n' % '\t'.join([str(self.nl2l[r])] + [str(conf_norm[r,c])
#                                                         for c in range(cols)]))
        f.close()


    def importConfusion(self, path=None, filename=None):
        if filename is None:
            filename = os.path.splitext(self.getOption('strArffFileName'))[0]
            filename += '.confusion.txt'
        if path is None:
            path = self.dctEnvPaths['data']
        f = file(os.path.join(path, filename), 'Ur')
        log2c = float(f.readline().split('=')[1].strip())
        log2g = float(f.readline().split('=')[1].strip())
        #accuracy = float(f.readline().split('=')[1].strip())
        f.readline()
        f.readline()
        f.readline()
        f.readline()
        conf_array = []
        for line in f:
            line = line.strip()
            if len(line) == 0:
                break
            #print line
            items = map(int, map(float, line.split('\t')[1:]))
            #print items
            conf_array.append(items)
        conf = ConfusionMatrix(numpy.asarray(conf_array))
        return log2c, log2g, conf

    def _calculateCompensation(self, labels):
        ulabels = numpy.unique(labels)
        count = numpy.bincount(labels)[ulabels]
        #weight = float(len(labels)) / count
        weight = (float(len(labels)) - count) / count
        weight_label = map(int, ulabels)
        #print count
        #print ulabels
        #print weight
        #print weight_label
        #print len(labels)
        #print weight * count
        #print sum(weight * count)
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
                conf = ConfusionMatrix.from_lists(labels, predictions,
                                                  self.l2nl)
                yield n,l2c,l2g,conf

                l2g += g_step
            l2c += c_step



class ConfusionMatrix(object):
    '''
    Simple holder to store a confusion matrix and to store and compute
    associated values.
    '''

    def __init__(self, conf):
        '''
        @param conf: squared matrix with manual annotations (gold-standard)
          along the rows and predicted values along the columns
        @type conf: numpy array
        '''
        assert conf.ndim == 2
        assert conf.shape[0] == conf.shape[1]
        self.conf = conf

        # true-positives
        self.tp = numpy.diag(self.conf)
        # false-positives
        self.fp = numpy.sum(self.conf, axis=0) - self.tp
        # false-negatives
        self.fn = numpy.sum(self.conf, axis=1) - self.tp
        # true-negatives
        self.tn = numpy.sum(self.conf) - self.tp - self.fn - self.fp

        # sensitivity
        self.se = self.tp / numpy.asarray(self.tp + self.fn, numpy.float)
        self.sensitivity = self.se

        # specificity
        self.sp = self.tn / numpy.asarray(self.tn + self.fp, numpy.float)
        self.specificity = self.sp

        # accuracy
        self.ac = (self.tp + self.tn) / \
                  numpy.asarray(self.tp + self.tn + self.fp + self.fn,
                                numpy.float)

        # positive prediction value (also precision)
        self.ppv = self.tp / numpy.asarray(self.tp + self.fp, numpy.float)
        self.precision = self.ppv

        # negative prediction value
        self.npv = self.tn / numpy.asarray(self.tn + self.fn, numpy.float)
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
        self.ac_sample = numpy.sum(self.tp) / numpy.sum(self.samples,
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



class ConfusionMatrix2(ConfusionMatrix):

    def __init__(self, conf):
        #super(ConfusionMatrix2, self).__init__(conf)
        pass


class CommonMixin(OptionManager):

    OPTIONS = {'dctCollectSamples' : Option(None),
               }

    __attributes__ = ['strChannelId',
                      'strRegionId',
                      ]

    def __init__(self, *args, **options):

        super(CommonMixin, self).__init__(*args, **options)

        dctCollectSamples = self.getOption('dctCollectSamples')
        self.strChannelId = dctCollectSamples['strChannelId']
        self.strRegionId = dctCollectSamples['strRegionId']

        self.setOption('strEnvPath', dctCollectSamples['strEnvPath'])
        BaseLearner.initEnv(self)

#    def initCommon(self):
#        BaseLearner.initEnv(self)
#        dctCollectSamples = self.getOption('dctCollectSamples')
#
#        for iClassLabel, dctAnnotations in dctCollectSamples['dctLabels'].iteritems():
#            strClassName = dctAnnotations['strClassName']
#            self.dctClassNames[iClassLabel] = strClassName
#            self.dctClassLabels[strClassName] = iClassLabel
#            self.dctHexColors[strClassName] = dctAnnotations['strColor']


class CommonClassPredictor(ClassPredictor, CommonMixin):

    def __init__(self, **options):
        super(CommonClassPredictor, self).__init__(**options)

class CommonObjectLearner(BaseLearner, CommonMixin):

    def __init__(self, **options):
        super(CommonObjectLearner, self).__init__(**options)
        #self.initCommon()

    def setFeatureNames(self, lstFeatureNames):
        if self.lstFeatureNames is None:
            self.lstFeatureNames = lstFeatureNames
        assert self.lstFeatureNames == lstFeatureNames

    def applyObjects(self, lstImageObjects):
        for oObj in lstImageObjects:
            self.dctImageObjects[oObj.sample_id] = oObj
            strClassName = self.dctClassNames[oObj.iLabel]
            dict_append_list(self.dctFeatureData, strClassName, oObj.aFeatures)
            dict_append_list(self.dctSampleNames, strClassName, oObj.sample_id)

if __name__ ==  "__main__":

    learner = ClassPredictor(strEnvPath='/Users/miheld/data/Classifiers/H2b_20x_MD_exp911_DG')
    learner.importFromArff()
    c, g, conf = learner.importConfusion()
    #learner.statsFromConfusion(conf)
