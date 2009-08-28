"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
              See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.phenes import *

#-------------------------------------------------------------------------------
# cecog imports:
#


#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class PluginWidget(PhenoType):
    pass


class Primary(PluginWidget):

    NAME = 'primary segmentation'

    lat_window_size = Int(0, label='LatWindowSize')
    lat_limit = Int(0, label='LatLimit')
    do_shape_watershed = Boolean(False, label='DoShapeWatershed', tooltip='Hello World!')
    gauss_size_shape = Int(0, label='GaussSizeShape')
    maxima_size_shape = Int(0, label='GaussSizeShape')


    def __call__(self, channels, masks):
        pass


#
#class PrimarySegmentation(_Segmentation):
#
#    NAME = 'PrimarySeg'
#
#    PROPERTIES = \
#        dict(bSpeedup =
#                 BooleanProperty(False,
#                                 doc=''),
#             iLatWindowSize =
#                 IntProperty(None,
#                             doc='size of averaging window for '
#                                 'local adaptive thresholding.'),
#             iLatLimit =
#                 IntProperty(None,
#                             doc='lower threshold for '
#                                 'local adaptive thresholding.'),
#
#             iLatWindowSize2 =
#                 IntProperty(None,
#                             doc='size of averaging window for '
#                                 'local adaptive thresholding.'),
#             iLatLimit2 =
#                 IntProperty(None,
#                             doc='lower threshold for '
#                                 'local adaptive thresholding.'),
#
#             bDoShapeWatershed =
#                 BooleanProperty(True,
#                                 doc='shape-based watershed: '
#                                     'split objects by distance-transformation.'),
#             iGaussSizeShape =
#                 IntProperty(4,
#                             doc=''),
#             iMaximaSizeShape =
#                 IntProperty(12,
#                             doc=''),
#
#             bDoIntensityWatershed =
#                 BooleanProperty(False,
#                                 doc='intensity-based watershed: '
#                                     'split objects by intensity.'),
#             iGaussSizeIntensity =
#                 IntProperty(5,
#                             doc=''),
#             iMaximaSizeIntensity =
#                 IntProperty(11,
#                             doc=''),
#
#             iMinMergeSize = IntProperty(75,
#                                         doc='watershed merge size: '
#                                             'merge all objects below that size'),
#
#             bRemoveBorderObjects =
#                 BooleanProperty(True,
#                                 doc='remove all objects touching the image borders'),
#
#             iEmptyImageMax =
#                 IntProperty(30,
#                             doc=''),
#
#           )
#
#    def __init__(self, **dctOptions):
#        super(PrimarySegmentation, self).__init__(**dctOptions)
#
#    def __call__(self, oMetaImage):
#        _Segmentation.__call__(self, oMetaImage)
#
#        #print "moo123"
#        #imgXY = oMetaImage.imgXY
#        #print type(imgXY), imgXY.getMin(), imgXY.getMax()
#        #oMetaImage.setImageXY(convertImageMinMax(imgXY))
#
#        imgXY = oMetaImage.imgXY
#        #print type(imgXY), imgXY.getMinmax()
#        iWidth, iHeight = oMetaImage.iWidth, oMetaImage.iHeight
#        #print iWidth, iHeight, self.strPathOutDebug
#
#        if self.bSpeedup:
#            imgTmp1 = ccore.Image(iWidth, iHeight)
#            ccore.binImage(imgXY, imgTmp1, 2)
#            iWidth /= 2
#            iHeight /= 2
#            imgTmp2 = ccore.Image(iWidth, iHeight)
#            ccore.scaleImage(imgTmp1, imgTmp2, "no")
#            imgXY = imgTmp2
#
#        #print self.bDebugMode, self.strPathOutDebug
#        if self.bDebugMode:
#            strPathOutDebug = self.strPathOutDebug
#            ccore.writeImage(imgXY,
#                             os.path.join(strPathOutDebug,
#                                          oMetaImage.format("00raw.jpg", bC=True)),
#                             self.strImageOutCompression)
#
#        # FIXME: scan for empty images
#        iMin, iMax = imgXY.getMinmax()
#        if iMax < self.iEmptyImageMax:
#            #print "max", iMax
#            self._oLogger.warning("Empty image found! Max image value %d < 'iEmptyImageMax' %d." %
#                                  (iMax, self.iEmptyImageMax))
#            return None
#
#        imgPrefiltered = ccore.discMedian(imgXY,
#                                          self.iMedianRadius)
#        self._oLogger.debug("         --- median ok")
#
#        #print self.bDebugMode, self.strPathOutDebug
#        if self.bDebugMode:
#            ccore.writeImage(imgPrefiltered,
#                             os.path.join(strPathOutDebug,
#                                          oMetaImage.format("00pre.jpg", bC=True)),
#                             self.strImageOutCompression)
#
#        imgBin = ccore.windowAverageThreshold(imgPrefiltered,
#                                              self.iLatWindowSize,
#                                              self.iLatLimit)
#        self._oLogger.debug("         --- local threshold ok")
#
#        #self._oLogger.debug("         --- local threshold2 %s %s" % (self.iLatWindowSize2, )
#        if not self.iLatWindowSize2 is None and not self.iLatLimit2 is None:
#            imgBin2 = ccore.windowAverageThreshold(imgPrefiltered,
#                                                   self.iLatWindowSize2,
#                                                   self.iLatLimit2)
#            self._oLogger.debug("         --- local threshold2 ok")
#            imgBin = ccore.projectImage([imgBin, imgBin2], ccore.ProjectionType.MaxProjection)
#
#        if self.bDebugMode:
#            strPathOutDebug = self.strPathOutDebug
#            ccore.writeImage(imgBin,
#                             os.path.join(strPathOutDebug,
#                                          oMetaImage.format("01bin.jpg", bC=True)),
#                             self.strImageOutCompression)
#        else:
#            strPathOutDebug = ""
#
#        if self.bDoShapeWatershed:
#            # some weird form of debug prefix
#            # (works only if compiler flag was set)
#
#            strFilePathDebug = os.path.join(strPathOutDebug,
#                                            oMetaImage.format("01wsShape---", bC=True))
#            imgBin = ccore.watershedShape(imgPrefiltered,
#                                          imgBin,
#                                          strFilePathDebug,
#                                          self.iLatWindowSize,
#                                          self.iGaussSizeShape,
#                                          self.iMaximaSizeShape,
#                                          self.iMinMergeSize)
#
#        if self.bDoIntensityWatershed:
#            strFilePathDebug = os.path.join(strPathOutDebug,
#                                            oMetaImage.format("02wsIntensity---", bC=True))
#            imgBin = ccore.watershedIntensity(imgPrefiltered,
#                                              imgBin,
#                                              strFilePathDebug,
#                                              self.iLatWindowSize,
#                                              self.iGaussSizeIntensity,
#                                              self.iMaximaSizeIntensity,
#                                              self.iMinMergeSize)
#
#        self._oLogger.debug("         --- segmentation ok")
#
#        if self.bSpeedup:
#            iWidth, iHeight = oMetaImage.iWidth, oMetaImage.iHeight
#            imgTmpBin = ccore.Image(iWidth, iHeight)
#            ccore.scaleImage(imgBin, imgTmpBin, "no")
#            imgBin = imgTmpBin
#
#            imgXY = oMetaImage.imgXY
#
#        oContainer = ccore.ImageMaskContainer(imgXY,
#                                              imgBin,
#                                              self.bRemoveBorderObjects)
#
#        self._oLogger.debug("         --- container ok")
#
#        # post-processing
#        #print self.bPostProcessing, self.lstPostprocessingFeatureCategories
#        if self.bPostProcessing:
#
#            # extract features
#            for strFeature in self.lstPostprocessingFeatureCategories:
#                oContainer.applyFeature(strFeature)
#            dctObjects = oContainer.getObjects()
#
#            lstGoodObjectIds = []
#            lstRejectedObjectIds = []
#
#            for iObjectId in dctObjects.keys()[:]:
#                dctObjectFeatures = dctObjects[iObjectId].getFeatures()
#                if not eval(self.strPostprocessingConditions, dctObjectFeatures):
#                    if self.bPostProcessDeleteObjects:
#                        del dctObjects[iObjectId]
#                        oContainer.delObject(iObjectId)
#                    lstRejectedObjectIds.append(iObjectId)
#                else:
#                    lstGoodObjectIds.append(iObjectId)
#        else:
#            lstGoodObjectIds = oContainer.getObjects().keys()
#            lstRejectedObjectIds = []
#
#        oContainer.lstGoodObjectIds = lstGoodObjectIds
#        oContainer.lstRejectedObjectIds = lstRejectedObjectIds
#
#        if self.bDebugMode:
#            oContainer.markObjects(ccore.RGBValue(0,255,0), False, False)
#            #oContainer.markObjects(lstGoodObjectIds, ccore.RGBValue(0,255,0), False, False)
#            #oContainer.markObjects(lstRejectedObjectIds, ccore.RGBValue(255,0,0), False, False)
#            oContainer.exportRGB(os.path.join(strPathOutDebug,
#                                              oMetaImage.format("03Contour.jpg", bC=True)),
#                                 self.strImageOutCompression)
#
#            # reset the container RGB
#            oContainer.eraseRGB()
#            oContainer.combineExtraRGB([7],[1])
#        return oContainer

#-------------------------------------------------------------------------------
# main:
#

