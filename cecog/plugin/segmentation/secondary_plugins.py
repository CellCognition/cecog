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

__all__ = ("Expanded", "Rim", "Inside", "Outside", "Modification", "Propagate")


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
