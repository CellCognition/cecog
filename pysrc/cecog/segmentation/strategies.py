"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2009 Michael Held
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

from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            FloatProperty,
                            IntProperty,
                            ListProperty,
                            StringProperty,
                            TupleProperty,
                            Property)
from pdk.attributes import Attribute
from pdk.datetimeutils import StopWatch

#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog import ccore

#-------------------------------------------------------------------------------
# functions:
#

def convertImageUInt12(imgIn, minValue=0, maxValue=4095):
    fConvertRatio  = 255.0 / (maxValue - minValue)
    iConvertOffset = -int(minValue)
    return ccore.linearTransform(imgIn, fConvertRatio, iConvertOffset)

def convertImageMinMax(imgIn, maxValue=255.0):
    minV, maxV = imgIn.getMinmax()
    convertRatio  = maxValue / (maxV - minV)
    convertOffset = -minV
    return ccore.linearTransform(imgIn, convertRatio, convertOffset)

#-------------------------------------------------------------------------------
# classes:
#

class _Segmentation(PropertyManager):

    PROPERTIES = \
        dict(strImageOutCompression =
                 StringProperty(80),
             strPathOutDebug =
                 StringProperty(None),
             bDebugMode =
                 BooleanProperty(False),
             iMedianRadius =
                 IntProperty(None, is_mandatory=True),

             bPostProcessing =
                 BooleanProperty(True,
                                 doc='post-processing: filter objects by size, '
                                     'shape, intensity, etc.'),
             lstPostprocessingFeatureCategories =
                 ListProperty(None,
                              doc='categories of features to '
                                  'extract for post-processing'),
             strPostprocessingConditions =
                 StringProperty('roisize > 50',
                                doc=''),
             bPostProcessDeleteObjects =
                 BooleanProperty(True,
                                 doc=''),

             bFlatfieldCorrection =
                 BooleanProperty(False,
                                 doc=''),
             strImageType =
                 StringProperty('UInt8',
                                doc=''),
             strBackgroundImagePath =
                 StringProperty('',
                                doc=''),
             fBackgroundCorrection =
                 FloatProperty('',
                               doc=''),
             fNormalizeMin =
                 FloatProperty(None,
                               doc=''),
             fNormalizeMax =
                 FloatProperty(None,
                               doc=''),
             fNormalizeRatio =
                 FloatProperty(None,
                               doc=''),
             fNormalizeOffset =
                 FloatProperty(None,
                               doc=''),

             tplCropRegion =
                 TupleProperty(None, doc=''),
             )

    __attributes__ = [Attribute('_oLogger')]

    def __init__(self, **dctOptions):
        super(_Segmentation, self).__init__(**dctOptions)
        self._oLogger = logging.getLogger(self.__class__.__name__)

    def __call__(self, oMetaImage):

        imgIn = oMetaImage.imgXY
        #print type(imgIn)
        if self.bFlatfieldCorrection:

            if self.strImageType == 'UInt16':
                imgBackground = ccore.readImageUInt16(self.strBackgroundImagePath)
            else:
                imgBackground = ccore.readImage(self.strBackgroundImagePath)
            imgF = ccore.flatfieldCorrection(imgIn, imgBackground, self.fBackgroundCorrection, True)
            #print imgF.getMinmax()
            #imgOut = convertImageMinMax(imgF)
            imgOut = ccore.linearTransform2(imgF, self.fNormalizeMin, self.fNormalizeMax, 0, 255, 0, 255)
            #print imgOut.getMinmax()

            #if imgOut == ccore.ImageUInt16:
            #    imgOut = convertImageUInt12(imgOut)

        elif type(imgIn) == ccore.ImageUInt16:
            imgOut = ccore.linearTransform3(imgIn, int(self.fNormalizeMin), int(self.fNormalizeMax), 0, 255, 0, 255)
        else:
            #FIXME:
            #if not self.fNormalizeMin is None and not self.fNormalizeMax is None:
            #    imgOut = ccore.linearTransform2(imgIn, int(self.fNormalizeMin), int(self.fNormalizeMax), 0, 255, 0, 255)
            if not self.fNormalizeRatio is None and not self.fNormalizeOffset is None:
                imgOut = ccore.linearTransform(imgIn, self.fNormalizeRatio, int(self.fNormalizeOffset))
            else:
                imgOut = imgIn

        if not self.tplCropRegion is None:
            x1, y1, x2, y2 = self.tplCropRegion
            imgOut2 = ccore.Image(x2-x1+1, y2-y1+1)
            ccore.copySubImage(imgOut, ccore.Diff2D(x1,y1), ccore.Diff2D(x2+1,y2+1), imgOut2, ccore.Diff2D(0,0))
            imgOut = imgOut2

        oMetaImage.setImageXY(imgOut)
        #print type(oMetaImage.imgXY)


    def estimateBackground(self, metaImage, medianRadius, latWindowSize, latLimit):
        self._oLogger.debug("         --- estimate background")
        imgXY = metaImage.imgXY

        imgPrefiltered = ccore.discMedian(imgXY, medianRadius)
        imgBin = ccore.windowAverageThreshold(imgPrefiltered,
                                              latWindowSize,
                                              latLimit)
        if self.bDebugMode:
            ccore.writeImage(imgBin,
                             os.path.join(self.strPathOutDebug,
                                          metaImage.format("background.jpg", bC=True)),
                             self.strImageOutCompression)

        imgLabels = ccore.ImageInt16(imgXY.width, imgXY.height)
        iCount = ccore.labelImage(imgBin, imgLabels, True, 0)
        dctAvg = ccore.findAverage(imgXY, imgLabels, iCount)
        return dctAvg[0]






