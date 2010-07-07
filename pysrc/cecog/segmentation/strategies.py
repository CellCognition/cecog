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

    def estimateBackground(self, metaImage, medianRadius, latWindowSize, latLimit):
        self._oLogger.debug("         --- estimate background")
        image = metaImage.image

        imgPrefiltered = ccore.discMedian(image, medianRadius)
        imgBin = ccore.windowAverageThreshold(imgPrefiltered,
                                              latWindowSize,
                                              latLimit)
#        if self.bDebugMode:
#            ccore.writeImage(imgBin,
#                             os.path.join(self.strPathOutDebug,
#                                          metaImage.format("background.jpg", bC=True)),
#                             self.strImageOutCompression)

        imgLabels = ccore.ImageInt16(image.width, image.height)
        iCount = ccore.labelImage(imgBin, imgLabels, True, 0)
        dctAvg = ccore.findAverage(image, imgLabels, iCount)
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

             hole_filling =
                 BooleanProperty(False),
           )

    def __init__(self, **dctOptions):
        super(PrimarySegmentation, self).__init__(**dctOptions)

    def __call__(self, meta_image):
        stopwatch1 = StopWatch()

        #print "moo123"
        #image = meta_image.image
        #print type(image), image.getMinmax()
        #meta_image.setImageXY(convertImageMinMax(image))

        image = meta_image.image
        #print type(image), image.getMinmax()
        width, height = meta_image.width, meta_image.height
        #print width, height, self.strPathOutDebug

        if self.bSpeedup:
            imgTmp1 = ccore.Image(width, height)
            ccore.binImage(image, imgTmp1, 2)
            width /= 2
            height /= 2
            imgTmp2 = ccore.Image(width, height)
            ccore.scaleImage(imgTmp1, imgTmp2, "no")
            image = imgTmp2

#        if self.bDebugMode:
#            strPathOutDebug = self.strPathOutDebug
#            ccore.writeImage(image,
#                             os.path.join(strPathOutDebug,
#                                          meta_image.format("00raw.jpg", bC=True)),
#                             self.strImageOutCompression)


        imgPrefiltered = ccore.discMedian(image,
                                          self.iMedianRadius)
        self._oLogger.debug("         --- median ok, %s" % stopwatch1.current_interval())

        stopwatch2 = StopWatch()
        #print self.bDebugMode, self.strPathOutDebug
#        if self.bDebugMode:
#            ccore.writeImage(imgPrefiltered,
#                             os.path.join(strPathOutDebug,
#                                          meta_image.format("00pre.jpg", bC=True)),
#                             self.strImageOutCompression)

        imgBin = ccore.windowAverageThreshold(imgPrefiltered,
                                              self.iLatWindowSize,
                                              self.iLatLimit)
        self._oLogger.debug("         --- local threshold ok, %s" % stopwatch2.current_interval())

        if self.hole_filling:
            ccore.holeFilling(imgBin, False)

        stopwatch3 = StopWatch()
        #self._oLogger.debug("         --- local threshold2 %s %s" % (self.iLatWindowSize2, )
        if not self.iLatWindowSize2 is None and not self.iLatLimit2 is None:
            imgBin2 = ccore.windowAverageThreshold(imgPrefiltered,
                                                   self.iLatWindowSize2,
                                                   self.iLatLimit2)
            imgBin = ccore.projectImage([imgBin, imgBin2], ccore.ProjectionType.MaxProjection)
            self._oLogger.debug("         --- local threshold2 ok, %s" % stopwatch3.current_interval())

        stopwatch4 = StopWatch()
#        if self.bDebugMode:
#            strPathOutDebug = self.strPathOutDebug
#            ccore.writeImage(imgBin,
#                             os.path.join(strPathOutDebug,
#                                          meta_image.format("01bin.jpg", bC=True)),
#                             self.strImageOutCompression)
#        else:
#            strPathOutDebug = ""

        if self.bDoShapeWatershed:
            # some weird form of debug prefix
            # (works only if compiler flag was set)

            strFilePathDebug = ''#os.path.join(strPathOutDebug,
#                                            meta_image.format("01wsShape---", bC=True))
            imgBin = ccore.watershedShape(imgPrefiltered,
                                          imgBin,
                                          strFilePathDebug,
                                          self.iLatWindowSize,
                                          self.iGaussSizeShape,
                                          self.iMaximaSizeShape,
                                          self.iMinMergeSize)

        if self.bDoIntensityWatershed:
            strFilePathDebug = ''#os.path.join(strPathOutDebug,
