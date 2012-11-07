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

#-------------------------------------------------------------------------------
# standard library imports:
#

import os, \
       logging

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from svm import svm_model

from pdk.options import Option
from pdk.optionmanagers import OptionManager
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)

#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog.learning.util import Normalizer

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#



#-------------------------------------------------------------------------------
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
    NAME = 'libSVM'
    METHOD = 'Support Vector Machine'

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

