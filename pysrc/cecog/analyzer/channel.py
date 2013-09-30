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

__all__ = ["PrimaryChannel", "SecondaryChannel", "TertiaryChannel"
           "MergedChannel"]

from os.path import join, isdir
import glob
import copy
import types
import numpy
from collections import OrderedDict

from cecog import ccore
from cecog.colors import Colors
from cecog.io.imagecontainer import MetaImage
from cecog.analyzer.object import ImageObject, ObjectHolder, Orientation

from cecog.util.logger import LoggerObject
from cecog.plugin.segmentation import (PRIMARY_SEGMENTATION_MANAGER,
                                       SECONDARY_SEGMENTATION_MANAGER,
                                       TERTIARY_SEGMENTATION_MANAGER)

class ChannelCore(LoggerObject):

    NAME = None
    _rank = None
    SEGMENTATION = None
    _is_virtual = False

    def __init__(self,
                 strChannelId,
                 # either number of zsclice or projection type
                 oZSliceOrProjection=1,
                 channelRegistration=None,
                 registration_start=None,
                 new_image_size=None,
                 strImageOutCompression="80",
                 strPathOutDebug=None,
                 lstFeatureCategories=None,
                 dctFeatureParameters=None,
                 lstFeatureNames=None,
                 bFlatfieldCorrection=False,
                 strBackgroundImagePath="",
                 fBackgroundCorrection="",
                 fNormalizeMin="",
                 fNormalizeMax="",
                 fNormalizeRatio="",
                 fNormalizeOffset=""):
        super(ChannelCore, self).__init__()

        # remove all the hungarian bullshit as soon as possible!
        self.strChannelId = strChannelId
        # either number of zsclice or projection type
        self.oZSliceOrProjection = oZSliceOrProjection
        self.channelRegistration = channelRegistration
        self.registration_start = registration_start
        self.new_image_size = new_image_size
        self.strImageOutCompression = strImageOutCompression
        self.strPathOutDebug = strPathOutDebug
        self.lstFeatureCategories = lstFeatureCategories
        self.dctFeatureParameters = dctFeatureParameters
        self.lstFeatureNames = lstFeatureNames
        self.bFlatfieldCorrection = bFlatfieldCorrection
        self.strBackgroundImagePath = strBackgroundImagePath
        self.fBackgroundCorrection = fBackgroundCorrection
        self.fNormalizeMin = fNormalizeMin
        self.fNormalizeMax = fNormalizeMax
        self.fNormalizeRatio = fNormalizeRatio
        self.fNormalizeOffset = fNormalizeOffset

        self._zslices = []
        self.containers = {}
        self._regions = {}
        self.meta_image = None
        self._features_calculated = False

    def __cmp__(self, channel):
        return cmp(self._rank, channel._rank)

    @classmethod
    def is_virtual(cls):
        return cls._is_virtual

    def region_names(self):
        return self._regions.keys()

    def get_region(self, name):
        return self._regions[name]

    def has_region(self, name):
        return self._regions.has_key(name)

    def get_container(self, name):
        return self.containers[name]

    def append_zslice(self, meta_image):
        self._zslices.append(meta_image)

    def clear(self):
        self._zslices = []
        self._regions = {}
        self.meta_image = None
        self.containers = {}

