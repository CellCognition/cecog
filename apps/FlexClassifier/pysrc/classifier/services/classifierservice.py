"""
"""

__docformat__ = "epytext"

__author__ = "Michael Held"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"


#------------------------------------------------------------------------------
# standard modules:
#
import logging, \
       os, \
       traceback, \
       random, \
       time, \
       sys
import cPickle as pickle

#------------------------------------------------------------------------------
# extension modules:
#
import numpy

from pyamf import register_class

from mito.learning.learning import BaseLearner
from mito import ccore
from mito.settings import Settings
from mito.analyzer.analyzer import *
from mito.analyzer.celltracker import *
from mito.experiment.plate import *

from pdk.containers.ordereddict import OrderedDict
from pdk.util.imageutils import rgbToHex, hexToRgb
from pdk.util.fileutils import collectFilesByRegex
from pdk.util.iterator import flatten

#------------------------------------------------------------------------------
# classifier modules:
#
from classifier.lib.amf import AmfMixin
from classifier.lib.helpers import hexToFlexColor

#------------------------------------------------------------------------------
# classes:
#

class Classifier(object):

    def __init__(self, name=None, path=None):
        #super(Classifier, self).__init__()
        self.name = name
        self.path = path

        self.dctClassInfos = OrderedDict()
        self.dctFeatureInfos = OrderedDict()
        self.isInitialized = False
        #self._loadInfos()

    def _loadInfos(self):
        print "LOAD"
        if not self.isInitialized:
            self._oLearner = BaseLearner(strEnvPath=self.path)
            try:
                self._oLearner.importFromArff()
            except IOError:
                pass
            else:
                print "import %s" % self.name

                for iLabel in self._oLearner.lstClassLabels:
                    strName = self._oLearner.dctClassNames[iLabel]
                    strHexColor = self._oLearner.dctHexColors[strName]
                    oClass = Class(strName, iLabel,
                                   len(self._oLearner.dctFeatureData[strName]),
                                   hexToFlexColor(strHexColor))
                    oClass.oClassifier = self
                    dctFeatures = {}
                    for iIdx, strFeatureName in enumerate(self._oLearner.lstFeatureNames):
                        dctFeatures[strFeatureName] = list(self._oLearner.dctFeatureData[strName][:,iIdx])
                    oClass.features = dctFeatures
                    self.dctClassInfos[strName] = oClass
                self.isInitialized = True

                for strFeatureName in self._oLearner.lstFeatureNames:
                    self.dctFeatureInfos[strFeatureName] = Feature(strFeatureName)

    @property
    def classes(self):
        self._loadInfos()
        return self.dctClassInfos.values()

    @property
    def classInfos(self):
        self._loadInfos()
        logging.debug("classes: %s" % len(self.dctClassInfos.values()))
        return self.dctClassInfos.values()

    @property
    def featureInfos(self):
        self._loadInfos()
        logging.debug("features: %s" % len(self.dctFeatureInfos.values()))
        return self.dctFeatureInfos.values()

    def getSamples(self, className):
        self._loadInfos()
        strPathSamples = os.path.join(self._oLearner.dctEnvPaths['samples'],
                                      className)
        #print len(self._oLearner.lstFeatureNames), len()
        dctImagePairs = OrderedDict()
        for strName, oMatch in collectFilesByRegex(strPathSamples, '(?P<prefix>.+?)__(?P<type>(img)|(msk)).+?', ['.png', '.jpg']):
            strPrefix = oMatch.group('prefix')
            strType = oMatch.group('type')
            if not strPrefix in dctImagePairs:
                dctImagePairs[strPrefix] = {}
            dctImagePairs[strPrefix][strType] = strName

        lstResults = []
        iIdx = 0
        for dctPair in dctImagePairs.values():
            #oContainer = ccore.SingleObjectContainer(dctPair['img'], dctPair['msk'])
            #strCoords = ",".join(map(str,flatten(oContainer.getCrackCoordinates(1))))
            #print dctPair['img'], dctPair['msk']
            #dctFeatures = {}
            #for iF, strFeatureName in enumerate(self._oLearner.lstFeatureNames):
            #    dctFeatures[strFeatureName] = self._oLearner.dctFeatureData[className][iIdx][iF]
            oSample = Sample(dctPair['img'])
            lstResults.append(oSample)
            iIdx += 1
            #break
        return lstResults

    def getFeatureData(self, featureNames):
        self._loadInfos()
        lstFeatureData = []
        if len(featureNames) == 1:
            strFeatureName = featureNames[0]
            for strClassName, oClass in self.dctClassInfos.iteritems():
                aY, aX = numpy.histogram(oClass.features[strFeatureName], normed=True)
                lstData = [dict(x=fX, y=fY) for fX,fY in zip(aX, aY)]
                lstFeatureData.append(lstData)
        elif len(featureNames) == 2:
            for strClassName, oClass in self.dctClassInfos.iteritems():
                iSize = len(oClass.features.values()[0])
                lstData = [dict([(strFeatureName, oClass.features[strFeatureName][iIdx]) for strFeatureName in featureNames])
                           for iIdx in range(iSize)]
                lstFeatureData.append(lstData)
        #print lstFeatureData
        return lstFeatureData


