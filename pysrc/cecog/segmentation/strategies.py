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
from pdk.datetimeutils import StopWatch
from pdk.ordereddict import OrderedDict
#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog import ccore
from cecog.gui.guitraits import (BooleanTrait,
                                 IntTrait,
                                 FloatTrait,
                                 )
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

def stopwatch(name=None):
    def wrap(func):
        def new_func(*args, **options):
            func_name = func.__name__
            s = StopWatch()
            logger = logging.getLogger(name)
            logger.debug('Start: %s' % func_name)
            result = func(*args, **options)
            logger.debug('Finish: %s, %s' % (func_name, s))
            return result
        return new_func
    return wrap

#-------------------------------------------------------------------------------
# classes:
#

class PluginManager(object):

    PREFIX = 'plugin'

    def __init__(self, name, section):
        self.name = name
        self.section = section
        self._plugins = OrderedDict()
        self._instances = OrderedDict()

    def init_from_settings(self, settings):
        plugin_params = {}
        self._instances.clear()
        for option_name in settings.options(self.section):
            items = option_name.split('__')
            if len(items) > 3 and items[0] == self.PREFIX and items[1] == self.name:
                plugin_cls_name = items[2]
                plugin_name = items[3]
                params = items[4:]
                plugin_params.setdefault(plugin_name, []).append((plugin_cls_name, (option_name, params)))

        for plugin_name in plugin_params:
            plugin_cls_name, param_info = plugin_params[plugin_name]
            plugin_cls = self._plugins[plugin_cls_name]
            trait_name_template = self._get_trait_name_template(plugin_name)
            param_manager = \
                ParamManager.from_settings(plugin_cls, trait_name_template, settings, self.section, param_info)
            instance = plugin_cls(plugin_name, param_manager)
            self._instances[plugin_name] = instance

    def add_instance(self, plugin_cls_name, settings):
        if not plugin_cls_name in self._plugins:
            raise ValueError("Plugin '%s' not registered for '%s'." % (plugin_cls_name, self.name))

        plugin_cls = self._plugins[plugin_cls_name]
        plugin_name = self._get_plugin_name(plugin_cls)
        trait_name_template = self._get_trait_name_template(plugin_name)
        param_manager = ParamManager(plugin_cls, trait_name_template, settings, self.section)
        instance = plugin_cls(plugin_name, param_manager)
        self._instances[plugin_name] = instance
        return plugin_name

    def remove_instance(self, plugin_name, settings):
        if not plugin_name in self._instances:
            raise ValueError("Plugin instance '%s' not found for '%s'." % (plugin_name, self.name))

        del self._instances[plugin_name]

    def _get_plugin_name(self, plugin_cls):
        plugin_name = plugin_cls.NAME
        cnt = 0
        while plugin_name + str(cnt) in self._instances:
            cnt += 1
        return plugin_name + str(cnt)

    def _get_trait_name_template(self, plugin_name):
        return '__'.join([self.PREFIX, self.name, plugin_name, '%s', '%s'])

    def register_plugin(self, plugin_cls):
        self._plugins[plugin_cls.NAME] = plugin_cls

    #def unregister_plugin(self, name):
    #    del self._plugins[name]

    def run(self, *args, **options):
        results = OrderedDict()
        for instance in self._instances:
            results[instance.name] = instance.run(*args, **options)
        return results


class ParamManager(object):

    GROUP_NAME = 'plugin'

    def __init__(self, plugin_cls, trait_name_template, settings, section):
        self._settings = settings
        self._section = section
        self._lookup = {}
        for param_name, trait in plugin_cls.PARAMS:
            trait_name = trait_name_template % (plugin_cls.NAME, param_name)
            self._lookup[param_name] = trait_name
            settings.register_trait(section, self.GROUP_NAME, trait_name, trait)

    def __del__(self):
        for trait_name in self._lookup.itervalues():
            self._settings.unregister_trait(self._section, self.GROUP_NAME, trait_name)

    def has_param(self, param_name):
        return param_name in self._lookup

    @classmethod
    def from_settings(cls, plugin_cls, trait_name_template, settings, section, param_info):
        """
        register all traits for the given params to the settings manager
        """
        instance = cls(plugin_cls, trait_name_template, settings, section)
        for param_name, trait_name in param_info:
            if instance.has_param(param_name):
                self[param_name] = settings.get_value(section, trait_name)
            else:
                raise ValueError("Parameter '%s' not specified." % param_name)
        return instance

    def __getitem__(self, param_name):
        return self._settings.get(self._section, self._lookup[param_name])

    def __setitem__(self, param_name, value):
        return self._settings.set(self._section, self._lookup[param_name], value)


