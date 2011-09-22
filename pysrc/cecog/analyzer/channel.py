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
from cecog import ccore
from cecog.plugin.segmentation import (PRIMARY_SEGMENTATION_MANAGER,
                                       SECONDARY_SEGMENTATION_MANAGER,
                                       TERTIARY_SEGMENTATION_MANAGER,
                                       )

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

    SEGMENTATION = None

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

             strImageOutCompression =
                 StringProperty('80'),
             strPathOutDebug =
                 StringProperty(None),


             lstFeatureCategories =
                 ListProperty(None,
                              doc=''),
             dctFeatureParameters =
                 DictionaryProperty(None,
                                    doc=''),
             lstFeatureNames =
                 ListProperty(None,
                              doc=''),


             bFlatfieldCorrection =
                 BooleanProperty(False,
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

        self.meta_image = copy.copy(meta_image)


    def apply_binning(self, iFactor):
        self.meta_image.binning(iFactor)

#    def apply_segmentation(self, channel):
#        raise NotImplementedError()

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
#        if self.bFlatfieldCorrection:
#
#            if self.strImageType == 'UInt16':
#                imgBackground = ccore.readImageUInt16(self.strBackgroundImagePath)
#            else:
#                imgBackground = ccore.readImage(self.strBackgroundImagePath)
#            imgF = ccore.flatfieldCorrection(imgIn, imgBackground, self.fBackgroundCorrection, True)
#            #print imgF.getMinmax()
#            #imgOut = convertImageMinMax(imgF)
#            imgOut = ccore.linearTransform2(imgF, self.fNormalizeMin, self.fNormalizeMax, 0, 255, 0, 255)
#            #print imgOut.getMinmax()
#
#            #if imgOut == ccore.ImageUInt16:
#            #    imgOut = convertImageUInt12(imgOut)
        if type(img_in) == ccore.UInt16Image:
            img_out = ccore.linearTransform3(img_in, int(self.fNormalizeMin),
                                             int(self.fNormalizeMax),
                                             0, 255, 0, 255)
        else:
#            #FIXME:
#            #if not self.fNormalizeMin is None and not self.fNormalizeMax is None:
#            #    imgOut = ccore.linearTransform2(imgIn, int(self.fNormalizeMin), int(self.fNormalizeMax), 0, 255, 0, 255)
#            if not self.fNormalizeRatio is None and not self.fNormalizeOffset is None:
#                imgOut = ccore.linearTransform(imgIn, self.fNormalizeRatio, int(self.fNormalizeOffset))
#            else:
            img_out = img_in

        self.meta_image.set_image(img_out)

    def get_requirement(self, name):
        '''
        Deliver required data for PluginManager to resolve plugin inter-dependencies.
        '''
        return self.dctContainers[name]

    def apply_segmentation(self, *args):
        '''
        Performs the actual segmentation tasks for this channel by calling the defined plugin instances (managed via
        the PluginManger of this channel).
        '''
        self.dctContainers = self.SEGMENTATION.run(self.meta_image, requirements=args)


class PrimaryChannel(_Channel):

    NAME = 'Primary'
    PREFIX = 'primary'

    RANK = 1
    SEGMENTATION = PRIMARY_SEGMENTATION_MANAGER


class SecondaryChannel(_Channel):

    NAME = 'Secondary'
    PREFIX = 'secondary'

    RANK = 2
    SEGMENTATION = SECONDARY_SEGMENTATION_MANAGER


class TertiaryChannel(SecondaryChannel):

    NAME = 'Tertiary'
    PREFIX = 'tertiary'

    RANK = 3
    SEGMENTATION = TERTIARY_SEGMENTATION_MANAGER


#-------------------------------------------------------------------------------
# main:
#

