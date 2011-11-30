"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog import ccore
from cecog.gui.guitraits import (BooleanTrait,
                                 IntTrait,
                                 FloatTrait,
                                 StringTrait)


from cecog.plugin import stopwatch
from cecog.plugin.segmentation.manager import _SegmentationPlugin

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class SegmentationPluginPrimary(_SegmentationPlugin):

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
    def prefilter(self, img_in):
        radius = self.params['medianradius']
        img_out = ccore.disc_median(img_in, radius)
        return img_out

    @stopwatch()
    def threshold(self, img_in, size, limit):
        print type(img_in)
        img_out = ccore.window_average_threshold(img_in, size, limit)
        return img_out

    @stopwatch()
    def correct_segmetation(self, img_in, img_bin, border, gauss_size, max_dist, min_merge_size, kind='shape'):
        print type(img_in), type(img_bin)
        if kind == 'shape':
            f = ccore.segmentation_correction_shape
        else:
            f = ccore.segmentation_correction_intensity
        return f(img_in, img_bin, border, gauss_size, max_dist, min_merge_size)

    @stopwatch()
    def postprocessing(self, container, is_active, roisize_minmax, intensity_minmax, delete_objects=True):

        valid_ids = container.getObjects().keys()
        rejected_ids = []

        if is_active:
            feature_categories = set()
            conditions = []
            for idx, (roisize, intensity) in enumerate(zip(roisize_minmax, intensity_minmax)):
                cmprt = '>=' if idx == 0 else '<='
                if roisize > -1:
                    feature_categories.add('roisize')
                    conditions.append('roisize %s %d' % (cmprt, roisize))
                if intensity > -1:
                    feature_categories.add('normbase2')
                    conditions.append('n2_avg %s %d' % (cmprt, intensity))

            if len(conditions) > 0:
                conditions_str = ' and '.join(conditions)

                # extract features needed for the filter
                # FIXME: features are currently kept in the ObjectContainer and used for classification automatically
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
        img_bin = self.threshold(img_prefiltered, self.params['latwindowsize'], self.params['latlimit'])


        if self.params['holefilling']:
            ccore.fill_holes(img_bin, False)


        if self.params['lat2']:
            img_bin2 = self.threshold(img_prefiltered, self.params['latwindowsize2'], self.params['latlimit2'])
            img_bin = ccore.projectImage([img_bin, img_bin2], ccore.ProjectionType.MaxProjection)


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

        print type(image), type(img_bin), self.params['removeborderobjects']
        container = ccore.ImageMaskContainer(image, img_bin, self.params['removeborderobjects'])
        
        
        self.postprocessing(container, self.params['postprocessing'],
                            (self.params['postprocessing_roisize_min'], self.params['postprocessing_roisize_max']),
                            (self.params['postprocessing_intensity_min'], self.params['postprocessing_intensity_max']))

        return container
    
    