class Channel(ChannelCore):

    def __init__(self, *args, **kw):
        super(Channel, self).__init__(*args, **kw)

    def purge(self, features=None):
        self.meta_image = None
        self._zslices = []
        for x in self.containers.keys():
            del self.containers[x]

        # remove crack_contours
        for name in self.region_names():
            region = self.get_region(name)
            for obj in region.values():
                obj.crack_contour = None

        # purge features
        if not features is None:
            channelFeatures = []
            for featureNames in features.values():
                if not featureNames is None:
                    channelFeatures.extend(featureNames)
            channelFeatures = sorted(set(channelFeatures))

            # reduce features per region and object to given list
            for regionName in self.region_names():
                region = self.get_region(regionName)
                channelFeatures2 = [x for x in channelFeatures
                                    if region.hasFeatureName(x)]
                for objId in region:
                    try:
                        region[objId].aFeatures = region.features_by_name(
                            objId, channelFeatures2)
                    except KeyError:
                        pass
                region.feature_names = channelFeatures2

    def apply_zselection(self):
        if type(self.oZSliceOrProjection) == types.TupleType:
            method, zbegin, zend, zstep = self.oZSliceOrProjection
            images = [img.image for img in self._zslices][(zbegin-1):zend:zstep]
            # single images don't carry the dtype
            dtype = img.format.lower()

            if method == "maximum":
                method_const = ccore.ProjectionType.MaxProjection
            elif method == "minimum":
                method_const = ccore.ProjectionType.MinProjection
            elif method == "average":
                method_const = ccore.ProjectionType.MeanProjection

            self.logger.debug("* applying %s Z-Projection to stack of %d images..." % (method, len(images)))
            imgprj = numpy.zeros((images[0].height, images[0].width),
                                 dtype=dtype)
            imgprj = ccore.numpy_to_image(imgprj, copy=True)
            ccore.zproject(imgprj, images, method_const)

            # overwrite the first MetaImage found with the projected image data
            meta_image = self._zslices[0]
            meta_image.set_image(imgprj)
        else:
            self.oZSliceOrProjection = int(self.oZSliceOrProjection)
            self.logger.debug("* selecting z-slice %d..." % self.oZSliceOrProjection)
            meta_image = self._zslices[self.oZSliceOrProjection-1]

        self.meta_image = copy.copy(meta_image)

    def apply_binning(self, iFactor):
        self.meta_image.binning(iFactor)

    def apply_registration(self):
        img_in = self.meta_image.image

        # ccore.subImage checks dimensions
        image = ccore.subImage(img_in,
                               ccore.Diff2D(*self.registration_start)-
                               ccore.Diff2D(*self.channelRegistration),
                               ccore.Diff2D(*self.new_image_size))
        self.meta_image.set_image(image)

    def apply_features(self):
        self._features_calculated = True
        for region_name, container in self.containers.iteritems():
            object_holder = ObjectHolder(region_name)
            if not container is None:
                for strFeatureCategory in self.lstFeatureCategories:
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
                             container.getCrackCoordinates(obj_id)]
                    obj.crack_contour = crack


                    # ORIENTATION TEST: orientation of objects (for tracking) #
                    # at the moment a bit of a hack #
                    # The problem is that orientation cannot be a feature #
                    # but moments need to be chosen to calculate the orientation. #
                    if 'moments' in self.lstFeatureCategories:
                        obj.orientation = Orientation(angle = c_obj.orientation,
                                                      eccentricity = dctFeatures['eccentricity'])

                    # why do wo sort the features according to their names??
                    # does it matter?
                    if self.lstFeatureNames is None:
                        self.lstFeatureNames = sorted(dctFeatures.keys())

                    # assign feature values in sorted order as NumPy array
                    features = (dctFeatures[f] for f in self.lstFeatureNames)
                    obj.aFeatures = numpy.fromiter(features, dtype=float)
                    object_holder[obj_id] = obj
                    # print 'orientation %s (%i, %i): %f (%f deg)' % (obj_id,
                    #                                                 obj.oRoi.upperLeft[0],
                    #                                                 obj.oRoi.upperLeft[1],
                    #                                                 obj.orientation,
                    #                                                 180.0 * obj.orientation / numpy.pi)

            if self.lstFeatureNames is not None:
                object_holder.feature_names = self.lstFeatureNames
            self._regions[region_name] = object_holder


    def _z_slice_image(self, plate_id):
        if not isdir(str(self.strBackgroundImagePath)):
            raise IOError("No z-slice correction image directory set")

        path = glob.glob(join(self.strBackgroundImagePath, plate_id+".tiff"))
        path.extend(glob.glob(
                join(self.strBackgroundImagePath, plate_id+".tif")))

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
            self.logger.debug("* using flat field correction with image from %s"
                              % self.strBackgroundImagePath)
            imgBackground = self._z_slice_image(plate_id)

            crop_coordinated = MetaImage.get_crop_coordinates()
            if crop_coordinated is not None:
                self.logger.debug("* applying cropping to background image")
                imgBackground = ccore.subImage(imgBackground,
                                               ccore.Diff2D(crop_coordinated[0],
                                                            crop_coordinated[1]),
                                               ccore.Diff2D(crop_coordinated[2],
                                                            crop_coordinated[3]))

            img_in = ccore.flatfieldCorrection(img_in, imgBackground, 0.0, True)
            img_out = ccore.linearTransform2(img_in, self.fNormalizeMin,
                                             self.fNormalizeMax, 0, 255, 0, 255)
        else:
            self.logger.debug("* not using flat field correction")
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
        return self.containers[name]

    def apply_segmentation(self, *args):
        """Performs the actual segmentation tasks for this channel by calling
        the defined plugin instances (managed via the PluginManger of this
        channel).
        """
        self.containers = self.SEGMENTATION.run(self.meta_image,
                                                requirements=args)

