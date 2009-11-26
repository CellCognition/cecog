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

from svm import svm_model

from pdk.options import Option
from pdk.optionmanagers import OptionManager
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)

#------------------------------------------------------------------------------
# cecog module imports:
#
from cecog.learning.util import Normalizer

#------------------------------------------------------------------------------
# constants:
#


#------------------------------------------------------------------------------
# functions:
#



#------------------------------------------------------------------------------
# classes:
#


class BaseClassifier(OptionManager):

    __attributes__ = ['bProbability',
                      '_oLogger']

    def __init__(self, **options):
        super(BaseClassifier, self).__init__(**options)
        self.bProbability = False
        self._oLogger = logging.getLogger(self.__class__.__name__)

    def __getstate__(self):
        dctState = get_attribute_values(self)
        del dctState['_oLogger']
        return dctState

    def __setstate__(self, state):
        set_attribute_values(self, state)
        self._oLogger = logging.getLogger(self.__class__.__name__)


class LibSvmClassifier(BaseClassifier):

    OPTIONS = {"strSvmPrefix"  : Option("features", doc="Prefix for libSVM .model and .range files."),
               "hasZeroInsert" : Option(True),
               #"clsWriter"   : Option(LibSvmWriter, doc="Writer class to write feature data, e.g. in sparse libSVM format."),
               }

    SVM_MODEL = svm_model
    NORMALIZER = Normalizer

    __attributes__ = ['oSvmModel',
                      'oNormalizer']

    def __init__(self, strDataPath, oLogger, **options):
        super(LibSvmClassifier, self).__init__(**options)

        strModelFilePath = os.path.join(strDataPath, self.getOption('strSvmPrefix') + '.model')
        if os.path.isfile(strModelFilePath):
            self._oLogger.info("Loading libSVM model file '%s'." % strModelFilePath)
            self.oSvmModel = self.SVM_MODEL(strModelFilePath)
        else:
            raise IOError("libSVM model file '%s' not found!" % strModelFilePath)

        strRangeFilePath = os.path.join(strDataPath, self.getOption('strSvmPrefix') + '.range')
        if os.path.isfile(strRangeFilePath):
            self._oLogger.info("Loading libSVM range file '%s'." % strRangeFilePath)
            self.oNormalizer = self.NORMALIZER(strRangeFilePath)
        else:
            raise IOError("libSVM range file '%s' not found!" % strRangeFilePath)

        self.bProbability = True if self.oSvmModel.probability == 1 else False

    def normalize(self, lstSampleFeatureData):
        return self.oNormalizer.scale(lstSampleFeatureData)

    def __call__(self, lstSampleFeatureData):
        lstScaledFeatures = self.normalize(lstSampleFeatureData)
        if self.getOption('hasZeroInsert'):
            lstScaledFeatures = [0] + lstScaledFeatures
        if self.bProbability:
            fLabel, dctProb = self.oSvmModel.predict_probability(lstScaledFeatures)
            iLabel = int(fLabel)
        else:
            fLabel = self.oSvmModel.predict(lstScaledFeatures)
            iLabel = int(fLabel)
            dctProb = {iLabel: 1.0}
        return iLabel, dctProb


#    EASY_PATH = "easy.py"
#
#    @classmethod
#    def cross_validation(cls, training_filename, testing_filename, confusion_filename,
#                         featureD, feature_nameL, n_fold=5,
#                         dctClassLabels=None, dctClassNames=None):
#        fn_train      = training_filename
#        fn_test       = testing_filename
#        fn_confusion  = confusion_filename
#
#
#        dataL = []
#        for strClassName, lstClassFeatures in featureD.iteritems():
#            print strClassName
#            for lstObjectFeatures in lstClassFeatures:
#                dataL.append(cls.WRITER.buildLineStatic(strClassName, lstObjectFeatures, dctClassLabels))
#        # mix the data around!
#        random.seed(time.time())
#        random.shuffle(dataL)
#
#        foldDataL = [[] for i in range(n_fold)]
#        fold_size = int(len(dataL) / n_fold)
#        for fold in range(n_fold):
#            foldDataL[fold].extend(dataL[fold_size*fold:fold_size*(fold+1)])
#
#        accuracyD = {}
#        for fold1 in range(n_fold):
#            print "  ** fold %d of %d **" % (fold1+1, n_fold)
#
#            # compose data
#            writer_training = cls.WRITER(fn_train, feature_nameL, dctClassLabels)
#            writer_testing  = cls.WRITER(fn_test, feature_nameL, dctClassLabels)
#            for fold2 in range(n_fold):
#                if fold2 != fold1:
#                    writer_training.writeLineList(foldDataL[fold2])
#            writer_testing.writeLineList(foldDataL[fold1])
#            writer_training.close()
#            writer_testing.close()
#
#            # train & test svm
#            cmd = "python %s %s %s" % (cls.EASY_PATH, fn_train, fn_test)
#            p = subprocess.Popen(cmd, shell=True, close_fds=False,
#                                 stdout = subprocess.PIPE)
#
#            for line in p.stdout.readlines():
#                print "   * subprocess: ", line.strip()
#            p.stdout.close()
#
#            # evaluate prediction
#            ft = open(fn_test, "r")
#            labelL = []
#            for line in ft:
#                lineL = line.strip().split(" ")
#                iLabel = int(lineL[0])
#                labelL.append(dctClassNames[iLabel])
#            ft.close()
#            ft = open(fn_test+".predict", "r")
#            predictL = []
#            for line in ft:
#                line = line.strip()
#                iLabel = int(line)
#                predictL.append(dctClassNames[iLabel])
#            ft.close()
#            assert len(labelL) == len(predictL)
#            for l,p in zip(labelL, predictL):
#                if not l in accuracyD:
#                    accuracyD[l] = {}
#                if not p in accuracyD[l]:
#                    accuracyD[l][p] = 0
#                accuracyD[l][p] += 1
#
#        #accuracyD = {'1': {'1':10,'21':2}, '21':{'1':4,'21':5}}
#        countD = {}
#        predictSum = 0
#        for l in accuracyD:
#            count = sum(accuracyD[l].values())
#            countD[l] = count
#            for p in accuracyD[l]:
#                accuracyD[l][p] /= float(count)
#            # FIXME! Why can this occur??????
#            if l not in accuracyD[l]:
#                accuracyD[l][l] = 0
#            predictSum += accuracyD[l][l]*count
#        accuracy = predictSum / float(sum(countD.values()))
#
#        print
#        print "  * Average Accuracy: ", accuracy
#        pp = pprint.PrettyPrinter(indent=4)
#        print "  * Class Accuracy:"
#        pp.pprint(accuracyD)
#        print "  * Class Counts:  "
#        pp.pprint(countD)
#
#        # build confusion matrix
#        lstClassIds = sorted(dctClassNames.keys())
#        lstClassNames = [dctClassNames[iKey] for iKey in lstClassIds]
#        oFile = open(fn_confusion, "w")
#        oFile.write("%s\n" % "\t".join([""] + lstClassNames))
#        # FIXME: assume a sorting by class_id is desired
#        for strClassNameOrig in lstClassNames:
#            lstStrs = []
#            for strClassNamePredicted in lstClassNames:
#                if strClassNamePredicted in accuracyD[strClassNameOrig]:
#                    lstStrs.append("%.1f%%" % (accuracyD[strClassNameOrig][strClassNamePredicted] * 100))
#                else:
#                    lstStrs.append("-")
#            oFile.write("%s\n" % "\t".join([strClassNameOrig] + lstStrs))
#        oFile.close()
#
#        return accuracy, accuracyD, countD

