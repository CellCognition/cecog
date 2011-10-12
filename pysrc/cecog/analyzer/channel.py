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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       types, \
       logging, \
       copy

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            FloatProperty,
                            IntProperty,
                            ListProperty,
                            TupleProperty,
                            StringProperty,
                            DictionaryProperty,
                            Property,
                            )
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)
from pdk.attributes import Attribute
from pdk.iterator import unique, flatten
from pdk.map import dict_values
from pdk.errors import NotImplementedMethodError

import numpy

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.analyzer.object import (ImageObject,
                                   ObjectHolder,
                                   )
from cecog.segmentation.strategies import (PrimarySegmentation,
                                          SecondarySegmentation,
                                          )
from cecog import ccore

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class _Channel(PropertyManager):

    NAME = None

    RANK = None

    PROPERTIES = \
        dict(strChannelId =
                 StringProperty(None,
                                is_mandatory=True,
                                doc=''),

             oZSliceOrProjection =
                 Property(1,
                          doc='either the number of the z-slice (starting by 1) '
                              'or the type of Z-projection: "max", "min", "mean"'),

             channelRegistration =
                 TupleProperty(None),
             registration_start = TupleProperty(None),
             new_image_size = TupleProperty(None),

             strChannelColor =
                 StringProperty('#FFFFFF'),
             iMedianRadius =
                 IntProperty(0,
                             doc='strength of median-filtering'),

             strImageOutCompression =
                 StringProperty('80'),
             strPathOutDebug =
                 StringProperty(None),
             bDebugMode =
                 BooleanProperty(False),

             bDoClassification =
                 BooleanProperty(False,
                                 doc=''),
             strClassificationEnv =
                 StringProperty('',
                                doc=''),
             strClassificationModel =
                 StringProperty('',
                                doc=''),
             lstFeatureCategories =
                 ListProperty(None,
                              doc=''),
             dctFeatureParameters =
                 DictionaryProperty(None,
                                    doc=''),
             lstFeatureNames =
                 ListProperty(None,
                              doc=''),
             lstAreaSelection =
                 ListProperty(None,
                              is_mandatory=True),

             dctAreaRendering =
                 DictionaryProperty(None,
                                    doc=''),

             bPostProcessing =
                 BooleanProperty(True,
                                 doc='post-processing: filter objects by size, '
                                     'shape, intensity, etc.'),
             lstPostprocessingFeatureCategories =
                 ListProperty(None,
                              doc=''),
             strPostprocessingConditions =
                 StringProperty('roisize > 50',
                                doc=''),
             bPostProcessDeleteObjects =
                 BooleanProperty(True,
                                 doc=''),

             tplScale =
                TupleProperty(None, doc=''),

             tplCropRegion =
                TupleProperty(None, doc=''),


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
                 FloatProperty('',
                               doc=''),
             fNormalizeMax =
                 FloatProperty('',
                               doc=''),
             fNormalizeRatio =
                 FloatProperty('',
                               doc=''),
             fNormalizeOffset =
                 FloatProperty('',
                               doc=''),
             )

    __attributes__ = [Attribute('_lstZSlices'),
                      Attribute('_oLogger'),
                      Attribute('_dctRegions'),
                      Attribute('meta_image'),
                      Attribute('dctContainers')
                      ]

    def __init__(self, **dctOptions):
        super(_Channel, self).__init__(**dctOptions)
        self._oLogger = logging.getLogger(self.__class__.__name__)
        self.clear()

    def __cmp__(self, oOther):
        return cmp(self.RANK, oOther.RANK)

    def __getstate__(self):
        # FIXME: not very elegant way to prevent logger from getting pickled
        dctState = get_attribute_values(self)
        del dctState['_oLogger']
        return dctState

    def __setstate__(self, state):
        set_attribute_values(self, state)
        # FIXME: restore logger instance
        self._oLogger = logging.getLogger(self.NAME)

    def clear(self):
        self._lstZSlices = []
        self._dctRegions = {}
        self.meta_image = None
        self.dctContainers = {}

    def region_names(self):
        return self._dctRegions.keys()

    def get_region(self, name):
        return self._dctRegions[name]

    def has_region(self, name):
        return name in self._dctRegions

    def get_container(self, name):
        return self.dctContainers[name]

    def purge(self, features=None):
        self.meta_image = None
        self._lstZSlices = []
        for x in self.dctContainers.keys():
            del self.dctContainers[x]

        # purge features
        if not features is None:
            channelFeatures = []
            for featureNames in features.values():
                if not featureNames is None:
                    channelFeatures.extend(featureNames)
            channelFeatures = sorted(unique(channelFeatures))

            # reduce features per region and object to given list
            for regionName in self.region_names():
                region = self.get_region(regionName)
                channelFeatures2 = [x for x in channelFeatures
                                    if region.hasFeatureName(x)]
                for objId in region:
                    try:
                        region[objId].aFeatures = region.getFeaturesByNames(objId, channelFeatures2)
                    except KeyError:
                        pass
                region.setFeatureNames(channelFeatures2)


    def append_zslice(self, meta_image):
        self._lstZSlices.append(meta_image)

    def apply_zselection(self):
        if type(self.oZSliceOrProjection) == types.TupleType:
            method, zbegin, zend, zstep = self.oZSliceOrProjection
            images = [img.image for img in self._lstZSlices][(zbegin-1):zend:zstep]

            if method == "maximum":
                method_const = ccore.ProjectionType.MaxProjection
            elif method == "minimum":
                method_const = ccore.ProjectionType.MinProjection
            elif method == "average":
                method_const = ccore.ProjectionType.MeanProjection

            self._oLogger.debug("* applying %s Z-Projection to stack of %d images..." % (method, len(images)))
            img_proj = ccore.projectImage(images, method_const)


            # overwrite the first MetaImage found with the projected image data
            meta_image = self._lstZSlices[0]
            meta_image.set_image(img_proj)
        else:
            self.oZSliceOrProjection = int(self.oZSliceOrProjection)
            self._oLogger.debug("* selecting z-slice %d..." % self.oZSliceOrProjection)
            meta_image = self._lstZSlices[self.oZSliceOrProjection-1]
            #print meta_image