class _Plugin(object):

    PARAMS = []
    NAME = None

    def __init__(self, name, param_manager):
        self.name = name
        self._param_manager = param_manager

    @property
    def params(self):
        return self._param_manager

    def run(self):
        pass


class _SegmentationPlugin(_Plugin):

    COLOR = '#FFFFFF'
    REQUIRES = None

    def run(self, meta_image, channel=None):
        if not self.REQUIRES is None:
            required_container = channel.dctContainers[self.REQUIRES]
            result_container = self._run(meta_image, required_container)
        else:
            result_container =  self._run(meta_image)
        return result_container


class SegmentationPluginPrimary(_SegmentationPlugin):

    NAME = 'primary'
    COLOR = '#FF0000'

    REQUIRES = None

    PARAMS = [('medianradius', IntTrait(2, 0, 1000, label='Median radius')),
              ('latwindowsize', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit', IntTrait(1, 0, 255, label='Min. contrast')),
              ('lat2', BooleanTrait(False, label='Local adaptive threshold 2')),
              ('latwindowsize2', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit2', IntTrait(1, 0, 255, label='Min. contrast')),
              ('shapewatershed', BooleanTrait(False, label='Split & merge by shape')),
              ('shapewatershed_gausssize', IntTrait(1, 0, 10000, label='Gauss radius')),
              ('shapewatershed_maximasize', IntTrait(1, 0, 10000, label='Min. seed distance')),
              ('shapewatershed_minmergesize', IntTrait(1, 0, 10000, label='Object size threshold')),
              ('intensitywatershed', BooleanTrait(False, label='Split & merge by intensity')),
              ('intensitywatershed_gausssize', IntTrait(1, 0, 10000, label='Gauss radius')),
              ('intensitywatershed_maximasize', IntTrait(1, 0, 10000, label='Min. seed distance')),
              ('intensitywatershed_minmergesize', IntTrait(1, 0, 10000, label='Object size threshold')),
              ('postprocessing', BooleanTrait(False, label='Object filter')),
              ('postprocessing_roisize_min', IntTrait(-1, -1, 10000, label='Min. object size')),
              ('postprocessing_roisize_max', IntTrait(-1, -1, 10000, label='Max. object size')),
              ('postprocessing_intensity_min', IntTrait(-1, -1, 10000, label='Min. average intensity')),
              ('postprocessing_intensity_max', IntTrait(-1, -1, 10000, label='Max. average intensity')),
              ('removeborderobjects', BooleanTrait(True, label='Remove border objects')),
              ('holefilling', BooleanTrait(True, label='Fill holes')),
              ]

    @stopwatch('test')
    def prefilter(self, img_in, radius):
        img_out = ccore.disc_median(img_in, radius)
        return img_out

    @stopwatch
    def threshold(self, img_in, size, limit):
        img_out = ccore.window_average_threshold(img_in, size, limit)
        return img_out

    @stopwatch
    def correct_segmetation(self, img_in, img_bin, border, gauss_size, max_dist, min_merge_size, kind='shape'):
        if kind == 'shape':
            f = ccore.segmentation_correction_shape
        else:
            f = ccore.segmentation_correction_intensity
        return f(img_in, img_bin, border, gauss_size, max_dist, min_merge_size)

    @stopwatch
    def postprocessing(self, container, is_active, feature_categories, conditions, delete_objects):
        if is_active:
            # extract features
            for strFeature in feature_categories:
                container.applyFeature(strFeature)
            dctObjects = container.getObjects()

            lstGoodObjectIds = []
            lstRejectedObjectIds = []

            for iObjectId in dctObjects.keys()[:]:
                dctObjectFeatures = dctObjects[iObjectId].getFeatures()
                if not eval(conditions, dctObjectFeatures):
                    if delete_objects:
                        del dctObjects[iObjectId]
                        container.delObject(iObjectId)
                    lstRejectedObjectIds.append(iObjectId)
                else:
                    lstGoodObjectIds.append(iObjectId)
        else:
            lstGoodObjectIds = container.getObjects().keys()
            lstRejectedObjectIds = []

        container.lstGoodObjectIds = lstGoodObjectIds
        container.lstRejectedObjectIds = lstRejectedObjectIds

    @stopwatch
    def _run(self, meta_image):
        image = meta_image.image

        img_prefiltered = self.prefilter(image, self.params['median_radius'])
        img_bin = self.threshold(img_prefiltered, self.params['latwindowsize'], self.params['latlimit'])

        if self.parmas['hole_filling']:
            ccore.fill_holes(img_bin, False)

        if self.params['lat2']:
            img_bin2 = self.thresold(img_prefiltered, self.params['latwindowsize2'], self.params['latlimit2'])
            img_bin = ccore.projectImage([img_bin, img_bin2], ccore.ProjectionType.MaxProjection)

        if self.parmas['shapewatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['latwindowsize'],
                                               self.params['shapewatershed_gausssize'],
                                               self.params['shapewatershed_maximasize'],
                                               self.params['shapewatershed_minmergesize'],
                                               kind='shape')

        if self.parmas['intensitywatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['latwindowsize'],
                                               self.params['intensitywatershed_gausssize'],
                                               self.params['intensitywatershed_maximasize'],
                                               self.params['intensitywatershed_minmergesize'],
                                               kind='intensity')

        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])

        self.postprocessing(container,
                            self.params['postprocessing'],
                            self.params['moo'],
                            self.params['moo'],
                            True)

        return container


