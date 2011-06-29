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
import numpy

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

    __attributes__ = [Attribute('_logger')]

    def __init__(self, **dctOptions):
        super(_Segmentation, self).__init__(**dctOptions)
        self._logger = logging.getLogger(self.__class__.__name__)

    def estimateBackground(self, metaImage, medianRadius, latWindowSize, latLimit):
        self._logger.debug("         --- estimate background")
        image = metaImage.image

        img_prefiltered = ccore.discMedian(image, medianRadius)
        imgBin = ccore.windowAverageThreshold(img_prefiltered,
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
        stopwatch_total = StopWatch()
        stopwatch = StopWatch()

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


        img_prefiltered = ccore.disc_median(image,
                                            self.iMedianRadius)
        self._logger.debug("         --- median ok, %s" %
                            stopwatch.current_interval())

        stopwatch.reset()
        #print self.bDebugMode, self.strPathOutDebug
#        if self.bDebugMode:
#            ccore.writeImage(img_prefiltered,
#                             os.path.join(strPathOutDebug,
#                                          meta_image.format("00pre.jpg", bC=True)),
#                             self.strImageOutCompression)

        imgBin = ccore.window_average_threshold(img_prefiltered,
                                                self.iLatWindowSize,
                                                self.iLatLimit)
        self._logger.debug("         --- local threshold ok, %s" %
                            stopwatch.current_interval())

        if self.hole_filling:
            ccore.fill_holes(imgBin, False)

        stopwatch.reset()
        #self._logger.debug("         --- local threshold2 %s %s" % (self.iLatWindowSize2, )
        if not self.iLatWindowSize2 is None and not self.iLatLimit2 is None:
            imgBin2 = ccore.window_average_threshold(img_prefiltered,
                                                     self.iLatWindowSize2,
                                                     self.iLatLimit2)
            imgBin = ccore.projectImage([imgBin, imgBin2], ccore.ProjectionType.MaxProjection)
            self._logger.debug("         --- local threshold2 ok, %s" %
                                stopwatch.current_interval())

        stopwatch.reset()
#        if self.bDebugMode:
#            strPathOutDebug = self.strPathOutDebug
#            ccore.writeImage(imgBin,
#                             os.path.join(strPathOutDebug,
#                                          meta_image.format("01bin.jpg", bC=True)),
#                             self.strImageOutCompression)
#        else:
#            strPathOutDebug = ""

        if self.bDoShapeWatershed:
            imgBin = ccore.segmentation_correction_shape(img_prefiltered,
                                                         imgBin,
                                                         self.iLatWindowSize,
                                                         self.iGaussSizeShape,
                                                         self.iMaximaSizeShape,
                                                         self.iMinMergeSize)

        if self.bDoIntensityWatershed:
            imgBin = ccore.segmentation_correction_intensity(img_prefiltered,
                                                             imgBin,
                                                             self.iLatWindowSize,
                                                             self.iGaussSizeIntensity,
                                                             self.iMaximaSizeIntensity,
                                                             self.iMinMergeSize)

        self._logger.debug("         --- segmentation ok, %s" %
                            stopwatch.current_interval())

        stopwatch.reset()
        if self.bSpeedup:
            width, height = meta_image.width, meta_image.height
            imgTmpBin = ccore.Image(width, height)
            ccore.scaleImage(imgBin, imgTmpBin, "no")
            imgBin = imgTmpBin

            image = meta_image.image

        container = ccore.ImageMaskContainer(image,
                                             imgBin,
                                             self.bRemoveBorderObjects)

        self._logger.debug("         --- container ok, %s" %
                            stopwatch.current_interval())

        stopwatch.reset()
        # post-processing
        #print self.bPostProcessing, self.lstPostprocessingFeatureCategories
        if self.bPostProcessing:

            # extract features
            for strFeature in self.lstPostprocessingFeatureCategories:
                container.applyFeature(strFeature)
            dctObjects = container.getObjects()

            lstGoodObjectIds = []
            lstRejectedObjectIds = []

            for iObjectId in dctObjects.keys()[:]:
                dctObjectFeatures = dctObjects[iObjectId].getFeatures()
                if not eval(self.strPostprocessingConditions, dctObjectFeatures):
                    if self.bPostProcessDeleteObjects:
                        del dctObjects[iObjectId]
                        container.delObject(iObjectId)
                    lstRejectedObjectIds.append(iObjectId)
                else:
                    lstGoodObjectIds.append(iObjectId)
            self._logger.debug("         --- post-processing ok, %s" %
                                stopwatch.current_interval())
        else:
            lstGoodObjectIds = container.getObjects().keys()
            lstRejectedObjectIds = []

        container.lstGoodObjectIds = lstGoodObjectIds
        container.lstRejectedObjectIds = lstRejectedObjectIds

#        if self.bDebugMode:
#            container.markObjects(ccore.RGBValue(0,255,0), False, False)
#            #container.markObjects(lstGoodObjectIds, ccore.RGBValue(0,255,0), False, False)
#            #container.markObjects(lstRejectedObjectIds, ccore.RGBValue(255,0,0), False, False)
#            container.exportRGB(os.path.join(strPathOutDebug,
#                                              meta_image.format("03Contour.jpg", bC=True)),
#                                 self.strImageOutCompression)
#
#            # reset the container RGB
#            container.eraseRGB()
#            container.combineExtraRGB([7],[1])
        self._logger.debug("         total time: %s" %
                            stopwatch_total.current_interval())
        return container


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

           fPropagateLambda =
               FloatProperty(None, is_mandatory=True),
           iPropagateDeltaWidth =
               IntProperty(None, is_mandatory=True),

           bPresegmentation =
               BooleanProperty(None, is_mandatory=True),
           iPresegmentationMedianRadius =
               IntProperty(None, is_mandatory=True),
           fPresegmentationAlpha =
               FloatProperty(None, is_mandatory=True),

           lstAreaSelection =
               ListProperty(None, is_mandatory=True),
           )

    def __init__(self, **dctOptions):
        super(SecondarySegmentation, self).__init__(**dctOptions)

    def __call__(self, meta_image, container):
        stopwatch_total = StopWatch()
        stopwatch = StopWatch()
        image, width, height = meta_image.image, meta_image.width, meta_image.height
        containers = {}
        iLabelNumber = container.img_labels.getMinmax()[1]+1
        img_prefiltered = image

        # expanded - in case expansion size == 0 original regions are taken
        if 'expanded' in self.lstAreaSelection:
            stopwatch.reset()
            if self.iExpansionSizeExpanded > 0:
                imgLabelsOut = ccore.seeded_region_expansion(img_prefiltered,
                                                             container.img_labels,
                                                             ccore.SrgType.KeepContours,
                                                             iLabelNumber,
                                                             self.fExpansionCostThreshold,
                                                             self.iExpansionSizeExpanded,
                                                             0
                                                             )
            else:
                imgLabelsOut = container.img_labels
            containers['expanded'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False, True)
            self._logger.debug("         --- expanded region ok, %s" %
                               stopwatch.current_interval())

        # inside - in case shrinking size == 0 original regions are taken
        if 'inside' in self.lstAreaSelection:
            stopwatch.reset()
            if self.iShrinkingSizeInside > 0:
                imgLabelsOut = ccore.seeded_region_shrinking(img_prefiltered,
                                                             container.img_labels,
                                                             iLabelNumber,
                                                             self.iShrinkingSizeInside
                                                             )
            else:
                imgLabelsOut = container.img_labels
            containers['inside'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False, True)
            self._logger.debug("         --- inside region ok, %s" %
                               stopwatch.current_interval())

        # outside - expansion size > 0 AND expansion > separation size needed,
        # otherwise area is 0
        if ('outside' in self.lstAreaSelection
             and self.iExpansionSizeOutside > 0
             and self.iExpansionSizeOutside > self.iExpansionSeparationSizeOutside):
            stopwatch.reset()
            imgLabelsOut = ccore.seeded_region_expansion(img_prefiltered,
                                                         container.img_labels,
                                                         ccore.SrgType.KeepContours,
                                                         iLabelNumber,
                                                         self.fExpansionCostThreshold,
                                                         self.iExpansionSizeOutside,
                                                         self.iExpansionSeparationSizeOutside,
                                                         )
            imgLabelsOut = ccore.substractImages(imgLabelsOut, container.img_labels)
            containers['outside'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False, True)
            self._logger.debug("         --- outside region ok, %s" %
                               stopwatch.current_interval())

        # rim - one value > 0 needed, otherwise area is 0
        if ('rim' in self.lstAreaSelection and
            (self.iExpansionSizeRim > 0 or self.iShrinkingSizeRim > 0)):
            stopwatch.reset()
            if self.iShrinkingSizeRim > 0:
                imgLabelsOutA = ccore.seeded_region_shrinking(img_prefiltered,
                                                              container.img_labels,
                                                              iLabelNumber,
                                                              self.iShrinkingSizeRim
                                                              )
            else:
                imgLabelsOutA = container.img_labels
            if self.iExpansionSizeRim > 0:
                imgLabelsOutB = ccore.seeded_region_expansion(img_prefiltered,
                                                              container.img_labels,
                                                              ccore.SrgType.KeepContours,
                                                              iLabelNumber,
                                                              self.fExpansionCostThreshold,
                                                              self.iExpansionSizeRim,
                                                              0
                                                              )
            else:
                imgLabelsOutB = container.img_labels
            imgLabelsOut = ccore.substractImages(imgLabelsOutB, imgLabelsOutA)
            containers['rim'] =\
                ccore.ImageMaskContainer(image, imgLabelsOut, False, True)
            self._logger.debug("         --- rim region ok, %s" %
                               stopwatch.current_interval())

        if ('propagate' in self.lstAreaSelection):
            stopwatch.reset()

            if self.iPresegmentationMedianRadius > 0:
                img_prefiltered = ccore.disc_median(image,
                                                    self.iPresegmentationMedianRadius)

            t = int(ccore.get_otsu_threshold(img_prefiltered) *
                    self.fPresegmentationAlpha)
            img_binary = ccore.threshold_image(img_prefiltered, t)

            #self._logger.debug("         --- pre-segmentation ok, %s" %
            #                    stopwatch.current_interval())

            labels_out = ccore.segmentation_propagate(img_prefiltered, img_binary,
                                                      container.img_labels,
                                                      self.fPropagateLambda,
                                                      self.iPropagateDeltaWidth)
            containers['propagate'] =\
                ccore.ImageMaskContainer(image, labels_out, False, True)
            self._logger.debug("         --- propagate region ok, %s" %
                               stopwatch.current_interval())

        if ('ws' in self.lstAreaSelection):
            labels_out = self.constrainedWatershedApproach(image,
                                                           container.img_labels)

            dctContainers['ws'] =\
                ccore.ImageMaskContainer(image, labels_out, False)
            self._logger.debug("         --- watershed based container ok, %s",
                               stopwatch.current_interval())


        self._logger.debug("         total time: %s" %
                            stopwatch_total.current_interval())
        return containers

    def constrainedWatershedApproach(self, imgIn, imgLabel):

        minlabel, maxlabel = imgLabel.getMinmax()
        imgThresh = ccore.threshold(imgLabel, 1, maxlabel, 0, 255)

        # internal marker
        imgEro = ccore.erode(imgThresh, 3, 8)
        imgInternalMarker = ccore.anchoredSkeleton(imgThresh, imgEro)
        #self.writeImageTitle(imgInternalMarker, 'SKELETON_MARKER')
        #imgInternalMarker = ccore.erode(imgThresh, 3, 8)

        # external marker
        imgInv = ccore.linearRangeMapping(imgThresh, 255, 0, 0, 255)
        imgVoronoi = ccore.watershed(imgInv)
        imgExternalMarker = ccore.threshold(imgVoronoi, 0, 0, 0, 255)

        # full marker image
        imgMarker = ccore.supremum(imgInternalMarker, imgExternalMarker)

        # gradient image
        #imgConv = ccore.conversionTo8Bit(imgIn, 2**15, 2**15 + 4096, 0, 255)
        imgFiltered = ccore.gaussianFilter(imgIn, 2)
        imgGrad = ccore.morphoGradient(imgFiltered, 1, 8)

        # Watershed result: 0 is WSL, 1 is Background, all other values correspond to labels.
        imgGradWatershed = ccore.constrainedWatershed(imgGrad, imgMarker)

        # we first get the regions
        minreslab, maxreslab = imgGradWatershed.getMinmax()
        imgBinSegmentationRes = ccore.threshold(imgGradWatershed, 2, maxreslab, 0, 255)

        imgTemp = ccore.copyImageIf(imgLabel, imgBinSegmentationRes)
        imgRes = ccore.relabelImage(imgBinSegmentationRes, imgTemp)

        return imgRes