#                                            meta_image.format("02wsIntensity---", bC=True))
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
            width, height = meta_image.width, meta_image.height
            imgTmpBin = ccore.Image(width, height)
            ccore.scaleImage(imgBin, imgTmpBin, "no")
            imgBin = imgTmpBin

            image = meta_image.image

        oContainer = ccore.ImageMaskContainer(image,
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

#        if self.bDebugMode:
#            oContainer.markObjects(ccore.RGBValue(0,255,0), False, False)
#            #oContainer.markObjects(lstGoodObjectIds, ccore.RGBValue(0,255,0), False, False)
#            #oContainer.markObjects(lstRejectedObjectIds, ccore.RGBValue(255,0,0), False, False)
#            oContainer.exportRGB(os.path.join(strPathOutDebug,
#                                              meta_image.format("03Contour.jpg", bC=True)),
#                                 self.strImageOutCompression)
#
#            # reset the container RGB
#            oContainer.eraseRGB()
#            oContainer.combineExtraRGB([7],[1])
        return oContainer


class SecondarySegmentation(_Segmentation):

    NAME = 'SecondarySeg'

    PROPERTIES = \
      dict(iExpansionSizeExpanded =
               IntProperty(None, is_mandatory=True),

           iShrinkingSizeInside =
               IntProperty(None, is_mandatory=True),

           iExpansionSizeOutside =
               IntProperty(None, is_mandatory=True),
           iExpansionSeparationSizeOutside =
               IntProperty(None, is_mandatory=True),

           iShrinkingSizeRim =
               IntProperty(None, is_mandatory=True),
           iExpansionSizeRim =
               IntProperty(None, is_mandatory=True),

           fExpansionCostThreshold =
               IntProperty(None, is_mandatory=True),
           lstAreaSelection =
               ListProperty(None, is_mandatory=True),
           )

    def __init__(self, **dctOptions):
        super(SecondarySegmentation, self).__init__(**dctOptions)

    def __call__(self, meta_image, oContainer):
        image, width, height = meta_image.image, meta_image.width, meta_image.height
        #imgPrefiltered = ccore.discMedian(image, self.iMedianRadius)
        #self._oLogger.debug("         --- median ok")
        imgPrefiltered = image

#        if self.bDebugMode:
#            ccore.writeImage(image,
#                             os.path.join(self.strPathOutDebug,
#                                          meta_image.format("01raw.jpg", bC=True)),
#                             self.strImageOutCompression)
#            ccore.writeImage(imgPrefiltered,
#                             os.path.join(self.strPathOutDebug,
#                                          meta_image.format("02pre.jpg", bC=True)),
#                             self.strImageOutCompression)

        dctContainers = {}
        iLabelNumber = oContainer.img_labels.getMinmax()[1]+1

        # expanded - in case expansion size == 0 original regions are taken
        if 'expanded' in self.lstAreaSelection:
            if self.iExpansionSizeExpanded > 0:
                imgLabelsOut = ccore.seededRegionExpansion(imgPrefiltered,
                                                           oContainer.img_labels,
                                                           ccore.SrgType.KeepContours,
                                                           iLabelNumber,
                                                           self.fExpansionCostThreshold,
                                                           self.iExpansionSizeExpanded,
                                                           0
                                                           )
                self._oLogger.debug("         --- seededRegionExpansion ok")
            else:
                imgLabelsOut = oContainer.img_labels
            dctContainers['expanded'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False)
            self._oLogger.debug("         --- expanded container ok")

        # inside - in case shrinking size == 0 original regions are taken
        if 'inside' in self.lstAreaSelection:
            if self.iShrinkingSizeInside > 0:
                imgLabelsOut = ccore.seededRegionShrinking(imgPrefiltered,
                                                           oContainer.img_labels,
                                                           iLabelNumber,
                                                           self.iShrinkingSizeInside
                                                           )
                self._oLogger.debug("         --- seededRegionShrinking ok")
            else:
                imgLabelsOut = oContainer.img_labels
            dctContainers['inside'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False)
            self._oLogger.debug("         --- inside container ok")

        # outside - expansion size > 0 AND expansion > separation size needed,
        # otherwise area is 0
        if ('outside' in self.lstAreaSelection
             and self.iExpansionSizeOutside > 0
             and self.iExpansionSizeOutside > self.iExpansionSeparationSizeOutside):
            imgLabelsOut = ccore.seededRegionExpansion(imgPrefiltered,
                                                       oContainer.img_labels,
                                                       ccore.SrgType.KeepContours,
                                                       iLabelNumber,
                                                       self.fExpansionCostThreshold,
                                                       self.iExpansionSizeOutside,
                                                       self.iExpansionSeparationSizeOutside,
                                                       )
            imgLabelsOut = ccore.substractImages(imgLabelsOut, oContainer.img_labels)
            dctContainers['outside'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False)
            self._oLogger.debug("         --- outside container ok")

        # rim - one value > 0 needed, otherwise area is 0
        if ('rim' in self.lstAreaSelection and
            (self.iExpansionSizeRim > 0 or self.iShrinkingSizeRim > 0)):
            if self.iShrinkingSizeRim > 0:
                imgLabelsOutA = ccore.seededRegionShrinking(imgPrefiltered,
                                                            oContainer.img_labels,
                                                            iLabelNumber,
                                                            self.iShrinkingSizeRim
                                                            )
            else:
                imgLabelsOutA = oContainer.img_labels
            if self.iExpansionSizeRim > 0:
                imgLabelsOutB = ccore.seededRegionExpansion(imgPrefiltered,
                                                            oContainer.img_labels,
                                                            ccore.SrgType.KeepContours,
                                                            iLabelNumber,
                                                            self.fExpansionCostThreshold,
                                                            self.iExpansionSizeRim,
                                                            0
                                                            )
            else:
                imgLabelsOutB = oContainer.img_labels
            imgLabelsOut = ccore.substractImages(imgLabelsOutB, imgLabelsOutA)
            dctContainers['rim'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False)
            self._oLogger.debug("         --- rim container ok")

#        if 'expanded' in dctContainers and not 'expanded' in self.lstAreaSelection:
#            del dctContainers['expanded']
#        if 'inside' in dctContainers and not 'inside' in self.lstAreaSelection:
#            del dctContainers['inside']

        return dctContainers