class SegmentationPluginExpanded(_SegmentationPlugin):

    NAME = 'expanded'
    COLOR = '#00FFFF'

    REQUIRES = 'primary'

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ]

    @stopwatch
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0:
            nr_objects = container.img_labels.getMinmax()[1]+1
            img_labels = ccore.seeded_region_expansion(image,
                                                       container.img_labels,
                                                       ccore.SrgType.KeepContours,
                                                       nr_objects,
                                                       0,
                                                       self.params['expansion_size'],
                                                       0)
        else:
            img_labels = container.img_labels

        return ccore.ImageMaskContainer(image, img_labels, False, True)


class SegmentationPluginInside(_SegmentationPlugin):

    NAME = 'inside'
    COLOR = '#FFFF00'

    REQUIRES = 'primary'

    PARAMS = [('shrinking_size', IntTrait(0, 0, 4000, label='Shrinking size')),
              ]

    @stopwatch
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['shrinking_size'] > 0:
            nr_objects = container.img_labels.getMinmax()[1]+1
            img_labels = ccore.seeded_region_shrinking(image,
                                                       container.img_labels,
                                                       nr_objects,
                                                       self.params['shrinking_size'])
        else:
            img_labels = container.img_labels

        return ccore.ImageMaskContainer(image, img_labels, False, True)


class SegmentationPluginOutside(_SegmentationPlugin):

    NAME = 'outside'
    COLOR = '#00FF00'

    REQUIRES = 'primary'

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ('separation_size', IntTrait(0, 0, 4000, label='Separation size')),
              ]

    @stopwatch
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0 and self.params['expansion_size'] > self.params['separation_size']:
            nr_objects = container.img_labels.getMinmax()[1]+1
            img_labels = ccore.seeded_region_expansion(image,
                                                       container.img_labels,
                                                       ccore.SrgType.KeepContours,
                                                       nr_objects,
                                                       0,
                                                       self.params['expansion_size'],
                                                       self.params['separation_size'])
            img_labels = ccore.substractImages(img_labels, container.img_labels)
            return ccore.ImageMaskContainer(image, img_labels, False, True)
        else:
            raise ValueError("Parameters are not valid. Requirements: 'expansion_size' > 0 and "
                             "'expansion_size' > 'separation_size'")


