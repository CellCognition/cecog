"""
Command line tool to segment and classify one single imagecontainer
Usage

>>>cmdtool.py -h

The output is the label image, the classifcation image and a table of the
prediction probabilities.

"""
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import csv
import argparse
import numpy as np
from collections import OrderedDict

from os.path import basename, splitext, join
import six
from six.moves import range
from six.moves import zip

try:
    import cecog
except ImportError:
    sys.path.append(os.pardir)
    import cecog

from cecog import ccore
from cecog import CH_VIRTUAL
from cecog.version import version
from cecog.learning.learning import CommonClassPredictor
from cecog.environment import CecogEnvironment
from cecog.io.imagecontainer import MetaImage
from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel
from cecog.traits.config import ConfigSettings
from cecog.colors import hex2rgb as hexToRgb


class SettingsMapper(object):
    """Map parameters from a ConfigSettings instance to groups to fit
    the API"""

    CHANNEL_CLASSES = (PrimaryChannel, SecondaryChannel, TertiaryChannel)

    FEATURES = {'featurecategory_intensity': ['normbase', 'normbase2'],
                'featurecategory_haralick': ['haralick', 'haralick2'],
                'featurecategory_stat_geom': ['levelset'],
                'featurecategory_granugrey': ['granulometry'],
                'featurecategory_basicshape': ['roisize',
                                               'circularity',
                                               'irregularity',
                                               'irregularity2',
                                               'axes'],
                'featurecategory_convhull': ['convexhull'],
                'featurecategory_distance': ['distance'],
                'featurecategory_moments': ['moments']}

    def __init__(self, configfile):
        self.img_height = None
        self.img_width = None
        self.settings = ConfigSettings()
        self.settings.read(configfile)

    def __call__(self, section, param):
        return self.settings.get(section, param)

    def setImageSize(self, width, height):
        self.img_width = width
        self.img_height = height

    @property
    def img_size(self):
        return self.img_width, self.img_height

    def featureParams(self, ch_name="Primary"):
        f_categories = list()
        f_cat_params = dict()

        # unfortunateley some classes expect empty list and dict
        if ch_name.lower() in CH_VIRTUAL:
            return f_categories, f_cat_params

        for cat, feature in six.iteritems(self.FEATURES):
            featopt = '%s_%s' %(ch_name, cat)
            if self('FeatureExtraction', featopt):
                if "haralick" in cat:
                    try:
                        f_cat_params['haralick_categories'].extend(feature)
                    except KeyError:
                        assert isinstance(feature, list)
                        f_cat_params['haralick_categories'] = feature
                else:
                    f_categories += feature

        if "haralick_categories" in f_cat_params:
            f_cat_params['haralick_distances'] = (1, 2, 4, 8)

        return f_categories, f_cat_params

    def zsliceParams(self, chname):
        self.settings.set_section('ObjectDetection')
        if self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_selection')):
            par = self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_selection_slice'))
        elif self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_projection')):
            method = self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_projection_method'))
            begin = self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_projection_begin'))
            end = self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_projection_end'))
            step = self("ObjectDetection", "%s_%s" %(chname.lower(), 'zslice_projection_step'))
            par = (method, begin, end, step)
        return par

    def registrationShift(self):
        xs = [0]
        ys = [0]

        for prefix in (SecondaryChannel.PREFIX, TertiaryChannel.PREFIX):
            if self('General','process_%s' %prefix):
                reg_x = self('ObjectDetection', '%s_channelregistration_x' %prefix)
                reg_y = self('ObjectDetection', '%s_channelregistration_y' %prefix)
                xs.append(reg_x)
                ys.append(reg_y)

        diff_x = []
        diff_y = []
        for i in range(len(xs)):
            for j in range(i, len(xs)):
                diff_x.append(abs(xs[i]-xs[j]))
                diff_y.append(abs(ys[i]-ys[j]))

        if self('General', 'crop_image'):
            y0 = self('General', 'crop_image_y0')
            y1 = self('General', 'crop_image_y1')
            x0 = self('General', 'crop_image_x0')
            x1 = self('General', 'crop_image_x1')

            self.img_width = x1 - x0
            self.img_height = y1 - y0

        if self.img_height is None or self.img_width is None:
            raise RuntimeError("Images size is not set. Use self.setImageSize(*size)")

        # new image size after registration of all images
        image_size = (self.img_width - max(diff_x),
                      self.img_height - max(diff_y))

        return (max(xs), max(ys)), image_size


    def channelParams(self, chname="Primary", color=None):
        f_cats, f_params = self.featureParams(chname)
        shift, size = self.registrationShift()
        params = {'strChannelId': color,
                  'channelRegistration': (self(
                    'ObjectDetection', '%s_channelregistration_x' %chname),
                                          self(
                    'ObjectDetection', '%s_channelregistration_y' %chname)),
                  'oZSliceOrProjection': self.zsliceParams(chname),
                  'new_image_size': size,
                  'registration_start': shift,
                  'fNormalizeMin': self('ObjectDetection', '%s_normalizemin' %chname),
                  'fNormalizeMax': self('ObjectDetection', '%s_normalizemax' %chname),
                  'lstFeatureCategories': f_cats,
                  'dctFeatureParameters': f_params}
        return params

    def channelRegions(self):
        """Return a dict of channel region pairs according to the classifier."""

        regions = OrderedDict()
        for ch_cls in self.CHANNEL_CLASSES:
            name = ch_cls.NAME
            if not ch_cls.is_virtual():
                region = self( \
                    "Classification", "%s_classification_regionname" %(name))

                # no plugins loaded
                if region not in (None, ""):
                    regions[name] = region
            else:
                regions2 = OrderedDict()
                for ch_cls2 in self.CHANNEL_CLASSES:
                    if ch_cls2.is_virtual():
                        continue
                    name2 =  ch_cls2.NAME
                    if self("Classification", "merge_%s" %name2):
                        regions2[name2] = self("Classification", "%s_%s_region" %(name, name2))
                if regions2:
                    regions[name] = regions2
        return regions


