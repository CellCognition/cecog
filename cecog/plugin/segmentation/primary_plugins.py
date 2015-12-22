"""
primary_plugins.py

Segmentation plugins for the primary channel.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ("LocalAdaptiveThreshold", "GlobalThreshold",
           "Ilastik", "LoadFromFile", "LocalAdaptiveThreshold2",
           "LocalAdaptiveThreshold3", "LocalAdaptiveThreshold4")

import os
import re
import numpy
from cecog import ccore
from cecog.gui.guitraits import BooleanTrait, IntTrait, StringTrait, FloatTrait

from cecog.plugin import stopwatch
from cecog.plugin.segmentation.manager import _SegmentationPlugin


class LocalAdaptiveThreshold(_SegmentationPlugin):

    LABEL = 'Local adaptive threshold w/ split&merge'
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
              ('shapewatershed_gausssize', IntTrait(1, 0, 1000000, label='Gauss radius')),
              ('shapewatershed_maximasize', IntTrait(1, 0, 1000000, label='Min. seed distance')),
              ('shapewatershed_minmergesize', IntTrait(1, 0, 1000000, label='Object size threshold')),
              ('intensitywatershed', BooleanTrait(False, label='Split & merge by intensity')),
              ('intensitywatershed_gausssize', IntTrait(1, 0, 1000000, label='Gauss radius')),
              ('intensitywatershed_maximasize', IntTrait(1, 0, 1000000, label='Min. seed distance')),
              ('intensitywatershed_minmergesize', IntTrait(1, 0, 1000000, label='Object size threshold')),
              ('postprocessing', BooleanTrait(False, label='Object filter')),
              ('postprocessing_roisize_min', IntTrait(-1, -1, 1000000, label='Min. object size')),
              ('postprocessing_roisize_max', IntTrait(-1, -1, 1000000, label='Max. object size')),
              ('postprocessing_intensity_min', IntTrait(-1, -1, 1000000, label='Min. average intensity')),
              ('postprocessing_intensity_max', IntTrait(-1, -1, 1000000, label='Max. average intensity')),
              ('removeborderobjects', BooleanTrait(True, label='Remove border objects')),
              ('holefilling', BooleanTrait(True, label='Fill holes')),
              ]

    # the : at the beginning indicates a QRC link with alias 'plugins/segmentation/local_adaptive_threshold'
    DOC = ':local_adaptive_threshold'

    def render_to_gui(self, panel):
        panel.add_group(None,
                        [('medianradius', (0, 0, 1, 1)),
                         ('latwindowsize', (0, 1, 1, 1)),
                         ('latlimit', (0, 2, 1, 1)),
                         ], link='lat', label='Local adaptive threshold')
        panel.add_group('lat2',
                        [('latwindowsize2', (0, 0, 1, 1)),
                         ('latlimit2', (0, 1, 1, 1)),
                         ])
        panel.add_input('holefilling')
        panel.add_input('removeborderobjects')
        panel.add_group('shapewatershed',
                        [('shapewatershed_gausssize', (0, 0, 1, 1)),
                         ('shapewatershed_maximasize', (0, 1, 1, 1)),
                         ('shapewatershed_minmergesize', (1, 0, 1, 1)),
                         ])
        panel.add_group('postprocessing',
                        [('postprocessing_roisize_min', (0, 0, 1, 1)),
                         ('postprocessing_roisize_max', (0, 1, 1, 1)),
                         ('postprocessing_intensity_min', (1, 0, 1, 1)),
                         ('postprocessing_intensity_max', (1, 1, 1, 1)),
                         ])

    @stopwatch()
    def prefilter(self, img_in, radius=None):
        if radius is None:
            radius = self.params['medianradius']
        img_out = ccore.disc_median(img_in, radius)
        return img_out

    @stopwatch()
    def threshold(self, img_in, size, limit):
        img_out = ccore.window_average_threshold(img_in, size, limit)
        return img_out

    @stopwatch()
    def correct_segmetation(self, img_in, img_bin, border, gauss_size,
                            max_dist, min_merge_size, kind='shape'):
        if kind == 'shape':
            f = ccore.segmentation_correction_shape
        else:
            f = ccore.segmentation_correction_intensity
        return f(img_in, img_bin, border, gauss_size, max_dist, min_merge_size)

    @stopwatch()
    def postprocessing(self, container, is_active, roisize_minmax,
                       intensity_minmax, delete_objects=True):

        valid_ids = container.getObjects().keys()
        rejected_ids = []

        if is_active:
            feature_categories = set()
            conditions = []
            for idx, (roisize, intensity) in enumerate( \
                zip(roisize_minmax, intensity_minmax)):
                cmprt = '>=' if idx == 0 else '<='
                if roisize > -1:
                    feature_categories.add('roisize')
                    conditions.append('roisize %s %d' % (cmprt, roisize))
                if intensity > -1:
                    feature_categories.add('normbase2')
                    conditions.append('n2_avg %s %d' % (cmprt, intensity))

            if len(conditions) > 0:
                conditions_str = ' and '.join(conditions)

                for feature in feature_categories:
                    container.applyFeature(feature)

                valid_ids = []
                rejected_ids = []

                # get a dict copy, because we delete elements from the dict
                objects = container.getObjects()
                for obj_id, obj in objects.iteritems():
                    # eval condition string based on the feature dict (provides values for the features above)
                    if not eval(conditions_str, obj.getFeatures()):
                        if delete_objects:
                            container.delObject(obj_id)
                        rejected_ids.append(obj_id)
                    else:
                        valid_ids.append(obj_id)

        # store valid and rejected object IDs to the container
        container.valid_ids = valid_ids
        container.rejected_ids = rejected_ids

    @stopwatch()
    def _run(self, meta_image):
        image = meta_image.image

        img_prefiltered = self.prefilter(image)
        img_bin1 = self.threshold(img_prefiltered, self.params['latwindowsize'], self.params['latlimit'])

        if self.params['holefilling']:
            ccore.fill_holes(img_bin1, False)

        if self.params['lat2']:
            img_bin2 = self.threshold(img_prefiltered, self.params['latwindowsize2'],
                                      self.params['latlimit2'])

            # replacement for not working ccore.projectImage
            img_bin = numpy.zeros((img_bin2.height, img_bin2.width),
                                 dtype=meta_image.format)
            img_bin = ccore.numpy_to_image(img_bin, copy=True)
            ccore.zproject(img_bin, [img_bin1, img_bin2], ccore.ProjectionType.MaxProjection)
        else:
            img_bin = img_bin1


        if self.params['shapewatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['latwindowsize'],
                                               self.params['shapewatershed_gausssize'],
                                               self.params['shapewatershed_maximasize'],
                                               self.params['shapewatershed_minmergesize'],
                                               kind='shape')
        if self.params['intensitywatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['latwindowsize'],
                                               self.params['intensitywatershed_gausssize'],
                                               self.params['intensitywatershed_maximasize'],
                                               self.params['intensitywatershed_minmergesize'],
                                               kind='intensity')

        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])

        self.postprocessing(
            container, self.params['postprocessing'],
            (self.params['postprocessing_roisize_min'],
             self.params['postprocessing_roisize_max']),
            (self.params['postprocessing_intensity_min'], self.params['postprocessing_intensity_max']))

        return container


class GlobalThreshold(LocalAdaptiveThreshold):

    DOC = ':global_threshold'

    LABEL = 'Gobal threshold w/ split&merge'
    NAME = 'primary_global_threshold'
    COLOR = '#FF0000'
    REQUIRES = None

    PARAMS = [('medianradius', IntTrait(2, 0, 1000, label='Median radius')),
              ('static_threshold', BooleanTrait(True, label='Static threshold')),
              ('threshold', IntTrait(25, 0, 255, label='Threshold')),
              ('shapewatershed', BooleanTrait(False, label='Split & merge by shape')),
              ('shapewatershed_gausssize', IntTrait(1, 0, 1000000, label='Gauss radius')),
              ('shapewatershed_maximasize', IntTrait(1, 0, 1000000, label='Min. seed distance')),
              ('shapewatershed_minmergesize', IntTrait(1, 0, 1000000, label='Object size threshold')),
              ('shapewatershed_rmax', IntTrait(40, 0, 1000000, label='Max. radius')),
              ('postprocessing', BooleanTrait(False, label='Object filter')),
              ('postprocessing_roisize_min', IntTrait(-1, -1, 1000000, label='Min. object size')),
              ('postprocessing_roisize_max', IntTrait(-1, -1, 1000000, label='Max. object size')),
              ('postprocessing_intensity_min', IntTrait(-1, -1, 1000000, label='Min. average intensity')),
              ('postprocessing_intensity_max', IntTrait(-1, -1, 1000000, label='Max. average intensity')),
              ('removeborderobjects', BooleanTrait(True, label='Remove border objects')),
              ('holefilling', BooleanTrait(True, label='Fill holes'))]

    def render_to_gui(self, panel):

        panel.add_group(None,
                        [('medianradius', (0, 0, 1, 1)),
                         ('threshold', (0, 1, 1, 1)),
                         ('static_threshold', (0, 2, 1, 1)),
                         ], link='global_threshold', label='global threshold')

        panel.add_input('holefilling')
        panel.add_input('removeborderobjects')
        panel.add_group('shapewatershed',
                        [('shapewatershed_gausssize', (0, 0, 1, 1)),
                         ('shapewatershed_maximasize', (0, 1, 1, 1)),
                         ('shapewatershed_minmergesize', (1, 0, 1, 1)),
                         ('shapewatershed_rmax', (1, 1, 1, 1))])

        panel.add_group('postprocessing',
                        [('postprocessing_roisize_min', (0, 0, 1, 1)),
                         ('postprocessing_roisize_max', (0, 1, 1, 1)),
                         ('postprocessing_intensity_min', (1, 0, 1, 1)),
                         ('postprocessing_intensity_max', (1, 1, 1, 1))])


    @stopwatch()
    def correct_segmetation(self, img_in, img_bin, border, gauss_size,
                            max_dist, min_merge_size):

        return ccore.segmentation_correction_shape(
            img_in, img_bin, border, gauss_size, max_dist, min_merge_size)

    @stopwatch()
    def threshold(self, image, threshold, static_threshold):

        if static_threshold:
            return ccore.threshold_image(image, threshold)

        ndimage = image.toArray()

        for i in xrange(255): # max unit8 interations
            limage = ccore.threshold_image(image, threshold)
            mask = limage.toArray()
            mu0 = ndimage[mask==0].mean()
            mu1 = ndimage[mask==255].mean()
            thrnew = int(numpy.floor((mu0 + mu1)/2.0))
            if thrnew == threshold:
                break
            else:
                threshold = thrnew

        return limage


    @stopwatch()
    def _run(self, meta_image):
        image = meta_image.image

        img_prefiltered = self.prefilter(image)
        img_bin = self.threshold(img_prefiltered,
                                 self.params['threshold'],
                                 self.params["static_threshold"])

        if self.params['holefilling']:
            ccore.fill_holes(img_bin, False)

        # split and merge
        if self.params['shapewatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['shapewatershed_rmax'],
                                               self.params['shapewatershed_gausssize'],
                                               self.params['shapewatershed_maximasize'],
                                               self.params['shapewatershed_minmergesize'])

        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])

        # filtering object by size and intesity
        self.postprocessing(container, self.params['postprocessing'],
                            (self.params['postprocessing_roisize_min'], self.params['postprocessing_roisize_max']),
                            (self.params['postprocessing_intensity_min'], self.params['postprocessing_intensity_max']))

        return container


class LoadFromFile(LocalAdaptiveThreshold):

    LABEL = 'Load from file'
    NAME = 'primary_from_file'
    COLOR = '#FF00FF'

    REQUIRES = None

    PARAMS = [('segmentation_folder', StringTrait('', 1000, label='Segmentation folder',
                                                 widget_info=StringTrait.STRING_FILE)),
              ('loader_regex',
               StringTrait('^%(plate)s$/^%(pos)s$/.*P%(pos)s_T%(time)05d_C%(channel)s_Z%(zslice)d_S1.tif',
                           1000, label='Regex for loading')),
              ]

    # the : at the beginning indicates a QRC link with alias 'plugins/segmentation/local_adaptive_threshold'
    DOC = ':local_adaptive_threshold'

    def render_to_gui(self, panel):
        panel.add_group(None, [('segmentation_folder', (0, 0, 1, 1))])
        panel.add_group(None, [('loader_regex', (0, 0, 1, 1))])


    @stopwatch()
    def _run(self, meta_image):
        image = meta_image.image

        coords = dict(
            plate = meta_image.image_container.current_plate,
            pos = meta_image.coordinate.position,
            time = meta_image.coordinate.time,
            zslice = meta_image.coordinate.zslice,
            channel = meta_image.coordinate.channel,
            )

        main_folder = self.params['segmentation_folder']
        #FIXME: This is useful enought to put into an reusable function, maybe in utils?
        locator = self.params["loader_regex"] % coords
        locator_split = locator.split('/')
        locator_match = '/'
        for loc in locator_split[:-1]:
            try:
                match_candidates = os.listdir(main_folder + locator_match)
                if len(match_candidates) == 0:
                    raise RuntimeError
            except:
                raise RuntimeError('No files found in ' + main_folder + locator_match)
            match_results = [m.group() for l in match_candidates for m in [re.search(loc, l)] if m]
            if len(match_results) != 1:
                raise RuntimeError('Could not match ' + match_candidates[0] + ' with ' + loc)
            locator_match += match_results[0] + '/'

        match_candidates = os.listdir(main_folder + locator_match)

        match_results = [m.group() for l in match_candidates for m in [re.search(locator_split[-1], l)] if m]
        if len(match_results) == 0:
            raise RuntimeError('Could not match ', match_candidates[0], 'with', locator_split[-1])

        match_result = match_results[0]

        img = ccore.readImage(main_folder + locator_match + match_result)

        container = ccore.ImageMaskContainer(image, img, False)
        return container


class Ilastik(LocalAdaptiveThreshold):

    LABEL = 'Local adaptive threshold w/ split&merge using trained ilastik classifier'
    NAME = 'primary_ilastik'
    COLOR = '#FF0000'

    REQUIRES = None

    PARAMS = [('ilastik_classifier', StringTrait('', 1000, label='ilastik Classifier File',
                                                 widget_info=StringTrait.STRING_FILE)),
              ('ilastik_class_selector', IntTrait(1, 0, 1000, label='Output class')),
              ('medianradius', IntTrait(2, 0, 1000, label='Median radius')),
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

    # the : at the beginning indicates a QRC link with alias 'plugins/segmentation/local_adaptive_threshold'
    DOC = ':local_adaptive_threshold'

    @stopwatch()
    def prefilter(self, img_in):
        img = SegmentationPluginPrimary.prefilter(self, img_in)
        np_img = img.toArray(True)
        return self._predict_image_with_ilastik(np_img)


    def threshold(self, img_in, *args):
        np_img = img_in.toArray(True)
        return ccore.numpy_to_image((np_img > 128).astype(numpy.uint8), True)

    def render_to_gui(self, panel):
        panel.add_group(None, [('ilastik_classifier', (0, 0, 1, 1)),
                               ('ilastik_class_selector', (1, 0, 1, 1)),
                               ], label='ilastik')
        SegmentationPluginPrimary.render_to_gui(self, panel)

    def _predict_image_with_ilastik(self, image_):
        import ilastik
        from ilastik.core.dataMgr import DataMgr, DataItemImage
        from ilastik.modules.classification.core.featureMgr import FeatureMgr
        from ilastik.modules.classification.core.classificationMgr import ClassificationMgr
        from ilastik.modules.classification.core.features.featureBase import FeatureBase
        from ilastik.modules.classification.core.classifiers.classifierRandomForest import ClassifierRandomForest
        from ilastik.modules.classification.core.classificationMgr import ClassifierPredictThread
        from ilastik.core.volume import DataAccessor
        import numpy, h5py

        dataMgr = DataMgr()

        # Transform input image to ilastik convention s
        # 3D = (time,x,y,z,channel)
        # 2D = (time,1,x,y,channel)
        # Note, this work for 2D images right now. Is there a need for 3D
        image_.shape = (1,1) + image_.shape

        # Check if image_ has channels, if not add singelton dimension
        if len(image_.shape) == 4:
            image_.shape = image_.shape + (1,)

        # Add data item di to dataMgr
        di = DataItemImage('')
        di.setDataVol(DataAccessor(image_))
        dataMgr.append(di, alreadyLoaded=True)

        fileName = self.params["ilastik_classifier"]
        ilastik_class = self.params["ilastik_class_selector"]

        hf = h5py.File(fileName,'r')
        temp = hf['classifiers'].keys()
        # If hf is not closed this leads to an error in win64 and mac os x
        hf.close()
        del hf

        classifiers = []
        for cid in temp:
            cidpath = 'classifiers/' + cid
            classifiers.append(ClassifierRandomForest.loadRFfromFile(fileName, str(cidpath)))

        dataMgr.module["Classification"]["classificationMgr"].classifiers = classifiers

        # Restore user selection of feature items from hdf5
        featureItems = []
        f = h5py.File(fileName,'r')
        for fgrp in f['features'].values():
            featureItems.append(FeatureBase.deserialize(fgrp))
        f.close()
        del f
        fm = FeatureMgr(dataMgr, featureItems)

        # Compute features
        fm.prepareCompute(dataMgr)
        fm.triggerCompute()
        fm.joinCompute(dataMgr)

        # Predict with loaded classifier
        classificationPredict = ClassifierPredictThread(dataMgr)
        classificationPredict.start()
        classificationPredict.wait()

        if ilastik_class >= classificationPredict._prediction[0].shape[-1]:
            raise RuntimeError('ilastik output class not valid...')

        # Produce output image and select the probability map
        probMap = (classificationPredict._prediction[0][0,0,:,:, ilastik_class] * 255).astype(numpy.uint8)
        img_out = ccore.numpy_to_image(probMap, True)
        return img_out


class LocalAdaptiveThreshold2(_SegmentationPlugin):

    LABEL = 'Toggle Mappings and Local Adaptive Threshold'
    NAME = 'lat_tm'
    COLOR = '#FF0000'

    REQUIRES = None

    # the : at the beginning indicates a QRC link with alias 'plugins/segmentation/local_adaptive_threshold_tm'
    DOC = ':local_adaptive_threshold_tm'

    PARAMS = [('medianradius', IntTrait(2, 0, 1000, label='Median radius')),
              ('togglemappings', BooleanTrait(False, label='Toggle Mappings')),
              ('tm_size', IntTrait(1, 0, 20, label='Toggle Mappings Size')),
              ('latwindowsize', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit', IntTrait(1, 0, 255, label='Min. contrast')),
              ('lat2', BooleanTrait(False, label='Local adaptive threshold 2')),
              ('latwindowsize2', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit2', IntTrait(1, 0, 255, label='Min. contrast')),
              ('shapewatershed', BooleanTrait(False, label='Split & merge by shape')),
              ('shapewatershed_gausssize', IntTrait(1, 0, 1000000, label='Gauss radius')),
              ('shapewatershed_maximasize', IntTrait(1, 0, 1000000, label='Min. seed distance')),
              ('shapewatershed_minmergesize', IntTrait(1, 0, 1000000, label='Object size threshold')),
              ('intensitywatershed', BooleanTrait(False, label='Split & merge by intensity')),
              ('intensitywatershed_gausssize', IntTrait(1, 0, 1000000, label='Gauss radius')),
              ('intensitywatershed_maximasize', IntTrait(1, 0, 1000000, label='Min. seed distance')),
              ('intensitywatershed_minmergesize', IntTrait(1, 0, 1000000, label='Object size threshold')),
              ('postprocessing', BooleanTrait(False, label='Object filter')),
              ('postprocessing_roisize_min', IntTrait(-1, -1, 1000000, label='Min. object size')),
              ('postprocessing_roisize_max', IntTrait(-1, -1, 1000000, label='Max. object size')),
              ('postprocessing_intensity_min_above_bg', IntTrait(-1, -1, 1000000, label='Min. average intensity above background')),
              ('postprocessing_intensity_max_above_bg', IntTrait(-1, -1, 1000000, label='Max. average intensity above background')),
              ('removeborderobjects', BooleanTrait(True, label='Remove border objects')),
              ('holefilling', BooleanTrait(True, label='Fill holes')),
             ]

    def render_to_gui(self, panel):
        panel.add_group('togglemappings',
                        [('tm_size', (0, 0, 1, 1)),
                         ])
        panel.add_group(None,
                        [('medianradius', (0, 0, 1, 1)),
                         ('latwindowsize', (0, 1, 1, 1)),
                         ('latlimit', (0, 2, 1, 1)),
                         ], link='lat', label='Local adaptive threshold')
        panel.add_group('lat2',
                        [('latwindowsize2', (0, 0, 1, 1)),
                         ('latlimit2', (0, 1, 1, 1)),
                         ])
        panel.add_input('holefilling')
        panel.add_input('removeborderobjects')
        panel.add_group('shapewatershed',
                        [('shapewatershed_gausssize', (0, 0, 1, 1)),
                         ('shapewatershed_maximasize', (0, 1, 1, 1)),
                         ('shapewatershed_minmergesize', (1, 0, 1, 1)),
                         ])
        panel.add_group('postprocessing',
                        [('postprocessing_roisize_min', (0, 0, 1, 1)),
                         ('postprocessing_roisize_max', (0, 1, 1, 1)),
                         ('postprocessing_intensity_min_above_bg', (1, 0, 1, 1)),
                         ('postprocessing_intensity_max_above_bg', (1, 1, 1, 1)),
                         ])

    @stopwatch()
    def prefilter(self, img_in, radius=None):

        img_temp = img_in
        if self.params['togglemappings']:
            img_temp = ccore.toggle_mapping(img_in, self.params['tm_size'])

        if radius is None:
            radius = self.params['medianradius']

        img_out = ccore.disc_median(img_temp, radius)
        return img_out

    @stopwatch()
    def threshold(self, img_in, size, limit):
        img_out = ccore.window_average_threshold(img_in, size, limit)
        return img_out

    @stopwatch()
    def correct_segmetation(self, img_in, img_bin, border, gauss_size,
                            max_dist, min_merge_size, kind='shape'):
        if kind == 'shape':
            f = ccore.segmentation_correction_shape
        else:
            f = ccore.segmentation_correction_intensity
        return f(img_in, img_bin, border, gauss_size, max_dist, min_merge_size)

    @stopwatch()
    def postprocessing(self, container, is_active, roisize_minmax,
                       intensity_minmax, delete_objects=True,
                       offset=0):

        valid_ids = container.getObjects().keys()
        rejected_ids = []

        if is_active:
            feature_categories = set()
            conditions = []
            for idx, (roisize, intensity) in enumerate( \
                zip(roisize_minmax, intensity_minmax)):
                cmprt = '>=' if idx == 0 else '<='
                if roisize > -1:
                    feature_categories.add('roisize')
                    conditions.append('roisize %s %d' % (cmprt, roisize))
                if intensity > -1:
                    feature_categories.add('normbase2')
                    conditions.append('n2_avg %s %d' % (cmprt, intensity+offset))

            if len(conditions) > 0:
                conditions_str = ' and '.join(conditions)

                # extract features needed for the filter
                # FIXME: features are currently kept in the ObjectContainer and used for classification automatically
                # Features can be removed from the container, but it remains much better a choice
                # to restrict the feature sets used for classification.
                for feature in feature_categories:
                    container.applyFeature(feature)

                valid_ids = []
                rejected_ids = []

                # get a dict copy, because we delete elements from the dict
                objects = container.getObjects()
                for obj_id, obj in objects.iteritems():
                    # eval condition string based on the feature dict (provides values for the features above)
                    if not eval(conditions_str, obj.getFeatures()):
                        if delete_objects:
                            container.delObject(obj_id)
                        rejected_ids.append(obj_id)
                    else:
                        valid_ids.append(obj_id)

            #pdb.set_trace()
            #img_v = container.img.
            # delete features that were added by the object filter
            for feature in ['roisize', 'normbase2']:
                container.deleteFeatureCategory(feature)


        # store valid and rejected object IDs to the container
        container.valid_ids = valid_ids
        container.rejected_ids = rejected_ids

    @stopwatch()
    def _run(self, meta_image):
        image = meta_image.image

        img_prefiltered = self.prefilter(image)

        img_bin1 = self.threshold(img_prefiltered, self.params['latwindowsize'], self.params['latlimit'])

        if self.params['holefilling']:
            ccore.fill_holes(img_bin1, False)

        if self.params['lat2']:
            img_bin2 = self.threshold(img_prefiltered, self.params['latwindowsize2'],
                                      self.params['latlimit2'])

            # replacement for not working ccore.projectImage
            img_bin = numpy.zeros((img_bin2.height, img_bin2.width),
                                 dtype=meta_image.format)
            img_bin = ccore.numpy_to_image(img_bin, copy=True)
            ccore.zproject(img_bin, [img_bin1, img_bin2], ccore.ProjectionType.MaxProjection)
        else:
            img_bin = img_bin1

        if self.params['shapewatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['latwindowsize'],
                                               self.params['shapewatershed_gausssize'],
                                               self.params['shapewatershed_maximasize'],
                                               self.params['shapewatershed_minmergesize'],
                                               kind='shape')
        if self.params['intensitywatershed']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['latwindowsize'],
                                               self.params['intensitywatershed_gausssize'],
                                               self.params['intensitywatershed_maximasize'],
                                               self.params['intensitywatershed_minmergesize'],
                                               kind='intensity')

        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])

        # calculate offset: mean on the background region, as given by the segmentation result
        # no locality: simply a global mean on the image.
        np_image = image.toArray(True)
        np_img_bin = img_bin.toArray(True)
        offset = np_image[np_img_bin==0].mean()

        self.postprocessing(container, self.params['postprocessing'],
                            (self.params['postprocessing_roisize_min'], self.params['postprocessing_roisize_max']),
                            (self.params['postprocessing_intensity_min_above_bg'], self.params['postprocessing_intensity_max_above_bg']),
                            offset=offset)

        return container


class LocalAdaptiveThreshold3(_SegmentationPlugin):

    LABEL = 'Local Adaptive Threshod, Split by morphological dynamics'
    NAME = 'primary3'
    COLOR = '#FF0000'

    REQUIRES = None

    # the : at the beginning indicates a QRC link with alias 'plugins/segmentation/local_adaptive_threshold_tm'
    DOC = ':local_adaptive_threshold_dyn'

    PARAMS = [('medianradius', IntTrait(2, 0, 1000, label='Median radius')),
              ('togglemappings', BooleanTrait(False, label='Toggle Mappings')),
              ('tm_size', IntTrait(1, 0, 20, label='Toggle Mappings Size')),
              ('latwindowsize', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit', IntTrait(1, 0, 255, label='Min. contrast')),
              ('lat2', BooleanTrait(False, label='Local adaptive threshold 2')),
              ('latwindowsize2', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit2', IntTrait(1, 0, 255, label='Min. contrast')),
              ('watershed_distance', BooleanTrait(False, label='Watershed (Distance)')),
              ('watershed_dynamic', IntTrait(2, 0, 1000, label='Minimal depth')),
              ('watershed_used_distance', IntTrait(2, 0, 2, label='Distance Metric (0: chessboard, 1: L1, 2: L2)')),
              ('postprocessing', BooleanTrait(False, label='Object filter')),
              ('postprocessing_roisize_min', IntTrait(-1, -1, 1000000, label='Min. object size')),
              ('postprocessing_roisize_max', IntTrait(-1, -1, 1000000, label='Max. object size')),
              ('postprocessing_intensity_min_above_bg', IntTrait(-1, -1, 1000000, label='Min. average intensity above background')),
              ('postprocessing_intensity_max_above_bg', IntTrait(-1, -1, 1000000, label='Max. average intensity above background')),
              ('removeborderobjects', BooleanTrait(True, label='Remove border objects')),
              ('holefilling', BooleanTrait(True, label='Fill holes')),
             ]


    def render_to_gui(self, panel):
        panel.add_group('togglemappings',
                        [('tm_size', (0, 0, 1, 1)),
                         ])
        panel.add_group(None,
                        [('medianradius', (0, 0, 1, 1)),
                         ('latwindowsize', (0, 1, 1, 1)),
                         ('latlimit', (0, 2, 1, 1)),
                         ], link='lat', label='Local adaptive threshold')
        panel.add_group('lat2',
                        [('latwindowsize2', (0, 0, 1, 1)),
                         ('latlimit2', (0, 1, 1, 1)),
                         ])
        panel.add_input('holefilling')
        panel.add_input('removeborderobjects')
        panel.add_group('watershed_distance',
                        [('watershed_dynamic', (0, 0, 1, 1)),
                         ('watershed_used_distance', (0, 1, 1, 1)),
                         ])

        panel.add_group('postprocessing',
                        [('postprocessing_roisize_min', (0, 0, 1, 1)),
                         ('postprocessing_roisize_max', (0, 1, 1, 1)),
                         ('postprocessing_intensity_min_above_bg', (1, 0, 1, 1)),
                         ('postprocessing_intensity_max_above_bg', (1, 1, 1, 1)),
                         ])

    @stopwatch()
    def prefilter(self, img_in, radius=None):

        img_temp = img_in
        if self.params['togglemappings']:
            img_temp = ccore.toggle_mapping(img_in, self.params['tm_size'])

        if radius is None:
            radius = self.params['medianradius']

        img_out = ccore.disc_median(img_temp, radius)
        return img_out

    @stopwatch()
    def threshold(self, img_in, size, limit):
        img_out = ccore.window_average_threshold(img_in, size, limit)
        return img_out

    @stopwatch()
    def OLD_correct_segmetation(self, img_in, img_bin, border, gauss_size,
                            max_dist, min_merge_size, kind='shape'):
        if kind == 'shape':
            f = ccore.segmentation_correction_shape
        else:
            f = ccore.segmentation_correction_intensity
        return f(img_in, img_bin, border, gauss_size, max_dist, min_merge_size)

    @stopwatch()
    def correct_segmetation(self, img_in, img_bin, dyn, distance=2):

        if distance==2:
            # Euclidean distance
            res = ccore.watershed_dynamic_split(img_bin, dyn, 8, 2)
        elif distance==1:
            # we use connectivity 4 (for the watershed) and distance mode 1 (which
            # corresponds to the L1 norm which corresponds to the graph distance
            # of a 4-neighborhood graph
            res = ccore.watershed_dynamic_split(img_bin, dyn, 8, 1)
        elif distance==0:
            # the chessboard distance and 8 connectivity for the watershed algorithm.
            # However, the distances are "deeper" for 4-connectivity.
            res = ccore.watershed_dynamic_split(img_bin, dyn, 8, 0)
        else:
            print 'not implemented'
            res = img_bin

        return res

    @stopwatch()
    def postprocessing(self, container, is_active, roisize_minmax,
                       intensity_minmax, delete_objects=True,
                       offset=0):

        valid_ids = container.getObjects().keys()
        rejected_ids = []

        if is_active:
            feature_categories = set()
            conditions = []
            for idx, (roisize, intensity) in enumerate( \
                zip(roisize_minmax, intensity_minmax)):
                cmprt = '>=' if idx == 0 else '<='
                if roisize > -1:
                    feature_categories.add('roisize')
                    conditions.append('roisize %s %d' % (cmprt, roisize))
                if intensity > -1:
                    feature_categories.add('normbase2')
                    conditions.append('n2_avg %s %d' % (cmprt, intensity+offset))

            if len(conditions) > 0:
                conditions_str = ' and '.join(conditions)

                # extract features needed for the filter
                # FIXME: features are currently kept in the ObjectContainer and used for classification automatically
                # Features can be removed from the container, but it remains much better a choice
                # to restrict the feature sets used for classification.
                for feature in feature_categories:
                    container.applyFeature(feature)

                valid_ids = []
                rejected_ids = []

                # get a dict copy, because we delete elements from the dict
                objects = container.getObjects()
                for obj_id, obj in objects.iteritems():
                    # eval condition string based on the feature dict (provides values for the features above)
                    if not eval(conditions_str, obj.getFeatures()):
                        if delete_objects:
                            container.delObject(obj_id)
                        rejected_ids.append(obj_id)
                    else:
                        valid_ids.append(obj_id)

            #pdb.set_trace()
            #img_v = container.img.
            # delete features that were added by the object filter
            for feature in ['roisize', 'normbase2']:
                container.deleteFeatureCategory(feature)


        # store valid and rejected object IDs to the container
        container.valid_ids = valid_ids
        container.rejected_ids = rejected_ids

    @stopwatch()
    def _run(self, meta_image):
        image = meta_image.image

        img_prefiltered = self.prefilter(image)

        img_bin1 = self.threshold(img_prefiltered, self.params['latwindowsize'], self.params['latlimit'])

        if self.params['holefilling']:
            ccore.fill_holes(img_bin1, False)

        if self.params['lat2']:
            img_bin2 = self.threshold(img_prefiltered, self.params['latwindowsize2'],
                                      self.params['latlimit2'])

            # replacement for not working ccore.projectImage
            img_bin = numpy.zeros((img_bin2.height, img_bin2.width),
                                 dtype=meta_image.format)
            img_bin = ccore.numpy_to_image(img_bin, copy=True)
            ccore.zproject(img_bin, [img_bin1, img_bin2], ccore.ProjectionType.MaxProjection)
        else:
            img_bin = img_bin1

        if self.params['watershed_distance']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['watershed_dynamic'],
                                               self.params['watershed_used_distance'])

        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])

        # calculate offset: mean on the background region, as given by the segmentation result
        # no locality: simply a global mean on the image.
        np_image = image.toArray(True)
        np_img_bin = img_bin.toArray(True)
        offset = np_image[np_img_bin==0].mean()

        self.postprocessing(
            container, self.params['postprocessing'],
            (self.params['postprocessing_roisize_min'],
             self.params['postprocessing_roisize_max']),
            (self.params['postprocessing_intensity_min_above_bg'],
             self.params['postprocessing_intensity_max_above_bg']),
            offset=offset)

        return container


class LocalAdaptiveThreshold4(_SegmentationPlugin):

    LABEL = 'Global and Local Adaptive Threshod, Split by morphological dynamics'
    NAME = 'primary4'
    COLOR = '#FF0000'

    REQUIRES = None

    # the : at the beginning indicates a QRC link with alias 'plugins/segmentation/local_adaptive_threshold_tm'
    DOC = ':local_adaptive_threshold_globloc'

    PARAMS = [('median', BooleanTrait(True, label='Median filter')),
              ('medianradius', IntTrait(2, 0, 1000, label='Median radius')),
              ('togglemappings', BooleanTrait(False, label='Toggle Mappings')),
              ('tm_size', IntTrait(1, 0, 20, label='Toggle Mappings Size')),
              ('local', BooleanTrait(False, label='Local Threshold')),
              ('latwindowsize', IntTrait(20, 1, 1000, label='Window size')),
              ('latlimit', IntTrait(1, 0, 255, label='Min. contrast')),
              ('global', BooleanTrait(False, label='Global Threshold')),
              ('otsu_factor', FloatTrait(0.95, 0, 255, label='Otsu Factor', digits=2)),
              ('offset', IntTrait(0, 0, 255, label='Threshold Offset')),
              ('watershed_distance', BooleanTrait(False, label='Watershed (Distance)')),
              ('watershed_dynamic', IntTrait(2, 0, 1000, label='Minimal depth')),
              ('watershed_used_distance',
               IntTrait(2, 0, 2, label='Distance Metric (0: chessboard, 1: L1, 2: L2)')),
              ('postprocessing', BooleanTrait(False, label='Object filter')),
              ('postprocessing_roisize_min', IntTrait(-1, -1, 1000000, label='Min. object size')),
              ('postprocessing_roisize_max', IntTrait(-1, -1, 1000000, label='Max. object size')),
              ('postprocessing_intensity_min_above_bg',
               IntTrait(-1, -1, 1000000, label='Min. average intensity above background')),
              ('postprocessing_intensity_max_above_bg',
               IntTrait(-1, -1, 1000000, label='Max. average intensity above background')),
              ('removeborderobjects', BooleanTrait(True, label='Remove border objects')),
              ('holefilling', BooleanTrait(True, label='Fill holes')),
              ('holearea', IntTrait(1, 0, 100000, label='Maximal Hole Size')),
          ]


    def render_to_gui(self, panel):
        panel.add_group('togglemappings',
                        [('tm_size', (0, 0, 1, 1)),
                         ])
        panel.add_group('median',
                        [('medianradius', (0, 0, 1, 1)),
                         ])
        panel.add_group('local',
                        [('latwindowsize', (0, 1, 1, 1)),
                         ('latlimit', (0, 2, 1, 1)),
                         ], link='lat', label='Local adaptive threshold')
        panel.add_group('global',
                        [('otsu_factor', (0, 0, 1, 1)),
                         ('offset', (0, 1, 1, 1)),
                         ])
        panel.add_group('holefilling',
                        [('holearea', (0, 0, 1, 1)),
                         ])
        panel.add_input('removeborderobjects')
        panel.add_group('watershed_distance',
                        [('watershed_dynamic', (0, 0, 1, 1)),
                         ('watershed_used_distance', (0, 1, 1, 1)),
                         ])

        panel.add_group('postprocessing',
                        [('postprocessing_roisize_min', (0, 0, 1, 1)),
                         ('postprocessing_roisize_max', (0, 1, 1, 1)),
                         ('postprocessing_intensity_min_above_bg', (1, 0, 1, 1)),
                         ('postprocessing_intensity_max_above_bg', (1, 1, 1, 1)),
                         ])

    @stopwatch()
    def prefilter(self, img_in, radius=None):

        img_temp = img_in
        if self.params['togglemappings']:
            img_temp = ccore.toggle_mapping(img_in, self.params['tm_size'])

        if radius is None:
            radius = self.params['medianradius']

        if self.params['median']:
            img_out = ccore.disc_median(img_temp, radius)
        else:
            img_out = img_temp

        return img_out

    @stopwatch()
    def threshold(self, img_in, size, limit):
        img_out = ccore.window_average_threshold(img_in, size, limit)
        return img_out

    @stopwatch()
    def _global_threshold(self, img, otsu_factor=1.0, offset=0):
        #histo = img.getHistogram(256)
        otsu_thresh = ccore.get_otsu_threshold(img)
        threshold = otsu_factor * otsu_thresh + offset
        img_thresh = ccore.threshold_image(img, int(threshold))
        #ccore.writeImage(img_thresh, os.path.join(self.debug_dir, 'thresh.png'))
        return img_thresh

    def get_first_mode(self, img):
        histo = img.getHistogram(256)

        mode = None

        if len(histo) > 3:
            for i in range(len(histo) - 2):
                if .5*(histo[i+1] + histo[i]) > .5*(histo[i+2] + histo[i+1]):
                    mode = i
                    break

        if mode is None:
            mode = 0
        return mode

    def get_perc_decrease(self, img, perc = 0.5):
        histo = img.getHistogram(256)
        max_histo = numpy.max(histo)

        ind = numpy.where(histo==max_histo)
        mode = ind[0][0]

        for i in range(mode, len(histo) -2):
            if .5*(histo[i+1] + histo[i]) < perc * max_histo:
                mode = i
                break

        return mode

    @stopwatch()
    def correct_segmetation(self, img_in, img_bin, dyn, distance=2):

        if distance==2:
            # Euclidean distance
            res = ccore.watershed_dynamic_split(img_bin, dyn, 8, 2)
        elif distance==1:
            # we use connectivity 4 (for the watershed) and distance mode 1 (which
            # corresponds to the L1 norm which corresponds to the graph distance
            # of a 4-neighborhood graph
            res = ccore.watershed_dynamic_split(img_bin, dyn, 8, 1)
        elif distance==0:
            # the chessboard distance and 8 connectivity for the watershed algorithm.
            # However, the distances are "deeper" for 4-connectivity.
            res = ccore.watershed_dynamic_split(img_bin, dyn, 8, 0)
        else:
            print 'not implemented'
            res = img_bin

        return res

    @stopwatch()
    def postprocessing(self, container, is_active, roisize_minmax,
                       intensity_minmax, delete_objects=True,
                       offset=0):

        valid_ids = container.getObjects().keys()
        rejected_ids = []

        if is_active:
            feature_categories = set()
            conditions = []
            for idx, (roisize, intensity) in enumerate( \
                zip(roisize_minmax, intensity_minmax)):
                cmprt = '>=' if idx == 0 else '<='
                if roisize > -1:
                    feature_categories.add('roisize')
                    conditions.append('roisize %s %d' % (cmprt, roisize))
                if intensity > -1:
                    feature_categories.add('normbase2')
                    conditions.append('n2_avg %s %f' % (cmprt, intensity+offset))

            if len(conditions) > 0:
                conditions_str = ' and '.join(conditions)

                # extract features needed for the filter
                # FIXME: features are currently kept in the ObjectContainer and used for classification automatically
                # Features can be removed from the container, but it remains much better a choice
                # to restrict the feature sets used for classification.
                for feature in feature_categories:
                    container.applyFeature(feature)

                valid_ids = []
                rejected_ids = []

                # get a dict copy, because we delete elements from the dict
                objects = container.getObjects()
                for obj_id, obj in objects.iteritems():
                    # eval condition string based on the feature dict (provides values for the features above)
                    if not eval(conditions_str, obj.getFeatures()):
                        if delete_objects:
                            container.delObject(obj_id)
                        rejected_ids.append(obj_id)
                    else:
                        valid_ids.append(obj_id)

            #pdb.set_trace()
            #img_v = container.img.
            # delete features that were added by the object filter
            for feature in ['roisize', 'normbase2']:
                container.deleteFeatureCategory(feature)


        # store valid and rejected object IDs to the container
        container.valid_ids = valid_ids
        container.rejected_ids = rejected_ids

    @stopwatch()
    def _run(self, meta_image):
        image = meta_image.image

        temp = self.prefilter(image)
        img_bin1 = None
        img_bin2 = None

        grey_level_shift = self.get_perc_decrease(temp, perc=0.5)
        im_min, im_max = temp.getMinmax()

        # we subtract grey_level_shift with lower clipping.
        # i.e. f(x) = 0 if x(x) <= grey_level_shift
        # otherwise: f(x) = f(x) - grey_level_shift
        if grey_level_shift >= im_max - 1:
            grey_level_shift = im_max - 1
        img_prefiltered = ccore.linearRangeMapping(temp, grey_level_shift, im_max, 0, im_max-grey_level_shift )

        if not (self.params['local'] or self.params['global']):
            raise RuntimeError('At least one thresholding scheme must be selected.')

        if self.params['local']:
            img_bin1 = self.threshold(img_prefiltered, self.params['latwindowsize'], self.params['latlimit'])

        if self.params['global']:
            #img_bin2 = self.threshold(img_prefiltered, self.params['latwindowsize2'],
            #                          self.params['latlimit2'])
            img_bin2 = self._global_threshold(img_prefiltered, otsu_factor=self.params['otsu_factor'],
                                              offset=self.params['offset'])

            if img_bin1 is None:
                img_bin = img_bin2
            else:
                # replacement for not working ccore.projectImage
                img_bin = numpy.zeros((img_bin2.height, img_bin2.width),
                                      dtype=meta_image.format)

                img_bin = ccore.numpy_to_image(img_bin, copy=True)
                ccore.zproject(img_bin, [img_bin1, img_bin2], ccore.ProjectionType.MaxProjection)
        else:
            img_bin = img_bin1

        if self.params['holefilling']:
            #ccore.fill_holes(img_bin, False)
            img_bin = ccore.area_close(img_bin, self.params['holearea'], 8)

        if self.params['watershed_distance']:
            img_bin = self.correct_segmetation(img_prefiltered, img_bin,
                                               self.params['watershed_dynamic'],
                                               self.params['watershed_used_distance'])

        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])

        # calculate offset: mean on the background region, as given by the segmentation result
        # no locality: simply a global mean on the image.
        np_image = image.toArray(True)
        np_img_bin = img_bin.toArray(True)
        offset = np_image[np_img_bin==0].mean()

        self.postprocessing(
            container, self.params['postprocessing'],
            (self.params['postprocessing_roisize_min'], self.params['postprocessing_roisize_max']),
            (self.params['postprocessing_intensity_min_above_bg'],
             self.params['postprocessing_intensity_max_above_bg']),
            offset=offset)

        return container
