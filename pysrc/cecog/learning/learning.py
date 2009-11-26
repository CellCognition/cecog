"""
The Mito-Imaging Project
Copyright (c) 2005-2006 Michael Held

Basic classes to define a training set, extract features from object-files and
run cross-validations tests
"""

__author__ =   'Michael Held'
__date__ =     '$Date$'
__revision__ = '$Rev$'
__source__ =   '$URL$'


#------------------------------------------------------------------------------
# standard library imports:
#

import sys, \
       os, \
       re, \
       math, \
       copy, \
       shelve, \
       random, \
       time, \
       subprocess, \
       pprint, \
       logging

#------------------------------------------------------------------------------
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
from pdk.iterator import unique, flatten
from pdk.map import dict_append_list
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)


#------------------------------------------------------------------------------
# cecog module imports:
#
from cecog.learning.util import SparseWriter, ArffWriter, ArffReader
from cecog.learning.classifier import LibSvmClassifier
from cecog.util import rgbToHex, LoggerMixin
from cecog.ccore import SingleObjectContainer


#------------------------------------------------------------------------------
# constants:
#


#------------------------------------------------------------------------------
# functions:
#



#------------------------------------------------------------------------------
# classes:
#


class BaseLearner(LoggerMixin, OptionManager):

    OPTIONS = {"strEnvPath" :          Option(".", callback="_onEnvPath"),
               "lstClassDefinitions" : Option([], callback="_onDefineClasses"),
               "strArffFileName" :     Option("features.arff"),
               "strSparseFileName" :   Option("features.sparse"),
               "filename_sampleids" :  Option("sample_ids.tsv"),
               "filename_pickle" :     Option("learner.pkl"),
               #"clsClassifier":        Option(None),
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
        self.dctSampleData = OrderedDict()
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
        return dict([(k,len(v)) for k,v in self.dctFeatureData.iteritems()])


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
        strEnvPath = self.getOption('strEnvPath')
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

    def importSampleNames(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = os.path.splitext(self.getOption('strArffFileName'))[0]
            strFileName = '%s.sample_names.tsv' % strFileName
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
                  'definition' : os.path.join(self.getOption('strEnvPath'), 'class_definition.tsv'),
                  }
        result.update({'has_path_data' : os.path.isdir(self.dctEnvPaths['data']),
                       'has_path_samples' : os.path.isdir(self.dctEnvPaths['samples']),
                       'has_path_annotations' : os.path.isdir(self.dctEnvPaths['annotations']),
                       'has_model' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], '%s.model' % filename)),
                       'has_range' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], '%s.range' % filename)),
                       'has_conf' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], '%s.confusion.txt' % filename)),
                       'has_arff' : os.path.isfile(os.path.join(self.dctEnvPaths['data'], self.getOption('strArffFileName'))),
                       'has_definition' : os.path.isfile(os.path.join(self.getOption('strEnvPath'), 'class_definition.tsv')),
                       }
                      )
        return result


    def exportToArff(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.getOption('strArffFileName')
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']

        oWriter = ArffWriter(os.path.join(strFilePath, strFileName),
                             self.lstFeatureNames,
                             self.dctClassLabels,
                             dctHexColors=self.dctHexColors)
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

    def exportSampleIds(self, strFilePath=None, strFileName=None):
        if strFileName is None:
            strFileName = self.getOption('filename_sampleids')
        if strFilePath is None:
            strFilePath = self.dctEnvPaths['data']
        f = file(os.path.join(strFilePath, strFileName), 'w')
        for k, v in self.dctSampleData.iteritems():
            for sample_id in v:
                f.write('%s\n' % sample_id)
        f.close()

    def export(self):
        self.exportToArff()
        self.exportToSparse()
        self.exportSampleIds()

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
        #BaseLearner(self).initEnv()

    def initCommon(self):
        BaseLearner.initEnv(self)
        dctCollectSamples = self.getOption('dctCollectSamples')

        for iClassLabel, dctAnnotations in dctCollectSamples['dctLabels'].iteritems():
            strClassName = dctAnnotations['strClassName']
            self.dctClassNames[iClassLabel] = strClassName
            self.dctClassLabels[strClassName] = iClassLabel
            self.dctHexColors[strClassName] = dctAnnotations['strColor']


class CommonObjectLearner(BaseLearner, CommonMixin):

    def __init__(self, **options):
        super(CommonObjectLearner, self).__init__(**options)
        self.initCommon()

    def setFeatureNames(self, lstFeatureNames):
        if self.lstFeatureNames is None:
            self.lstFeatureNames = lstFeatureNames
        assert self.lstFeatureNames == lstFeatureNames

    def applyObjects(self, lstImageObjects):
        for oObj in lstImageObjects:
            self.dctImageObjects[oObj.sample_id] = oObj
            strClassName = self.dctClassNames[oObj.iLabel]
            dict_append_list(self.dctFeatureData, strClassName, oObj.aFeatures)
            dict_append_list(self.dctSampleData, strClassName, oObj.sample_id)



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
               "strModelPrefix" : Option(None),
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
        lstRequiredFeatureData = [aFeatureData[dctNameLookup[x]] for x in self.lstFeatureNames]
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
        return labels, samples

    def train(self, c, g, probability=1, compensation=True,
              path=None, filename=None):
        if filename is None:
            filename = os.path.splitext(self.getOption('strArffFileName'))[0]
            filename += '.model'
        if path is None:
            path = self.dctEnvPaths['data']
        param = svm.svm_parameter(kernel_type=svm.RBF,
                                  C=c, gamma=g,
                                  probability=probability)
        labels, samples = self.getData(normalize=True)
        if compensation:
            weight, weight_label = self._calculateCompensation(labels)
            param.weight = weight
            param.weight_label = weight_label
            param.nr_weight = len(weight)

        problem = svm.svm_problem(labels, samples)
        model = svm.svm_model(problem, param)
        model.save(os.path.join(path, filename))

    def exportConfusion(self, c, g, accuracy, conf, path=None, filename=None):
        if filename is None:
            filename = os.path.splitext(self.getOption('strArffFileName'))[0]
            filename += '.confusion.txt'
        if path is None:
            path = self.dctEnvPaths['data']
        f = file(os.path.join(path, filename), 'w')
        f.write('log2(C) = %f\n' % c)
        f.write('log2(g) = %f\n' % g)
        f.write('accuracy = %f\n' % accuracy)
        f.write('\n')
        rows, cols = conf.shape
        f.write('confusion matrix (absolute)\n')
        f.write('%s\n' % '\t'.join([''] + ['%d' % self.nl2l[nl]
                                           for nl in range(cols)]))
        for r in range(rows):
            f.write('%s\n' % '\t'.join([str(self.nl2l[r])] + [str(conf[r,c])
                                                         for c in range(cols)]))
        f.write('\n')
        f.write('confusion matrix (relative)\n')
        conf_norm = conf.swapaxes(0,1) / numpy.array(numpy.sum(conf, 1), numpy.float)
        conf_norm = conf_norm.swapaxes(0,1)
        f.write('%s\n' % '\t'.join([''] + [str(self.nl2l[nl])
                                           for nl in range(cols)]))
        for r in range(rows):
            f.write('%s\n' % '\t'.join([str(self.nl2l[r])] + [str(conf_norm[r,c])
                                                         for c in range(cols)]))
        f.close()


    def importConfusion(self, path=None, filename=None):
        if filename is None:
            filename = os.path.splitext(self.getOption('strArffFileName'))[0]
            filename += '.confusion.txt'
        if path is None:
            path = self.dctEnvPaths['data']
        f = file(os.path.join(path, filename), 'Ur')
        c = float(f.readline().split('=')[1].strip())
        g = float(f.readline().split('=')[1].strip())
        accuracy = float(f.readline().split('=')[1].strip())
        f.readline()
        f.readline()
        f.readline()
        conf = []
        for line in f:
            line = line.strip()
            if len(line) == 0:
                break
            #print line
            items = map(int, map(float, line.split('\t')[1:]))
            #print items
            conf.append(items)
        conf = numpy.asarray(conf)
        return c, g, accuracy, conf

    def _calculateCompensation(self, labels):
        ulabels = numpy.unique(labels)
        count = numpy.bincount(labels)[ulabels]
        #weight = float(len(labels)) / count
        weight = (float(len(labels)) - count) / count
        weight_label = ulabels
        #print count
        #print ulabels
        #print weight
        #print weight_label
        #print len(labels)
        #print weight * count
        #print sum(weight * count)
        return weight, weight_label

    def iterGridSearchSVM(self, c_info=None, g_info=None, fold=5,
                          probability=0, compensation=True):
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

        c = c_begin
        while c <= c_end:
            g = g_begin
            while g <= g_end:

                param = svm.svm_parameter(kernel_type = svm.RBF,
                                          C=2**c, gamma=2**g,
                                          probability=probability)
                if compensation:
                    param.weight = weight
                    param.weight_label = weight_label
                    param.nr_weight = len(weight)

                validation = svm.cross_validation(problem, param, fold)
                validation = map(int, validation)

                yield n,c,g,validation,labels

                g += g_step
            c += c_step



    def crossValidation(self, c=None, g=None, probability=1):
        #print self.dctFeatureData
        #print self.oClassifier.oSvmModel.model
        #print dir(self.oClassifier.oSvmModel.svm_type)
        #print dir(self.oClassifier.oSvmModel.model)
        #sys.exit(0)

        import svm
        oSvmParam = svm.svm_parameter(kernel_type = svm.RBF, C=c, gamma=g,
                                      probability=probability)

        dctLabelMapping = dict(zip(self.dctClassNames, self.dctClassNames))

#        dctLabelMapping = {1 : 1,
#                           2 : 2,
#                           3 : 3,
#                           4 : 4,
#                           5 : 5,
#                           6 : 6,
#                           }

#        dctLabelMapping = {1 : 1,
#                           2 : 2,
#                           3 : 3,
#                           4 : 3,
#                           5 : 1,
#                           6 : 1,
#                           7 : 4,
#                           }

#        for iLabelC, iLabelN in dctLabelMapping.iteritems():
#            strName = self.dctClassNames[iLabelC]
#            self.dctClassLabels[strName] = iLabelN

        lstPattern = []
        lstLabels = []
        for strClassName, lstSamples in self.dctFeatureData.iteritems():
            iClassLabel = self.dctClassLabels[strClassName]
            for aSample in lstSamples:
                lstLabels.append(iClassLabel)
                lstPattern.append([0]+list(self.oClassifier.normalize(aSample)))

        bDoAsymetryCompensation = False
        weight_label, weight = [], []
        if bDoAsymetryCompensation:
            for label in unique(self.dctClassLabels.values()):
                positiveCount = lstLabels.count(label)
                negativeCount = len(lstLabels) - positiveCount
                weight.append(float(negativeCount)/float(positiveCount))
                weight_label.append(label)
            oSvmParam.weight = weight
            oSvmParam.weight_label = weight_label
            oSvmParam.nr_weight = len(weight)

        oSvmProblem = svm.svm_problem(lstLabels, lstPattern)
        lstTargets = map(int, svm.cross_validation(oSvmProblem, oSvmParam, 5))

        iAccurateVote = 0
        dctCrossVote = {}

        for iLabelC, iLabelN in dctLabelMapping.iteritems():
            strName = self.dctClassNames[iLabelC]
            self.dctClassLabels[strName] = iLabelN

        print self.dctClassLabels
        print self.dctClassNames
        aCrossVote = numpy.zeros([max(unique(self.dctClassLabels.values()))]*2)
        for iTrueLabel, iTestLabel in zip(lstLabels, lstTargets):

            #strTrueName = self.dctClassNames[iTrueLabel]
            #strTestName = self.dctClassNames[iTestLabel]

            iTrueLabel = dctLabelMapping[iTrueLabel]
            iTestLabel = dctLabelMapping[iTestLabel]

            aCrossVote[iTrueLabel-1,iTestLabel-1] += 1

            if iTrueLabel == iTestLabel:
                iAccurateVote += 1


        fAccuracy = iAccurateVote / float(len(lstLabels))

        # normalize the confusion matrix to the sum of row-counts
        aCrossVoteNorm = (aCrossVote.swapaxes(0,1) / aCrossVote.sum(axis=1)).swapaxes(0,1)

        if bDoAsymetryCompensation:
            print "Asymetry compensation:"
            print zip(weight_label, weight), len(weight)
        #print dctCrossVote
        print iAccurateVote, fAccuracy
        print aCrossVote
        print aCrossVoteNorm
        print aCrossVote.sum(axis=1)
        print [lstLabels.count(x) for x in sorted(self.dctClassLabels.values())]

        self._exportCrossValidation(aCrossVote,
                                    os.path.join(self.getPath('data'), 'cross-validation.tsv'))
        self._exportCrossValidation(aCrossVoteNorm,
                                    os.path.join(self.getPath('data'), 'cross-validation-normalized.tsv'))

        oModel = svm.svm_model(oSvmProblem, oSvmParam)
        oModel.save(os.path.join(self.getPath('data'), 'all_features_CVoptimized.sparse.model'))


    def _exportCrossValidation(self, aData, strFilename):
        lstNames = [self.dctClassNames[x] for x in sorted(unique(self.dctClassLabels.values()))]
        oTable = newTable(lstNames, rowLabels=lstNames, data=aData)
        exportTable(oTable, strFilename, fieldDelimiter="\t", stringDelimiter="")


    def test(self):
        from rpy import r

        lstPattern = []
        lstLabels = []
        for strClassName, lstSamples in self.dctFeatureData.iteritems():
            iClassLabel = self.dctClassLabels[strClassName]
            for aSample in lstSamples:
                lstLabels.append(iClassLabel)
                lstPattern.append(self.oClassifier.normalize(aSample))

        aPattern = numpy.asarray(lstPattern)
        oCluster = r.kmeans(aPattern, len(self.dctClassLabels), nstart=25)

        print oCluster
        print zip(lstLabels, oCluster['cluster'])

        oPca = r.prcomp(aPattern, scale=True)
        print oPca


class CommonClassPredictor(ClassPredictor, CommonMixin):

    def __init__(self, **options):
        super(CommonClassPredictor, self).__init__(**options)
        #self.initCommon()



class ObjectTeacherBase(object):

    DEFAULT_ARFF_FILENAME = 'all_features.arff'

    def __init__(self, clsLearner):
        self.dctFeatureData = {}
        self.dctClassNames = {}
        self.dctClassLabels = {}
        self.lstFeatureNames = None
        self.clsLearner = clsLearner
        self.dctHexColors = {}


    def writeFile(self, strFilename, clsWriter=None, lstFeatureNames=None):

        if clsWriter is None:
            clsWriter = self.clsLearner.clsWriter
        if lstFeatureNames is None:
            lstFeatureNames = self.lstFeatureNames
        writer = clsWriter(strFilename, lstFeatureNames, self.dctClassLabels)
        writer.writeAllFeatureData(self.dctFeatureData)
        writer.close()


    def loadArffData(self, strFilename):
        oReader = ArffReader(strFilename)
        self.dctFeatureData = oReader.dctFeatureData
        self.dctClassNames = oReader.dctClassNames
        self.dctClassLabels = oReader.dctClassLabels
        self.lstFeatureNames = oReader.lstFeatureNames
        self.dctHexColors = oReader.dctHexColors
        print self.dctClassLabels
        print self.dctClassNames
        print self.dctFeatureData.keys()
        #oReader.close()

    def writeArffData(self, strFilename):
        oWriter = ArffWriter(strFilename,
                             self.lstFeatureNames,
                             self.dctClassLabels,
                             dctHexColors=self.dctHexColors)
        oWriter.writeAllFeatureData(self.dctFeatureData)
        oWriter.close()


    def loadSVMModel(self, strModelFilename, strRangeFilename):
        pass



    def writeShelve(self, strFilename):
        oShelve = shelve.open(strFilename, flag="c")
        oShelve["class_names"] = self.dctClassNames
        for strClassName, lstFeature in self.dctFeatureData.iteritems():
            oShelve[strClassName] = lstFeature
        oShelve.close()


    def cross_validation(self,
                         strTrainingFilename,
                         strTestingFilename,
                         strConfusionFilename,
                         lstFeatureNames=None,
                         iFold=5):
        if lstFeatureNames is None:
            lstFeatureNames = self.lstFeatureNames

        logging.info("\n *** Cross Validation Testing ***\n")
        logging.info("   * Learner: '%s'" % self.clsLearner.__name__)
        logging.info("   * Folds:", iFold)
        logging.info("   * Files: '%s', '%s'" % (strTrainingFilename,
                                                 strTestingFilename))
        logging.info("   * Features: count %d, %s" % (len(lstFeatureNames),
                                                      lstFeatureNames))
        logging.info("   * Objects: %d" % sum([len(x)
                                               for x in self.dctFeatureData.values()]))
        logging.info("")
        self.clsLearner.cross_validation(strTrainingFilename,
                                         strTestingFilename,
                                         strConfusionFilename,
                                         self.dctFeatureData,
                                         lstFeatureNames,
                                         n_fold=iFold,
                                         dctClassLabels=self.dctClassLabels,
                                         dctClassNames=self.dctClassNames)

    def check(self, bDoFilter=False):

        dctCheck = {}
        for iClassLabel in self.dctFeatureData:
            lstClassFeatures = self.dctFeatureData[iClassLabel]
            lstRemoveFeatures = []
            for dctFeatureValues in lstClassFeatures:
                for strFeatureName, fFeatureValue in dctFeatureValues.iteritems():
                    #print name, value, str(value).isdigit()
                    if str(fFeatureValue) in ["nan", "inf", "-inf"]:
                        if not dctFeatureValues in lstRemoveFeatures:
                            lstRemoveFeatures.append(dctFeatureValues)
                        iNameIndex = self.lstFeatureNames.index(strFeatureName)
                        if not iNameIndex in checkD:
                            dctCheck[iNameIndex] = {'name': strFeatureName,
                                                    'classes': {}
                                                    }
                        if not iClassLabel in dctCheck[iNameIndex]['classes']:
                            dctCheck[iNameIndex]['classes'][iClassLabel] = 0
                        dctCheck[iNameIndex]['classes'][iClassLabel] += 1

            if bDoFilter and len(lstRemoveFeatures) > 0:
                for remove in removeL:
                    featureLD.remove(remove)

        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(dctCheck)





#------------------------------------------------------------------------------
# main:
#


if __name__ ==  "__main__":

    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(message)s')

    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/exp435_gfp_GalT_2')

    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/exp687_rfp_H2B_Taxol')
    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/FRET_10xMD_Claudia_H2BYFP_3')
    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/H2B_20x_MD_Katja_exp911')
    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/Tub_20x_MD_exp911')
    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/H2b_IBB_MD_20x')
    #oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/GalT_10x_MD_exp835')

#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/PCNA_10x_Plastic_50ms_StoM')
#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/exp435_gfp_GalT')
#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/exp464_gfp_PCNA')
#    oC.importFromArff()
#    oC.crossValidation()

#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/H2b_10x_MD_exp757')
#    oC.importFromArff()
#    oC.crossValidation(c=128.0, g=0.03125)

    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/H2b_20x_MD_exp911_DG')
    oC.importFromArff()
    oC.crossValidation(c=2048.0, g=0.0078125)

#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/GalT_10x_MD_exp835')
#    oC.importFromArff()
#    oC.crossValidation(c=32.0, g=0.0078125)

#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/H2b_10x_MD_exp835_GalT')
#    oC.importFromArff()
#    oC.crossValidation(c=32.0, g=0.03125)

#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/H2b_20x_MD_exp550_DG')
#    oC.importFromArff()
#    oC.crossValidation(c=128.0, g=0.0078125)



#    oC = ClassPredictor(strEnvPath='/Volumes/Data1T/Classifiers/Tub_20x_MD_exp911_DG')
#    oC.importFromArff()
#    oC.crossValidation(c=2048.0, g=0.0001220703125)
