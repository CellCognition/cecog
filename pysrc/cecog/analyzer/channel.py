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

__all__ = ["PrimaryChannel", "SecondaryChannel", "TertiaryChannel"]

import os
import sys
import glob
import copy
import types
import numpy
import logging

from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            FloatProperty,
                            ListProperty,
                            TupleProperty,
                            StringProperty,
                            DictionaryProperty,
                            Property)

from pdk.attributemanagers import get_attribute_values, set_attribute_values
from pdk.attributes import Attribute
from pdk.iterator import unique
from pdk.map import dict_values

from cecog import ccore
from cecog.io.imagecontainer import MetaImage
from cecog.analyzer.object import ImageObject, ObjectHolder

from cecog.plugin.segmentation import (PRIMARY_SEGMENTATION_MANAGER,
                                       SECONDARY_SEGMENTATION_MANAGER,
                                       TERTIARY_SEGMENTATION_MANAGER)

class Channel(PropertyManager):

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

    def __init__(self, **kw):
        super(Channel, self).__init__(**kw)
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

        # remove crack_contours
        for regionName in self.region_names():
            region = self.get_region(regionName)
            for obj in region.values():
                    obj.crack_contour = None


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

    def apply_registration(self):
        img_in = self.meta_image.image
#        image = ccore.subImage(img_in,
#                               ccore.Diff2D(*self.registration_start)-
#                               ccore.Diff2D(*self.channelRegistration),
#                               ccore.Diff2D(*self.new_image_size))
        ### FIXME
        image = img_in
        self.meta_image.set_image(image)

    def apply_features(self):

        for region_name, container in self.dctContainers.iteritems():
            object_holder = ObjectHolder(region_name)
            if not container is None:
                for strFeatureCategory in self.lstFeatureCategories:
                    #print strFeatureCategory
#                    sys.stdout.flush()
                    container.applyFeature(strFeatureCategory)

                # calculate set of haralick features
                # (with differnt distances)
                if 'haralick_categories' in self.dctFeatureParameters:
                    for strHaralickCategory in self.dctFeatureParameters['haralick_categories']:
                        for iHaralickDistance in self.dctFeatureParameters['haralick_distances']:
                            container.haralick_distance = iHaralickDistance
                            container.applyFeature(strHaralickCategory)

                for obj_id, c_obj in container.getObjects().iteritems():
                    dctFeatures = c_obj.getFeatures()

                        # build a new ImageObject
                    obj = ImageObject(c_obj)
                    obj.iId = obj_id

                    ul = obj.oRoi.upperLeft
                    crack = [(pos[0] + ul[0], pos[1] + ul[1])
                             for pos in
                             container.getCrackCoordinates(obj_id)
                             ]
                    obj.crack_contour = crack

                    if self.lstFeatureNames is None:
                        self.lstFeatureNames = sorted(dctFeatures.keys())

                    # assign feature values in sorted order as NumPy array
                    obj.aFeatures = \
                        numpy.asarray(dict_values(dctFeatures,
                                                  self.lstFeatureNames))
                    object_holder[obj_id] = obj

            if not self.lstFeatureNames is None:
                object_holder.setFeatureNames(self.lstFeatureNames)
            self._dctRegions[region_name] = object_holder

    def _z_slice_image(self, plate_id):
        if not os.path.isdir(str(self.strBackgroundImagePath)):
            raise IOError("No z-slice correction image directory set")

        path = glob.glob(os.path.join(self.strBackgroundImagePath, plate_id+".tiff"))
        path.extend(glob.glob(
                os.path.join(self.strBackgroundImagePath, plate_id+".tif")))

        if len(path) > 1:
            raise IOError("Multiple z-slice flat field corr. images found.\n"
                          "Directory must contain only one file per plate\n"
                          "(%s)" %", ".join(path))
        try:
            # ccore need str not unicode
            bg_image = ccore.readImageFloat(str(path[0]))
        except Exception, e:
            # catching all errors, even files that are no images
            raise IOError(("Z-slice flat field correction image\n"
                           " could not be loaded! (file: %s)"
                           %path[0]))
        return bg_image

    def normalize_image(self, plate_id=None):
        img_in = self.meta_image.image
        if self.bFlatfieldCorrection:
            self._oLogger.debug("* using flat field correction with image from %s" \
                                    % self.strBackgroundImagePath)
            imgBackground = self._z_slice_image(plate_id)

            crop_coordinated = MetaImage.get_crop_coordinates()
            if crop_coordinated is not None:
                self._oLogger.debug("* applying cropping to background image")
                imgBackground = ccore.subImage(imgBackground,
                                               ccore.Diff2D(crop_coordinated[0],
                                                            crop_coordinated[1]),
                                               ccore.Diff2D(crop_coordinated[2],
                                                            crop_coordinated[3]))

            img_in = ccore.flatfieldCorrection(img_in, imgBackground, 0.0, True)
            img_out = ccore.linearTransform2(img_in, self.fNormalizeMin,
                                             self.fNormalizeMax, 0, 255, 0, 255)
        else:
            self._oLogger.debug("* not using flat field correction")
            if type(img_in) == ccore.UInt16Image:
                img_out = ccore.linearTransform3(img_in, int(self.fNormalizeMin),
                                                 int(self.fNormalizeMax),
                                                 0, 255, 0, 255)
            elif type(img_in) == ccore.Image:
                img_out = ccore.linearTransform2(img_in, int(self.fNormalizeMin),
                                                 int(self.fNormalizeMax),
                                                 0, 255, 0, 255)

            else:
                img_out = img_in

        self.meta_image.set_image(img_out)

    def get_requirement(self, name):
        """Deliver required data for PluginManager to resolve plugin
        inter-dependencies.
        """
        return self.dctContainers[name]

    def apply_segmentation(self, *args):
        """Performs the actual segmentation tasks for this channel by calling
        the defined plugin instances (managed via the PluginManger of this
        channel).
        """
        if self.SEGMENTATION.number_loaded_plugins() == 0:
            raise RuntimeError("%s channel has no loaded segmentation plugins!"
                               %self.NAME)
        self.dctContainers = self.SEGMENTATION.run(self.meta_image,
                                                   requirements=args)

# XXX remove prefix in future version just use name
class PrimaryChannel(Channel):

    NAME = 'Primary'
    PREFIX = NAME.lower()

    RANK = 1
    SEGMENTATION = PRIMARY_SEGMENTATION_MANAGER


class SecondaryChannel(Channel):

    NAME = 'Secondary'
    PREFIX = NAME.lower()

    RANK = 2
    SEGMENTATION = SECONDARY_SEGMENTATION_MANAGER


class TertiaryChannel(Channel):

    NAME = 'Tertiary'
    PREFIX = NAME.lower()

    RANK = 3
    SEGMENTATION = TERTIARY_SEGMENTATION_MANAGER