class Class(object):

    def __init__(self, name=None, label=None, samples=None, color=None):
        self.name = name
        self.label = label
        self.samples = samples
        self.color = color
        self.features = None


class Feature(object):

    def __init__(self, name=None):
        self.name = name


class Sample(object):

    def __init__(self, path=None):
        self.path = path
        self.url = '/site_media'+path
        self.name = path
        self.features = None
        self.coords = None
        #self._get_coords()

    def _get_coords(self):
        path_img = self.path
        path_msk = path_img.replace('__img', '__msk')
        container = ccore.SingleObjectContainer(path_img, path_msk)
        self.coords = ",".join(map(str,
                                   flatten(container.getCrackCoordinates(1))))
        print path_img
        print "  ", self.coords


class ClassifierService(object):

    def __init__(self, path):
        self.strPath = path
        self._dctClassifiers = None
        self._updateClassifiers()

    def _updateClassifiers(self):
        self._dctClassifiers = OrderedDict()
        for strName in os.listdir(self.strPath):
            strPathClassifier = os.path.join(self.strPath, strName)
            if os.path.isdir(strPathClassifier) and strName[0] not in ['.', '_']:
                oClassifier = Classifier(strName, strPathClassifier)
                self._dctClassifiers[strName] = oClassifier

    def getAll(self, update):
        logging.info("getAll, update: %s" % update)
        if update:
            self._updateClassifiers()
        return self._dctClassifiers.values()

    def getClassInfos(self, name):
        logging.info("getClassInfos")
        oClassifier = self._dctClassifiers[name]
        return oClassifier.classInfos

    def getFeatureInfos(self, name):
        logging.info("getFeatureInfos")
        oClassifier = self._dctClassifiers[name]
        return oClassifier.featureInfos

    def getSampleInfos(self, classifierName, className):
        logging.info("getClassSamples %s %s" % (classifierName, className))
        oClassifier = self._dctClassifiers[classifierName]
        return oClassifier.getSamples(className)

    def getFeatureData(self, classifierName, featureNames):
        logging.info("getFeatureData %s %s" % (classifierName, featureNames))
        oClassifier = self._dctClassifiers[classifierName]
        return oClassifier.getFeatureData(featureNames)


#------------------------------------------------------------------------------
#

DOMAIN_NS = 'org.cecog'
META_DATA = ['amf3']
register_class(Classifier, DOMAIN_NS+'.Classifier', metadata=META_DATA, attrs=['name', 'path'])
register_class(Class, DOMAIN_NS+'.Class', metadata=META_DATA, attrs=['name', 'label', 'color', 'samples'])
register_class(Feature, DOMAIN_NS+'.Feature', metadata=META_DATA, attrs=['name'])
register_class(Sample, DOMAIN_NS+'.Sample', metadata=META_DATA, attrs=['name', 'path', 'url', 'features', 'coords'])