class PrimarySegmentation(_Segmentation):

    NAME = 'PrimarySeg'

    PROPERTIES = \
        dict(bSpeedup =
                 BooleanProperty(False,
                                 doc=''),
             iLatWindowSize =
                 IntProperty(None,
                             doc='size of averaging window for '
                                 'local adaptive thresholding.'),
             iLatLimit =
                 IntProperty(None,
                             doc='lower threshold for '
                                 'local adaptive thresholding.'),

             iLatWindowSize2 =
                 IntProperty(None,
                             doc='size of averaging window for '
                                 'local adaptive thresholding.'),
             iLatLimit2 =
                 IntProperty(None,
                             doc='lower threshold for '
                                 'local adaptive thresholding.'),

             bDoShapeWatershed =
                 BooleanProperty(True,
                                 doc='shape-based watershed: '
                                     'split objects by distance-transformation.'),
             iGaussSizeShape =
                 IntProperty(4,
                             doc=''),
             iMaximaSizeShape =
                 IntProperty(12,
                             doc=''),

             bDoIntensityWatershed =
                 BooleanProperty(False,
                                 doc='intensity-based watershed: '
                                     'split objects by intensity.'),
             iGaussSizeIntensity =
                 IntProperty(5,
                             doc=''),
             iMaximaSizeIntensity =
                 IntProperty(11,
                             doc=''),

             iMinMergeSize = IntProperty(75,
                                         doc='watershed merge size: '
                                             'merge all objects below that size'),

             bRemoveBorderObjects =
                 BooleanProperty(True,
                                 doc='remove all objects touching the image borders'),

             iEmptyImageMax =
                 IntProperty(30,
                             doc=''),

           )

    def __init__(self, **dctOptions):
        super(PrimarySegmentation, self).__init__(**dctOptions)

    def __call__(self, oMetaImage):
        stopwatch1 = StopWatch()
        _Segmentation.__call__(self, oMetaImage)

        #print "moo123"
        #imgXY = oMetaImage.imgXY
        #print type(imgXY), imgXY.getMinmax()
        #oMetaImage.setImageXY(convertImageMinMax(imgXY))

        imgXY = oMetaImage.imgXY
        #print type(imgXY), imgXY.getMinmax()
        iWidth, iHeight = oMetaImage.iWidth, oMetaImage.iHeight
        #print iWidth, iHeight, self.strPathOutDebug

        if self.bSpeedup:
            imgTmp1 = ccore.Image(iWidth, iHeight)
            ccore.binImage(imgXY, imgTmp1, 2)
            iWidth /= 2
            iHeight /= 2
            imgTmp2 = ccore.Image(iWidth, iHeight)
            ccore.scaleImage(imgTmp1, imgTmp2, "no")
            imgXY = imgTmp2

        #print self.bDebugMode, self.strPathOutDebug
        if self.bDebugMode:
            strPathOutDebug = self.strPathOutDebug
            ccore.writeImage(imgXY,
                             os.path.join(strPathOutDebug,
                                          oMetaImage.format("00raw.jpg", bC=True)),
                             self.strImageOutCompression)

        # FIXME: scan for empty images
        iMin, iMax = imgXY.getMinmax()
        if iMax < self.iEmptyImageMax:
            #print "max", iMax
            self._oLogger.warning("Empty image found! Max image value %d < 'iEmptyImageMax' %d." %
                                  (iMax, self.iEmptyImageMax))
            return None

        imgPrefiltered = ccore.discMedian(imgXY,
                                          self.iMedianRadius)
        self._oLogger.debug("         --- median ok, %s" % stopwatch1.current_interval())

        stopwatch2 = StopWatch()
        #print self.bDebugMode, self.strPathOutDebug
        if self.bDebugMode:
            ccore.writeImage(imgPrefiltered,
                             os.path.join(strPathOutDebug,
                                          oMetaImage.format("00pre.jpg", bC=True)),
                             self.strImageOutCompression)

        imgBin = ccore.windowAverageThreshold(imgPrefiltered,
                                              self.iLatWindowSize,
                                              self.iLatLimit)
        self._oLogger.debug("         --- local threshold ok, %s" % stopwatch2.current_interval())

        stopwatch3 = StopWatch()
        #self._oLogger.debug("         --- local threshold2 %s %s" % (self.iLatWindowSize2, )
        if not self.iLatWindowSize2 is None and not self.iLatLimit2 is None:
            imgBin2 = ccore.windowAverageThreshold(imgPrefiltered,
                                                   self.iLatWindowSize2,
                                                   self.iLatLimit2)
            imgBin = ccore.projectImage([imgBin, imgBin2], ccore.ProjectionType.MaxProjection)
            self._oLogger.debug("         --- local threshold2 ok, %s" % stopwatch3.current_interval())

        stopwatch4 = StopWatch()
        if self.bDebugMode:
            strPathOutDebug = self.strPathOutDebug
            ccore.writeImage(imgBin,
                             os.path.join(strPathOutDebug,
                                          oMetaImage.format("01bin.jpg", bC=True)),
                             self.strImageOutCompression)
        else:
            strPathOutDebug = ""

        if self.bDoShapeWatershed:
            # some weird form of debug prefix
            # (works only if compiler flag was set)

            strFilePathDebug = os.path.join(strPathOutDebug,
                                            oMetaImage.format("01wsShape---", bC=True))
            imgBin = ccore.watershedShape(imgPrefiltered,
                                          imgBin,
                                          strFilePathDebug,
                                          self.iLatWindowSize,
                                          self.iGaussSizeShape,
                                          self.iMaximaSizeShape,
                                          self.iMinMergeSize)

        if self.bDoIntensityWatershed:
            strFilePathDebug = os.path.join(strPathOutDebug,
                                            oMetaImage.format("02wsIntensity---", bC=True))
            imgBin = ccore.watershedIntensity(imgPrefiltered,
                                              imgBin,
                                              strFilePathDebug,
                                              self.iLatWindowSize,
                                              self.iGaussSizeIntensity,
                                              self.iMaximaSizeIntensity,
                                              self.iMinMergeSize)

        self._oLogger.debug("         --- segmentation ok, %s" % stopwatch4.current_interval())

        stopwatch5 = StopWatch()
        if self.bSpeedup:
            iWidth, iHeight = oMetaImage.iWidth, oMetaImage.iHeight
            imgTmpBin = ccore.Image(iWidth, iHeight)
            ccore.scaleImage(imgBin, imgTmpBin, "no")
            imgBin = imgTmpBin

            imgXY = oMetaImage.imgXY

        oContainer = ccore.ImageMaskContainer(imgXY,
                                              imgBin,
                                              self.bRemoveBorderObjects)

        self._oLogger.debug("         --- container ok, %s" % stopwatch5.current_interval())

        stopwatch6 = StopWatch()
        # post-processing
        #print self.bPostProcessing, self.lstPostprocessingFeatureCategories
        if self.bPostProcessing:

            # extract features
            for strFeature in self.lstPostprocessingFeatureCategories:
                oContainer.applyFeature(strFeature)
            dctObjects = oContainer.getObjects()

            lstGoodObjectIds = []
            lstRejectedObjectIds = []

            for iObjectId in dctObjects.keys()[:]:
                dctObjectFeatures = dctObjects[iObjectId].getFeatures()
                if not eval(self.strPostprocessingConditions, dctObjectFeatures):
                    if self.bPostProcessDeleteObjects:
                        del dctObjects[iObjectId]
                        oContainer.delObject(iObjectId)
                    lstRejectedObjectIds.append(iObjectId)
                else:
                    lstGoodObjectIds.append(iObjectId)
            self._oLogger.debug("         --- post-processing ok, %s" % stopwatch6.current_interval())
        else:
            lstGoodObjectIds = oContainer.getObjects().keys()
            lstRejectedObjectIds = []

        oContainer.lstGoodObjectIds = lstGoodObjectIds
        oContainer.lstRejectedObjectIds = lstRejectedObjectIds

        if self.bDebugMode:
            oContainer.markObjects(ccore.RGBValue(0,255,0), False, False)
            #oContainer.markObjects(lstGoodObjectIds, ccore.RGBValue(0,255,0), False, False)
            #oContainer.markObjects(lstRejectedObjectIds, ccore.RGBValue(255,0,0), False, False)
            oContainer.exportRGB(os.path.join(strPathOutDebug,
                                              oMetaImage.format("03Contour.jpg", bC=True)),
                                 self.strImageOutCompression)

            # reset the container RGB
            oContainer.eraseRGB()
            oContainer.combineExtraRGB([7],[1])
        return oContainer