#        elif type(self.oZSliceOrProjection) == types.IntType:
#            self._oLogger.debug("* selecting z-slice %d..." % self.oZSliceOrProjection)
#            meta_image = self._lstZSlices[self.oZSliceOrProjection-1]
#        else:
#            raise ValueError("Wrong 'oZSliceOrProjection' value '%s' for channel Id '%s'" %\
#                             (self.oZSliceOrProjection, self.strChannelId))

#        if not self.channelRegistration is None:
#            shift = self.channelRegistration.values()[0]
#            w = meta_image.iWidth - shift[0]
#            h = meta_image.iHeight - shift[1]
#            if self.strChannelId in self.channelRegistration:
#                s = (0,0)
#            else:
#                s = shift
#            meta_image.image = ccore.subImage(meta_image.image,
#                                              ccore.Diff2D(*s),
#                                              ccore.Diff2D(w, h))

        self.meta_image = copy.copy(meta_image)


    def apply_binning(self, iFactor):
        self.meta_image.binning(iFactor)

    def apply_segmentation(self):
        raise NotImplementedMethodError()

    def apply_registration(self):
        img_in = self.meta_image.image
        image = ccore.subImage(img_in,
                               ccore.Diff2D(*self.registration_start)-
                               ccore.Diff2D(*self.channelRegistration),
                               ccore.Diff2D(*self.new_image_size))
        self.meta_image.set_image(image)

    def apply_features(self):

        for strKey, oContainer in self.dctContainers.iteritems():

            oObjectHolder = ObjectHolder(strKey)

            if not oContainer is None:

                for strFeatureCategory in self.lstFeatureCategories:
                    #print strFeatureCategory
                    sys.stdout.flush()
                    oContainer.applyFeature(strFeatureCategory)

                # calculate set of haralick features
                # (with differnt distances)
                if 'haralick_categories' in self.dctFeatureParameters:
                    for strHaralickCategory in self.dctFeatureParameters['haralick_categories']:
                        for iHaralickDistance in self.dctFeatureParameters['haralick_distances']:
                            oContainer.haralick_distance = iHaralickDistance
                            oContainer.applyFeature(strHaralickCategory)

                lstValidObjectIds = []
                lstRejectedObjectIds = []

                for iObjectId, oObject in oContainer.getObjects().iteritems():
                    dctFeatures = oObject.getFeatures()

                    bAcceptObject = True