# XXX remove prefix in future version just use name
class PrimaryChannel(Channel):

    NAME = 'Primary'
    PREFIX = NAME.lower()

    _rank = 1
    SEGMENTATION = PRIMARY_SEGMENTATION_MANAGER

class SecondaryChannel(Channel):

    NAME = 'Secondary'
    PREFIX = NAME.lower()

    _rank = 2
    SEGMENTATION = SECONDARY_SEGMENTATION_MANAGER

class TertiaryChannel(Channel):

    NAME = 'Tertiary'
    PREFIX = NAME.lower()

    _rank = 3
    SEGMENTATION = TERTIARY_SEGMENTATION_MANAGER

# This channel is 'virtual'
class MergedChannel(ChannelCore):
    """
    Virtal or PseudoChannel which is meant to concatenate features of
    other channels. It cannot perform an segmentation or ohter operation
    on images.
    """

    NAME = 'Merged'
    PREFIX = NAME.lower()
    _rank = 4
    SEGMENTATION = None
    _is_virtual = True

    def __init__(self, *args, **kw):
        super(MergedChannel, self).__init__(*args, **kw)
        # defines channels an regions to concatenate
        self._merge_regions = OrderedDict()
        self._channels = None

    @property
    def merge_regions(self):
        return self._merge_regions

    @merge_regions.setter
    def merge_regions(self, regions):
        """Set channels and regions to concatenate."""
        self._merge_regions.update(regions)

    @merge_regions.deleter
    def merged_regions(self):
        del self._merge_regions

    def apply_segmentation(self, channels, master="Primary"):
        self._channels = channels
        self._new_container(master)

    def apply_features(self, *args, **kw):
        """Concatenate features of images objects of different channels"""
        holder = ObjectHolder("-".join(self._merge_regions.values()))
        for cname, region_name in self._merge_regions.iteritems():
            channel = self._channels[cname]
            holder0 = channel.get_region(region_name)
            pfx = "%s_%s" %(cname, region_name)
            feature_names = ["_".join((pfx, f)) for f in holder0.feature_names]
            holder.cat_samples(holder0, feature_names)

        removed = holder.remove_incomplete()
        if len(removed) > 0:
            self.logger.info("Found incomplete samples in merged channel")
            self.logger.info("removed samples: %s" %",".join([str(r) for r in removed]))
        self._regions[self.regkey] = holder
        self.lstFeatureNames = holder.feature_names

    def _new_container(self, master):
        # not sure if it makes a difference to have a master
        # perhaps a method to get an rgb image

        # find the region of the primary channel
        # it does not feel a great piece of code ... 
        available_regions = self._channels[master].containers.keys()
        if 'primary' in available_regions:
            default_region = 'primary'
        elif 'primary' in [x[:len('primary')] for x in available_regions]:
            default_region = filter(lambda x: x[:len('primary')]=='primary', available_regions)[0]
        else:
            default_region = available_regions[0]

        mcnt = self._channels[master].containers[default_region]
        self.containers[self.regkey] = mcnt

    @property
    def regkey(self):
        # tuples are hashable
        return tuple(self._merge_regions.values())

    def meta_images(self, alpha=1.0):
        """Return a list of image, hexcolor, alpha-value tripples, which
        is used for ccore.makeRGBImage method.
        """

        images = list()
        ccolors = dict([(c.strChannelId, False) for c in self._channels.values()])

        for channel in self._channels.values():
            ccolor = channel.strChannelId
            if ccolor is not None and not ccolors[channel.strChannelId]:
                ccolors[channel.strChannelId] = True
                images.append((channel.meta_image.image,
                               Colors.channel_hexcolor(ccolor),
                               alpha))
        return images

    def sub_channels(self):
        for schannel, region in self._merge_regions.iteritems():
            yield self._channels[schannel], region

    # most of the following functions are just dummy implementations to stay
    # combatible to processing channels that do actually perform segmentation
    def purge(self, *args, **kw):
        self._channels = None

    def normalize_image(self, *args, **kw):
        pass

    def apply_zselection(self, *args, **kw):
        pass

    def apply_registration(self, *args, **kw):
        pass

    def apply_binning(self, *args, **kw):
        pass