class SegmentationPluginRim(_SegmentationPlugin):

    NAME = 'rim'
    COLOR = '#FF00FF'

    REQUIRES = 'primary'

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ('shrinking_size', IntTrait(0, 0, 4000, label='Shrinking size')),
              ]

    @stopwatch
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0 or self.params['shrinking_size'] > 0:

            nr_objects = container.img_labels.getMinmax()[1]+1
            if self.params['shrinking_size'] > 0:
                img_labelsA = ccore.seeded_region_shrinking(image,
                                                            container.img_labels,
                                                            nr_objects,
                                                            self.params['shrinking_size'])
            else:
                img_labelsA = container.img_labels

            if self.params['expansion_size'] > 0:
                img_labelsB = ccore.seeded_region_expansion(image,
                                                            container.img_labels,
                                                            ccore.SrgType.KeepContours,
                                                            nr_objects,
                                                            0,
                                                            self.params['expansion_size'],
                                                            0)
            else:
                img_labelsB = container.img_labels
            img_labels = ccore.substractImages(img_labelsB, img_labelsA)
            return ccore.ImageMaskContainer(image, img_labels, False, True)
        else:
            raise ValueError("Parameters are not valid. Requirements: 'expansion_size' > 0 and/or "
                             "'shrinking_size' > 0")


class SegmentationPluginPropagate(_SegmentationPlugin):

    NAME = 'propagate'
    COLOR = '#FFFF99'

    REQUIRES = 'primary'

    PARAMS = [('presegmentation_median_radius', IntTrait(1, 0, 100, label='Median radius')),
              ('presegmentation_alpha', FloatTrait(1.0, 0, 4000, label='Otsu factor', digits=2)),
              ('lambda', FloatTrait(0.05, 0, 4000, label='Lambda', digits=2)),
              ('delta_width', IntTrait(1, 1, 4, label='Delta width')),
              ]

    @stopwatch
    def _run(self, meta_image, container):
        image = meta_image.image

        img_prefiltered = ccore.disc_median(image, self.params['presegmentation_median_radius'])
        t = int(ccore.get_otsu_threshold(img_prefiltered) * self.params['presegmentation_alpha'])
        img_bin = ccore.threshold_image(img_prefiltered, t)
        img_labels = ccore.segmentation_propagate(img_prefiltered, img_bin,
                                                  container.img_labels,
                                                  self.params['lambda'],
                                                  self.params['delta_width'])
        return ccore.ImageMaskContainer(image, img_labels, False, True)


class SegmentationPluginConstrainedWatershed(_SegmentationPlugin):

    NAME = 'constrained_watershed'
    COLOR = '#FF99FF'

    REQUIRES = 'primary'

    PARAMS = [('gauss_filter_size', IntTrait(2, 1, 4, label='Gauss filter size')),
              ]

    @stopwatch
    def _run(self, meta_image, container):
        image = meta_image.image
        img_labels = self._constrained_watershed(image, container.img_labels,
                                                 filter_size=self.params['gauss_filter_size'])
        return ccore.ImageMaskContainer(image, img_labels, False, True)

    def _constrained_watershed(self, img_in, img_labels, filter_size=2):

        maxlabel = img_labels.getMinmax()[1]
        img_bin = ccore.threshold(img_labels, 1, maxlabel, 0, 255)

        # internal marker
        img_ero = ccore.erode(img_bin, 3, 8)
        img_internal_marker = ccore.anchoredSkeleton(img_bin, img_ero)

        # external marker
        img_inv = ccore.linearRangeMapping(img_bin, 255, 0, 0, 255)
        img_voronoi = ccore.watershed(img_inv)
        img_external_marker = ccore.threshold(img_voronoi, 0, 0, 0, 255)

        # full marker image
        img_marker = ccore.supremum(img_internal_marker, img_external_marker)

        # gradient image
        img_filtered = ccore.gaussianFilter(img_in, filter_size)
        img_grad = ccore.morphoGradient(img_filtered, 1, 8)

        # Watershed result: 0 is WSL, 1 is Background, all other values correspond to labels.
        img_grad_watershed = ccore.constrainedWatershed(img_grad, img_marker)

        # we first get the regions
        maxreslab = img_grad_watershed.getMinmax()[1]
        img_bin2 = ccore.threshold(img_grad_watershed, 2, maxreslab, 0, 255)

        img_temp = ccore.copyImageIf(img_labels, img_bin2)
        img_out = ccore.relabelImage(img_bin2, img_temp)

        return img_out

