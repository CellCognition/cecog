"""
secondary_plugins.py

Segementation plugins for secondary and tertiary channels i.e.
plugins that depend on a primary segmentation.

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ("Expanded", "Rim", "Inside", "Outside", "Modification",
           "Propagate", "ConstrainedWatershed", "Modification")

from cecog import ccore
from cecog.gui.guitraits import IntTrait, FloatTrait, BooleanTrait


from cecog.plugin import stopwatch
from cecog.plugin.segmentation.manager import _SegmentationPlugin


class Expanded(_SegmentationPlugin):

    LABEL = 'Expanded region from primary'
    NAME = 'expanded'
    COLOR = '#00FFFF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']
    PARAMS = [('expansion_size', IntTrait(10, 0, 4000, label='Expansion size'))]

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

        return ccore.ImageMaskContainer(image, img_labels, False, True, True)


class Inside(_SegmentationPlugin):

    LABEL = 'Shrinked region from primary'
    NAME = 'inside'
    COLOR = '#FFFF00'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('shrinking_size', IntTrait(5, 0, 4000, label='Shrinking size')),
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

        return ccore.ImageMaskContainer(image, img_labels, False, True, True)


class Outside(_SegmentationPlugin):

    LABEL = 'Ring around primary region'
    NAME = 'outside'
    COLOR = '#00FF00'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(10, 0, 4000, label='Expansion size')),
              ('separation_size', IntTrait(5, 0, 4000, label='Separation size')),
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
            return ccore.ImageMaskContainer(image, img_labels, False, True, True)
        else:
            raise ValueError("Parameters are not valid. Requirements: 'expansion_size' > 0 and "
                             "'expansion_size' > 'separation_size'")


class Rim(_SegmentationPlugin):

    LABEL = 'Rim at primary region'
    NAME = 'rim'
    COLOR = '#FF00FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(5, 0, 4000, label='Expansion size')),
              ('shrinking_size', IntTrait(5, 0, 4000, label='Shrinking size')),
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
            return ccore.ImageMaskContainer(image, img_labels, False, True, True)
        else:
            raise ValueError("Parameters are not valid. Requirements: 'expansion_size' > 0 and/or "
                             "'shrinking_size' > 0")


class Modification(_SegmentationPlugin):

    LABEL = 'Expansion/shrinking of primary region'
    NAME = 'modification'
    COLOR = '#FF00FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('expansion_size', IntTrait(5, 0, 4000, label='Expansion size')),
              ('shrinking_size', IntTrait(5, 0, 4000, label='Shrinking size')),
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
            return ccore.ImageMaskContainer(image, img_labels, False, True, True)
        else:
            raise ValueError("Parameters are not valid. Requirements: 'expansion_size' > 0 and/or "
                             "'shrinking_size' > 0")


class Propagate(_SegmentationPlugin):

    LABEL = 'Propagate region from primary'
    NAME = 'propagate'
    COLOR = '#FFFF99'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('presegmentation_median_radius', IntTrait(1, 0, 100, label='Median radius')),
              ('presegmentation_alpha', FloatTrait(1.0, 0, 4000, label='Otsu factor', digits=2)),
              ('lambda', FloatTrait(0.05, 0, 4000, label='Lambda', digits=2)),
              ('delta_width', IntTrait(1, 1, 4, label='Delta width')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image

        img_prefiltered = ccore.disc_median(image, self.params['presegmentation_median_radius'])
        t = int(ccore.get_otsu_threshold(img_prefiltered) * self.params['presegmentation_alpha'])
        img_bin = ccore.threshold_image(img_prefiltered, t)
        img_labels = ccore.segmentation_propagate(img_prefiltered, img_bin,
                                                  container.img_labels,
                                                  self.params['lambda'],
                                                  self.params['delta_width'])
        return ccore.ImageMaskContainer(image, img_labels, False, True, True)


class ConstrainedWatershed(_SegmentationPlugin):

    LABEL = 'Constrained watershed from primary'
    NAME = 'constrained_watershed'
    COLOR = '#FF99FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('gauss_filter_size', IntTrait(2, 1, 4, label='Gauss filter size')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):
        image = meta_image.image
        img_labels = self._constrained_watershed(image, container.img_labels,
                                                 filter_size=self.params['gauss_filter_size'])
        return ccore.ImageMaskContainer(image, img_labels, False, True, True)

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


class Difference(_SegmentationPlugin):

    LABEL = 'Difference of primary and secondary'
    NAME = 'difference'
    COLOR = '#FF00FF'
    DOC = ":additional_segmentation_plugins"

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

        return ccore.ImageMaskContainer(image, img_labels, False, True, True)
