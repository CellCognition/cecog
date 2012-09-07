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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

#-------------------------------------------------------------------------------
# cecog imports:
#
from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class Region(object):

    def __init__(self, oRoi=None, tplCoords=None):
        if oRoi is not None:
            self.upperLeft = (oRoi.upperLeft.x, oRoi.upperLeft.y)
            self.lowerRight = (oRoi.lowerRight.x, oRoi.lowerRight.y)
        elif tplCoords is not None:
            self.upperLeft = (tplCoords[0], tplCoords[1])
            self.lowerRight = (tplCoords[2], tplCoords[3])
        else:
            self.upperLeft = None
            self.lowerRight = None


class ImageObject(object):

    def __init__(self, oObject=None):
        #self.oRoi = oObject.oRoi
        #self.oCenterAbs2 = oObject.oCenterAbs
        if oObject is not None:
            self.oCenterAbs = (oObject.oCenterAbs.x, oObject.oCenterAbs.y)
            self.oRoi = Region(oRoi=oObject.oRoi)
        else:
            self.oCenterAbs = None
            self.oRoi = None
        self.iLabel = None
        self.dctProb = {}
        self.strClassName = None
        self.strHexColor = None
        self.iId = None
        self.aFeatures = None
        self.crack_contour = None

#    def __copy__(self):
#        oImageObject = ImageObject()
#        oImageObject.oCenterAbs = self.oCenterAbs
#        oImageObject.aChromatinFeatures = copy.copy(self.aChromatinFeatures)
#        oImageObject.aSecondaryFeatures = copy.copy(self.aSecondaryFeatures)
#        oImageObject.iLabel = self.iLabel
#        oImageObject.dctProb = self.dctProb
#        oImageObject.strClassName = self.strClassName
#        oImageObject.strHexColor = self.strHexColor
#        oImageObject.iId = self.iId
#        return oImageObject

    def squaredMagnitude(self, oObj):
        x = float(oObj.oCenterAbs[0] - self.oCenterAbs[0])
        y = float(oObj.oCenterAbs[1] - self.oCenterAbs[1])
        return x*x + y*y


class ObjectHolder(OrderedDict):

    def __init__(self, strName):
        super(ObjectHolder, self).__init__()
        self.strName = strName
        self._lstFeatureNames = []
        self._dctNamesIdx = {}

    def setFeatureNames(self, lstFeatureNames):
        self._lstFeatureNames = lstFeatureNames[:]
        self._dctNamesIdx.clear()
        # build mapping: featureName -> index
        self._dctNamesIdx = dict([(n,i)
                                  for i, n in enumerate(self._lstFeatureNames)])

    def getFeatureNames(self):
        return self._lstFeatureNames[:]

    def hasFeatureName(self, name):
        return name in self._dctNamesIdx

    def getFeaturesByNames(self, obj_id, lstFeatureNames):
        if lstFeatureNames is None:
            lstFeatureNames = self._lstFeatureNames
        aData = \
        numpy.asarray([self[obj_id].aFeatures[self._dctNamesIdx[strFeatureName]]
                       for strFeatureName in lstFeatureNames])
        return aData

#-------------------------------------------------------------------------------
# main:
#