class ImageProcessor(object):

    def __init__(self, mapper, images):
        super(ImageProcessor, self).__init__()
        self.mapper = mapper
        self._channels = OrderedDict()

        self.metaimages = dict()
        for name, image in six.iteritems(images):
            metaimage = MetaImage()
            metaimage.set_image(ccore.readImage(image))
            self.metaimages[name] = [metaimage]

        self.mapper.setImageSize(metaimage.width, metaimage.height)
        self._setupChannels(images)

    def _setupChannels(self, images):
        chdict = dict((c.NAME.lower(), c) for c in self.mapper.CHANNEL_CLASSES)
        regions = self.mapper.channelRegions()

        for cname in six.iterkeys(images):
            cid = self.mapper("ObjectDetection", "%s_channelid" %cname)
            channel = chdict[cname.lower()](
                **self.mapper.channelParams(cname.title(), cid))

            channel.plugin_mgr.init_from_settings(self.mapper.settings)
            for zslice in self.metaimages[cname]:
                channel.append_zslice(zslice)
            self._channels[cname] = channel

    def exportLabelImage(self, ofile, cname):
        channel = self._channels[cname]
        for region in channel.region_names():
            container = channel.containers[region]
            if isinstance(region, tuple):
                region = '-'.join(region)
            lif_name = ofile+"-lables_%s_%s.tif" %(cname.lower(), region)
            container.exportLabelImage(lif_name, "LWZ")

    def exportClassificationImage(self, ofile, cname):
        channel = self._channels[cname]
        for region in channel.region_names():
            container = channel.containers[region]
            if isinstance(region, tuple):
                region = '-'.join(region)
            ofile = ofile+"-classification_%s_%s.tif" %(cname.lower(), region)
            container.exportRGB(ofile, '90')

    def exportTable(self, ofile, classifier):
        ofile = ofile+'.csv'
        classnames = list(classifier.class_names.values())
        fieldnames = ['ObjectId'] + classnames
        with open(ofile, "wb") as fp:
            writer = csv.DictWriter(fp, fieldnames, delimiter=",")
            writer.writeheader()
            for obj, probs in zip(self.objects, self.probs):
                line = {'ObjectId': obj.iId}
                for label, name in six.iteritems(classifier.class_names):
                    line[name] = probs[label]
                writer.writerow(line)

    def process(self):
        """process files: create projection normalize image get objects for
        several channels"""
        channels = list()
        for cname, channel in six.iteritems(self._channels):
            channels.append(channel)
            channel.apply_zselection()
            channel.normalize_image()
            channel.apply_registration()

            if isinstance(channel, PrimaryChannel):
                channel.apply_segmentation()
            elif isinstance(channel, (SecondaryChannel, TertiaryChannel)):
                channel.apply_segmentation(*channels[:])
            channel.apply_features()

    def findObjects(self, classifier):
        """ runs the classifier """
        objects = list()
        probs = list()
        channel = self._channels[classifier.name.title()]

        for region in channel.region_names():
            holder = channel.get_region(region)
            container = channel.containers[region]
            for l, obj in six.iteritems(holder):

                obj.iLabel, prob = classifier.predict(obj.aFeatures,
                                                   holder.feature_names)

                obj.strClassNames = classifier.class_names[obj.iLabel]
                objects.append(obj)
                probs.append(prob)

                # for classification images
                hexcolor = classifier.hexcolors[ \
                    classifier.class_names[obj.iLabel]]
                rgb = ccore.RGBValue(*hexToRgb(hexcolor))
                container.markObjects([l], rgb, False, True)

        self.objects = np.array(objects)
        self.probs = np.array(probs)