#                    # post-processing
#                    if self.bPostProcessing:
#
#                        if not eval(self.strPostprocessingConditions, dctFeatures):
#                            if self.bPostProcessDeleteObjects:
#                                #del dctObjects[iObjectId]
#                                oContainer.delObject(iObjectId)
#                                bAcceptObject = False
#                            lstRejectedObjectIds.append(iObjectId)
#                        else:
#                            lstValidObjectIds.append(iObjectId)
#                    else:
#                        lstValidObjectIds.append(iObjectId)
#
#                    oContainer.lstValidObjectIds = lstValidObjectIds
#                    oContainer.lstRejectedObjectIds = lstRejectedObjectIds

                    if bAcceptObject:
                        # build a new ImageObject
                        oImageObject = ImageObject(oObject)
                        oImageObject.iId = iObjectId

                        if self.lstFeatureNames is None:
                            self.lstFeatureNames = sorted(dctFeatures.keys())

                        # assign feature values in sorted order as NumPy array
                        oImageObject.aFeatures = \
                            numpy.asarray(dict_values(dctFeatures,
                                                      self.lstFeatureNames))

                        oObjectHolder[iObjectId] = oImageObject

            if not self.lstFeatureNames is None:
                oObjectHolder.setFeatureNames(self.lstFeatureNames)
            self._dctRegions[strKey] = oObjectHolder

    def normalize_image(self):
        img_in = self.meta_image.image
        if self.bFlatfieldCorrection:
            imgBackground = ccore.readImageFloat(self.strBackgroundImagePath)

            img_in = ccore.flatfieldCorrection(img_in, imgBackground, 0.0, True)
            img_out = ccore.linearTransform2(img_in, self.fNormalizeMin, self.fNormalizeMax, 0, 255, 0, 255)
        else:
            if type(img_in) == ccore.UInt16Image:
                img_out = ccore.linearTransform3(img_in, int(self.fNormalizeMin),
                                                 int(self.fNormalizeMax),
                                                 0, 255, 0, 255)
            else:
                img_out = img_in

        self.meta_image.set_image(img_out)


class PrimaryChannel(_Channel):

    NAME = 'Primary'
    PREFIX = 'primary'

    RANK = 1

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
        super(PrimaryChannel, self).__init__(**dctOptions)

    def apply_segmentation(self, oDummy):
        oSegmentation = PrimarySegmentation(strImageOutCompression = self.strImageOutCompression,
                                            strPathOutDebug = self.strPathOutDebug,
                                            bDebugMode = self.bDebugMode,
                                            iMedianRadius = self.iMedianRadius,
                                            bSpeedup = self.bSpeedup,
                                            iLatWindowSize = self.iLatWindowSize,
                                            iLatLimit = self.iLatLimit,
                                            iLatWindowSize2 = self.iLatWindowSize2,
                                            iLatLimit2 = self.iLatLimit2,
                                            bDoShapeWatershed = self.bDoShapeWatershed,
                                            iGaussSizeShape = self.iGaussSizeShape,
                                            iMaximaSizeShape = self.iMaximaSizeShape,
                                            bDoIntensityWatershed = self.bDoIntensityWatershed,
                                            iGaussSizeIntensity = self.iGaussSizeIntensity,
                                            iMaximaSizeIntensity = self.iMaximaSizeIntensity,
                                            iMinMergeSize = self.iMinMergeSize,
                                            bRemoveBorderObjects = self.bRemoveBorderObjects,
                                            bPostProcessing = self.bPostProcessing,
                                            lstPostprocessingFeatureCategories = self.lstPostprocessingFeatureCategories,
                                            strPostprocessingConditions = self.strPostprocessingConditions,
                                            bPostProcessDeleteObjects = self.bPostProcessDeleteObjects,
                                            bFlatfieldCorrection = self.bFlatfieldCorrection,
                                            strImageType = self.strImageType,
                                            strBackgroundImagePath = self.strBackgroundImagePath,
                                            fBackgroundCorrection = self.fBackgroundCorrection,
                                            fNormalizeMin = self.fNormalizeMin,
                                            fNormalizeMax = self.fNormalizeMax,
                                            fNormalizeRatio = self.fNormalizeRatio,
                                            fNormalizeOffset = self.fNormalizeOffset,
                                            tplCropRegion = self.tplCropRegion,
                                            hole_filling = self.hole_filling,
                                            )
        oContainer = oSegmentation(self.meta_image)
        self.dctContainers['primary'] = oContainer