class SecondarySegmentation(_Segmentation):

    NAME = 'SecondarySeg'

    PROPERTIES = \
      dict(iExpansionSize =
               IntProperty(None, is_mandatory=True),
           iExpansionSeparationSize =
               IntProperty(None, is_mandatory=True),
           iShrinkingSeparationSize =
               IntProperty(None, is_mandatory=True),
           fExpansionCostThreshold =
               IntProperty(None, is_mandatory=True),
           lstAreaSelection =
               ListProperty(None, is_mandatory=True),
           )

    def __init__(self, **dctOptions):
        super(SecondarySegmentation, self).__init__(**dctOptions)

    def __call__(self, oMetaImage, oContainer):
        _Segmentation.__call__(self, oMetaImage)

        imgXY, iWidth, iHeight = oMetaImage.imgXY, oMetaImage.iWidth, oMetaImage.iHeight
        #imgPrefiltered = ccore.discMedian(imgXY, self.iMedianRadius)
        #self._oLogger.debug("         --- median ok")
        imgPrefiltered = imgXY

        if self.bDebugMode:
            ccore.writeImage(imgXY,
                             os.path.join(self.strPathOutDebug,
                                          oMetaImage.format("01raw.jpg", bC=True)),
                             self.strImageOutCompression)
#            ccore.writeImage(imgPrefiltered,
#                             os.path.join(self.strPathOutDebug,
#                                          oMetaImage.format("02pre.jpg", bC=True)),
#                             self.strImageOutCompression)

        dctContainers = {}
        iLabelNumber = oContainer.img_labels.getMinmax()[1]+1

        if ('expanded' in self.lstAreaSelection or
            'outside' in self.lstAreaSelection):
            imgLabelsOutA = ccore.seededRegionExpansion(imgPrefiltered,
                                                        oContainer.img_labels,
                                                        ccore.SrgType.KeepContours,
                                                        iLabelNumber,
                                                        self.fExpansionCostThreshold,
                                                        self.iExpansionSize,
                                                        self.iExpansionSeparationSize
                                                        )
            self._oLogger.debug("         --- seededRegionExpansion ok")
            dctContainers['expanded'] =\
                ccore.ImageMaskContainer(imgXY, imgLabelsOutA, False)
            self._oLogger.debug("         --- expanded container ok")

        if ('inside' in self.lstAreaSelection or
            'rim' in self.lstAreaSelection):
            imgLabelsOutB = ccore.seededRegionShrinking(imgPrefiltered,
                                                        oContainer.img_labels,
                                                        iLabelNumber,
                                                        self.iShrinkingSeparationSize
                                                        )
            self._oLogger.debug("         --- seededRegionShrinking ok")
            dctContainers['inside'] =\
                ccore.ImageMaskContainer(imgXY, imgLabelsOutB, False)
            self._oLogger.debug("         --- inside container ok")

        if 'outside' in self.lstAreaSelection:
            imgLabelsOutC = ccore.substractImages(imgLabelsOutA, oContainer.img_labels)
            dctContainers['outside'] =\
                ccore.ImageMaskContainer(imgXY, imgLabelsOutC, False)
            self._oLogger.debug("         --- outside container ok")

        if 'rim' in self.lstAreaSelection:
            imgLabelsOutD = ccore.seededRegionExpansion(imgPrefiltered,
                                                        imgLabelsOutB,
                                                        ccore.SrgType.KeepContours,
                                                        iLabelNumber,
                                                        self.fExpansionCostThreshold,
                                                        self.iExpansionSize,
                                                        self.iExpansionSeparationSize
                                                        )
            self._oLogger.debug("         --- seededRegionExpansion ok")
            dctContainers['rim'] =\
                ccore.ImageMaskContainer(imgXY, imgLabelsOutD, False)
            self._oLogger.debug("         --- rim container ok")

        if 'expanded' in dctContainers and not 'expanded' in self.lstAreaSelection:
            del dctContainers['expanded']
        if 'inside' in dctContainers and not 'inside' in self.lstAreaSelection:
            del dctContainers['inside']

        return dctContainers