class SegmentationPluginIlastik(SegmentationPluginPrimary):

    LABEL = 'Local adaptive threshold w/ split&merge using trained ilastik classifier'
    NAME = 'primary_ilastik'
    COLOR = '#FF0000'

    REQUIRES = None

    PARAMS = [('ilastik_classifier', StringTrait('', 1000, label='Ilastik classifier file',
                                                 widget_info=StringTrait.STRING_FILE)),
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
        img_out = self._predict_image_with_ilastik(np_img)
        return img_out
    
    def render_to_gui(self, panel):
        panel.add_group(None, [('ilastik_classifier', (0, 0, 1, 1))])
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
        
        

        # Create FeatureMgr
       
        
        # Compute features

        fm.prepareCompute(dataMgr)
        fm.triggerCompute()
        fm.joinCompute(dataMgr)
        
        # Predict with loaded classifier
        
        classificationPredict = ClassifierPredictThread(dataMgr)
        classificationPredict.start()
        classificationPredict.wait()
        
        # Produce output image and select the probability map
        probMap = (classificationPredict._prediction[0][0,0,:,:, 1] *255).astype(numpy.uint8)
        
        img_out = ccore.numpy_to_image(probMap, True)
        return img_out
        
        


class SegmentationPluginExpanded(_SegmentationPlugin):

    LABEL = 'Expanded region from primary'
    NAME = 'expanded'
    COLOR = '#00FFFF'
    DOC = \
'''
Non-overlapping expansion of the primary segmentation by a certain number of steps given as 'Expansion size'.
'''

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0:
            nr_objects = container.img_labels.getMinmax()[1] + 1
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

    LABEL = 'Shrinked region from primary'
    NAME = 'inside'
    COLOR = '#FFFF00'

    REQUIRES = ['primary_segmentation']

    PARAMS = [('shrinking_size', IntTrait(0, 0, 4000, label='Shrinking size')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['shrinking_size'] > 0:
            nr_objects = container.img_labels.getMinmax()[1] + 1
            img_labels = ccore.seeded_region_shrinking(image,
                                                       container.img_labels,
                                                       nr_objects,
                                                       self.params['shrinking_size'])
        else:
            img_labels = container.img_labels

        return ccore.ImageMaskContainer(image, img_labels, False, True)


class SegmentationPluginOutside(_SegmentationPlugin):

    LABEL = 'Ring around primary region'
    NAME = 'outside'
    COLOR = '#00FF00'

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ('separation_size', IntTrait(0, 0, 4000, label='Separation size')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0 and self.params['expansion_size'] > self.params['separation_size']:
            nr_objects = container.img_labels.getMinmax()[1] + 1
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

    LABEL = 'Rim at primary region'
    NAME = 'rim'
    COLOR = '#FF00FF'

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ('shrinking_size', IntTrait(0, 0, 4000, label='Shrinking size')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0 or self.params['shrinking_size'] > 0:

            nr_objects = container.img_labels.getMinmax()[1] + 1
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


class SegmentationPluginModification(_SegmentationPlugin):

    LABEL = 'Expansion/shrinking of primary region'
    NAME = 'modification'
    COLOR = '#FF00FF'

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(0, 0, 4000, label='Expansion size')),
              ('shrinking_size', IntTrait(0, 0, 4000, label='Shrinking size')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image
        if self.params['expansion_size'] > 0 or self.params['shrinking_size'] > 0:

            nr_objects = container.img_labels.getMinmax()[1] + 1
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

    LABEL = 'Propagate region from primary'
    NAME = 'propagate'
    COLOR = '#FFFF99'

    REQUIRES = ['primary_segmentation']

    PARAMS = [('presegmentation_median_radius', IntTrait(1, 0, 100, label='Median radius')),
              ('presegmentation_alpha', FloatTrait(1.0, 0, 4000, label='Otsu factor', digits=2)),
              ('lambda', FloatTrait(0.05, 0, 4000, label='Lambda', digits=2)),
              ('delta_width', IntTrait(1, 1, 4, label='Delta width')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image

        img_red = ccore.disc_median(image, self.params['presegmentation_median_radius'])
        t = int(ccore.get_otsu_threshold(img_prefiltered) * self.params['presegmentation_alpha'])
        img_bin = ccore.threshold_image(img_prefiltered, t)
        img_labels = ccore.segmentation_propagate(img_prefiltered, img_bin,
                                                  container.img_labels,
                                                  self.params['lambda'],
                                                  self.params['delta_width'])
        return ccore.ImageMaskContainer(image, img_labels, False, True)


class SegmentationPluginConstrainedWatershed(_SegmentationPlugin):

    LABEL = 'Constrained watershed from primary'
    NAME = 'constrained_watershed'
    COLOR = '#FF99FF'

    REQUIRES = ['primary_segmentation']

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


class SegmentationPluginDifference(_SegmentationPlugin):

    LABEL = 'Difference of primary and secondary'
    NAME = 'difference'
    COLOR = '#FF00FF'

    REQUIRES = ['primary_segmentation', 'secondary_segmentation']

    PARAMS = [('reverse', BooleanTrait(False, label='Reverse subtraction')),
              ]

    @stopwatch()
    def _run(self, meta_image, container_prim, container_sec):
        image = meta_image.image
        if not self.params['reverse']:
            img_labels = ccore.substractImages(container_prim.img_labels, container_sec.img_labels)
        else:
            img_labels = ccore.substractImages(container_sec.img_labels, container_prim.img_labels)

        #array = img_labels.toArray()
        #array = numpy.abs(array)
        #img_labels = ccore.numpy_to_image(array, copy=True)
        return ccore.ImageMaskContainer(image, img_labels, False, True)