class SecondaryChannel(_Channel):

    NAME = 'Secondary'
    PREFIX = 'secondary'

    RANK = 2

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
                 IntProperty(None,
                             is_mandatory=True,
                             doc=''),

             fPropagateLambda =
               FloatProperty(None, is_mandatory=True),
             iPropagateDeltaWidth =
               IntProperty(None, is_mandatory=True),

             iConstrainedWatershedGaussFilterSize =
               IntProperty(None, is_mandatory=True),

             bPresegmentation =
               BooleanProperty(None, is_mandatory=True),
             iPresegmentationMedianRadius =
               IntProperty(None, is_mandatory=True),
             fPresegmentationAlpha =
               FloatProperty(None, is_mandatory=True),

             bEstimateBackground =
                 BooleanProperty(False),
             iBackgroundMedianRadius =
                 IntProperty(None),
             iBackgroundLatSize =
                 IntProperty(None),
             iBackgroundLatLimit =
                 IntProperty(None),
             )


    __attributes__ = [Attribute('fBackgroundAverage'),
                      Attribute('bSegmentationSuccessful'),
                      ]

    def __init__(self, **dctOptions):
        super(SecondaryChannel, self).__init__(**dctOptions)
        self.fBackgroundAverage = float('NAN')
        self.bSegmentationSuccessful = False

    def apply_segmentation(self, oChannel):
        if 'primary' in oChannel.dctContainers:
            oSegmentation = SecondarySegmentation(strImageOutCompression = self.strImageOutCompression,
                                                  strPathOutDebug = self.strPathOutDebug,
                                                  bDebugMode = self.bDebugMode,
                                                  iMedianRadius = self.iMedianRadius,

                                                  iExpansionSizeExpanded = self.iExpansionSizeExpanded,
                                                  iShrinkingSizeInside = self.iShrinkingSizeInside,
                                                  iExpansionSizeOutside = self.iExpansionSizeOutside,
                                                  iExpansionSeparationSizeOutside = self.iExpansionSeparationSizeOutside,
                                                  iExpansionSizeRim = self.iExpansionSizeRim,
                                                  iShrinkingSizeRim = self.iShrinkingSizeRim,

                                                  fExpansionCostThreshold = self.fExpansionCostThreshold,

                                                  fPropagateLambda = self.fPropagateLambda,
                                                  iPropagateDeltaWidth = self.iPropagateDeltaWidth,

                                                  iConstrainedWatershedGaussFilterSize = self.iConstrainedWatershedGaussFilterSize,

                                                  bPresegmentation = self.bPresegmentation,
                                                  iPresegmentationMedianRadius = self.iPresegmentationMedianRadius,
                                                  fPresegmentationAlpha = self.fPresegmentationAlpha,

                                                  lstAreaSelection = self.lstAreaSelection,
                                                  bFlatfieldCorrection = self.bFlatfieldCorrection,
                                                  strImageType = self.strImageType,
                                                  strBackgroundImagePath = self.strBackgroundImagePath,
                                                  fBackgroundCorrection = self.fBackgroundCorrection,
                                                  fNormalizeMin = self.fNormalizeMin,
                                                  fNormalizeMax = self.fNormalizeMax,
                                                  tplCropRegion = self.tplCropRegion,
                                                  )
            self.dctContainers = oSegmentation(self.meta_image, oChannel.dctContainers['primary'])

            if self.bEstimateBackground:
                self.fBackgroundAverage = oSegmentation.estimateBackground(self.meta_image,
                                                                           self.iBackgroundMedianRadius,
                                                                           self.iBackgroundLatSize,
                                                                           self.iBackgroundLatLimit)
            self.bSegmentationSuccessful = True


class TertiaryChannel(SecondaryChannel):

    NAME = 'Tertiary'
    PREFIX = 'tertiary'

    RANK = 3


#-------------------------------------------------------------------------------
# main:
#