class CmdTool(object):

    def __init__(self, configfile, outdir, image1,
                 image2 = None, image3 = None):

        super(CmdTool, self).__init__()
        self.environ = CecogEnvironment(version, redirect=False, debug=False)
        self.mapper = SettingsMapper(configfile)

        self.images = dict()
        names = [cl.NAME for cl in self.mapper.CHANNEL_CLASSES]
        for name, image in zip(names, (image1, image2, image3)):
            if image is not None:
                self.images[name] = image

        self.classifiers = dict()
        self.outdir = outdir
        self._setupClassifier()

    def _setupClassifier(self):
        for name, image in six.iteritems(self.images):
            if image is None:
                continue
            self.classifiers[name] = CommonClassPredictor( \
                clf_dir=self.mapper('Classification',
                                    '%s_classification_envpath'
                                    %name),
                name=name,
                channels=name,
                color_channel=self.mapper("ObjectDetection", "%s_channelid" %name))

            self.classifiers[name].importFromArff()
            self.classifiers[name].loadClassifier()

    def __call__(self):
        imp = ImageProcessor(self.mapper, self.images)
        imp.process()

        for name, imgfile in six.iteritems(self.images):
            print(('processing image %s' %basename(imgfile)))
            classifier = self.classifiers[name]
            ofile = join(self.outdir, str(splitext(basename(imgfile))[0]))
            imp.findObjects(classifier)
            imp.exportLabelImage(ofile, name.title())
            imp.exportClassificationImage(ofile, name.title())
            imp.exportTable(ofile, classifier)

if __name__ == '__main__':

    parser = argparse.ArgumentParser( \
        description=('Run SVM classfier on a single images. Output'
                     'is the label image the classification image and a '
                     'csv file that contains the prediction probabilities'))
    parser.add_argument('-i1', '--image1', dest='image1', required=True,
                        help='image file for primary channel')
    parser.add_argument('-i2', '--image2', dest='image2',
                        help='image file for secondary channel')
    parser.add_argument('-i3', '--image3', dest='image3',
                        help='image file for tertiary channel')
    parser.add_argument("-o", "--outdir", dest="outdir",
                        type=str, required=True,
                        default=None, help="Output directory")
    parser.add_argument("-s", "--settings", dest="configfile",
                        type=str, required=True,
                        help="Path to cellcognition config file")

    args = parser.parse_args()

    cf = CmdTool(args.configfile, args.outdir, args.image1,
                 args.image2, args.image3)
    cf()
