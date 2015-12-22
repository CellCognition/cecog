"""
watershed.py

Segementation plugins for secondary and tertiary channels i.e.
based on watershed algorithms.

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("WatershedAndMultiThreshold", "WatershedAndThreshold",
           "WatershedAndThresholdLocalThreshold", "ConstrainedWatershed")

import numpy
import itertools

from cecog import ccore
from cecog.gui.guitraits import IntTrait, FloatTrait, BooleanTrait

from cecog.plugin import stopwatch
from cecog.plugin.segmentation.manager import _SegmentationPlugin


class ConstrainedWatershed(_SegmentationPlugin):

    LABEL = 'Constrained watershed from primary'
    NAME = 'constrained_watershed'
    COLOR = '#FF99FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('gauss_filter_size', IntTrait(2, 1, 4, label='Gauss filter size')), ]

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


class WatershedAndThreshold(_SegmentationPlugin):

    LABEL = 'Global Threshold and Watershed from Primary Channel'
    NAME = 'ws_and_threshold'
    COLOR = '#0099FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('gauss_filter_size', IntTrait(2, 1, 4, label='Gauss filter size')),
              ('otsu_factor', FloatTrait(0.95, 0, 255, label='Otsu Factor', digits=2)),
              ('offset', IntTrait(0, 0, 255, label='Threshold Offset')),
              ('gradient', BooleanTrait(False, label='Use Gradient (instead of the original image)')),
              ]

    @stopwatch()
    def _run(self, meta_image, container):

        image = meta_image.image
        img_filtered = self._prefilter(image, self.params['gauss_filter_size'])

        img_thresh = self._global_threshold(img_filtered,
                                            self.params['otsu_factor'],
                                            self.params['offset'])

        method = 1
        if self.params['gradient']:
            method=2

        img_labels = self._constrained_watershed(img_filtered,
                                                 container.img_labels,
                                                 img_thresh,
                                                 method=method)

        return ccore.ImageMaskContainer(image, img_labels, False, True, True)


    def _prefilter(self, img, filter_size):
        img_filtered = ccore.gaussianFilter(img, filter_size)
        return img_filtered

    def _global_threshold(self, img, otsu_factor=1.0, offset=0):
        #histo = img.getHistogram(256)
        otsu_thresh = ccore.get_otsu_threshold(img)
        threshold = otsu_factor * otsu_thresh + offset
        img_thresh = ccore.threshold_image(img, int(threshold))
        #ccore.writeImage(img_thresh, os.path.join(self.debug_dir, 'thresh.png'))
        return img_thresh

    def _constrained_watershed(self,
                               img_in, img_labels, img_thresh,
                               method=1):

        # binary image: nuclei
        maxlabel = img_labels.getMinmax()[1]
        img_bin = ccore.threshold(img_labels, 1, maxlabel, 0, 255)
        #ccore.writeImage(img_bin, os.path.join(self.debug_dir, 'nuclei_bin.png'))

        if method==1:
            # use of the inverted image
            img_inv = ccore.linearRangeMapping(img_in, 255, 0, 0, 255)
            #ccore.writeImage(img_inv, os.path.join(self.debug_dir, 'img_inv.png'))

            ws = ccore.constrainedWatershed(img_inv, img_bin)

        elif method==2:
            # use of the gradient
            img_grad = ccore.morphoGradient(img_in, 1, 8)
            #ccore.writeImage(img_grad, os.path.join(self.debug_dir, 'grad.png'))

            ws = ccore.constrainedWatershed(img_grad, img_bin)

        #ccore.writeImage(ws, os.path.join(self.debug_dir, 'ws.png'))

        # we first get the regions
        maxreslab = ws.getMinmax()[1]
        img_bin_ws = ccore.threshold(ws, 1, maxreslab, 0, 255)
        #ccore.writeImage(img_bin_ws, os.path.join(self.debug_dir, 'ws_bin.png'))

        img_bin_out = ccore.copyImageIf(img_thresh, img_bin_ws)
        #ccore.writeImage(img_bin_ws, os.path.join(self.debug_dir, 'bin_out.png'))

        img_temp = ccore.copyImageIf(img_labels, img_bin_out)
        img_out = ccore.relabelImage(img_bin_out, img_temp)
        #ccore.writeImage(img_out, os.path.join(self.debug_dir, 'relabel.png'))

        return img_out


class WatershedAndMultiThreshold(_SegmentationPlugin):

    LABEL = 'Global 3-level Threshold and Watershed from Primary Channel'
    NAME = 'ws_and_multi_threshold'
    COLOR = '#0099FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('gauss_filter_size', IntTrait(2, 1, 4, label='Gauss filter size')),
              ('otsu_factor', FloatTrait(0.95, 0, 255, label='Otsu Factor', digits=2)),
              ('offset', IntTrait(0, 0, 255, label='Threshold Offset')),
              ('gradient', BooleanTrait(False, label='Use Gradient (instead of the original image)')),
              ('to_background', BooleanTrait(False, label='Intermediate Level to background')),
              ]

    # histo : a histogram
    # M: the number of free thresholds (M >= 1)
    def _find_multi_otsu(self, histo, M):

        # number of pixels
        N = numpy.sum(histo)

        # number of grey levels
        L = len(histo)

        # relative histogram
        hrel = histo / numpy.float(N)

        A = numpy.tile(numpy.array(hrel), (L, 1))
        B = numpy.triu(A)
        P = numpy.cumsum(B, axis=1)

        C = numpy.tile(numpy.arange(L), (L, 1))
        D = C * B
        S = numpy.cumsum(D, axis=1)

        P[P==0.0] = 1.0
        scores = S * S / P

        #pdb.set_trace()

        grey_values = numpy.arange(1, L-1)
        best_score = 0
        best_combination = ()
        for thresholds in itertools.combinations(grey_values, M):
            all_thresholds = list(thresholds) + [L-1]
            #pdb.set_trace()
            #current_score = np.sum([scores[i, i+1] for i in all_thresholds[:-1]])

            current_score = scores[0,all_thresholds[0]]
            current_score += numpy.sum([scores[all_thresholds[i] + 1,
                                               all_thresholds[i+1]] for i in range(len(all_thresholds)-1)])
            #print all_thresholds, current_score
            if current_score > best_score:
                best_combination = thresholds
                best_score = current_score
                #print ' *** updated best_score: ', best_combination, best_score
        return best_score, best_combination

    @stopwatch()
    def _run(self, meta_image, container):

        image = meta_image.image
        img_filtered = self._prefilter(image, self.params['gauss_filter_size'])

        img_thresh = self._global_threshold(img_filtered,
                                            self.params['otsu_factor'],
                                            self.params['offset'])

        method = 1
        if self.params['gradient']:
            method=2

        img_labels = self._constrained_watershed(img_filtered,
                                                 container.img_labels,
                                                 img_thresh,
                                                 method=method)

        return ccore.ImageMaskContainer(image, img_labels, False, True, True)


    def _prefilter(self, img, filter_size):
        img_filtered = ccore.gaussianFilter(img, filter_size)
        return img_filtered

    def _global_threshold(self, img, otsu_factor=1.0, offset=0, to_background=False):
        histo = img.getHistogram(256)
        #otsu_thresh = ccore.get_otsu_threshold(img)
        bs, bc = self._find_multi_otsu(numpy.array(histo), 2)

        if to_background:
            # in this case, we take the higher of the two thresholds
            threshold = otsu_factor * bc[1] + offset
        else:
            # in this case, we take the lower of the two thresholds
            threshold = otsu_factor * bc[0] + offset

        img_thresh = ccore.threshold_image(img, int(threshold))
        return img_thresh

    def _constrained_watershed(self,
                               img_in, img_labels, img_thresh,
                               method=1):

        # binary image: nuclei
        maxlabel = img_labels.getMinmax()[1]
        img_bin = ccore.threshold(img_labels, 1, maxlabel, 0, 255)
        #ccore.writeImage(img_bin, os.path.join(self.debug_dir, 'nuclei_bin.png'))

        if method==1:
            # use of the inverted image
            img_inv = ccore.linearRangeMapping(img_in, 255, 0, 0, 255)
            #ccore.writeImage(img_inv, os.path.join(self.debug_dir, 'img_inv.png'))

            ws = ccore.constrainedWatershed(img_inv, img_bin)

        elif method==2:
            # use of the gradient
            img_grad = ccore.morphoGradient(img_in, 1, 8)
            #ccore.writeImage(img_grad, os.path.join(self.debug_dir, 'grad.png'))

            ws = ccore.constrainedWatershed(img_grad, img_bin)

        #ccore.writeImage(ws, os.path.join(self.debug_dir, 'ws.png'))

        # we first get the regions
        maxreslab = ws.getMinmax()[1]
        img_bin_ws = ccore.threshold(ws, 1, maxreslab, 0, 255)
        #ccore.writeImage(img_bin_ws, os.path.join(self.debug_dir, 'ws_bin.png'))

        img_bin_out = ccore.copyImageIf(img_thresh, img_bin_ws)
        #ccore.writeImage(img_bin_ws, os.path.join(self.debug_dir, 'bin_out.png'))

        img_temp = ccore.copyImageIf(img_labels, img_bin_out)
        img_out = ccore.relabelImage(img_bin_out, img_temp)
        #ccore.writeImage(img_out, os.path.join(self.debug_dir, 'relabel.png'))

        return img_out


class WatershedAndThresholdLocalThreshold(_SegmentationPlugin):

    LABEL = 'Global & Local Threshold + Watershed from Primary Channel'
    NAME = 'ws_and_global_and_local_threshold'
    COLOR = '#0099FF'
    DOC = ":additional_segmentation_plugins"

    REQUIRES = ['primary_segmentation']

    PARAMS = [('gauss_filter_size', IntTrait(2, 1, 4, label='Gauss filter size')),
              ('otsu_factor', FloatTrait(0.95, 0, 255, label='Otsu Factor', digits=2)),
              ('offset', IntTrait(0, 0, 255, label='Threshold Offset')),
              ('gradient', BooleanTrait(False, label='Use Gradient (instead of the original image)')),
              ('medianradius', IntTrait(0, 0, 255, label='Median Radius (for local thresholding)')),
              ('window_size', IntTrait(0, 0, 255, label='Window size')),
              ('local_threshold', IntTrait(0, 0, 255, label='Local Threshold')),
              ]

    @stopwatch()
    def _local_prefilter(self, img_in, radius=None):
        if radius is None:
            radius = self.params['medianradius']
        img_out = ccore.disc_median(img_in, radius)
        return img_out

    @stopwatch()
    def _local_threshold(self, img_in):
        img_out = ccore.window_average_threshold(img_in,
                                                 self.params['window_size'],
                                                 self.params['local_threshold'])
        return img_out


    @stopwatch()
    def _run(self, meta_image, container):

        image = meta_image.image
        img_filtered = self._prefilter(image, self.params['gauss_filter_size'])

        img_thresh = self._global_threshold(img_filtered,
                                            self.params['otsu_factor'],
                                            self.params['offset'])

        img_local_filtered = self._local_prefilter(image)
        img_local_thresh = self._local_threshold(img_local_filtered)
        img_thresh = ccore.supremum(img_thresh, img_local_thresh)

        method = 1
        if self.params['gradient']:
            method=2

        img_labels = self._constrained_watershed(img_filtered,
                                                 container.img_labels,
                                                 img_thresh,
                                                 method=method)

        return ccore.ImageMaskContainer(image, img_labels, False, True, True)


    def _prefilter(self, img, filter_size):
        img_filtered = ccore.gaussianFilter(img, filter_size)
        return img_filtered

    def _global_threshold(self, img, otsu_factor=1.0, offset=0):
        #histo = img.getHistogram(256)
        otsu_thresh = ccore.get_otsu_threshold(img)
        threshold = otsu_factor * otsu_thresh + offset
        img_thresh = ccore.threshold_image(img, int(threshold))
        #ccore.writeImage(img_thresh, os.path.join(self.debug_dir, 'thresh.png'))
        return img_thresh

    def _constrained_watershed(self,
                               img_in, img_labels, img_thresh,
                               method=1):

        # binary image: nuclei
        maxlabel = img_labels.getMinmax()[1]
        img_bin = ccore.threshold(img_labels, 1, maxlabel, 0, 255)
        #ccore.writeImage(img_bin, os.path.join(self.debug_dir, 'nuclei_bin.png'))

        if method==1:
            # use of the inverted image
            img_inv = ccore.linearRangeMapping(img_in, 255, 0, 0, 255)
            #ccore.writeImage(img_inv, os.path.join(self.debug_dir, 'img_inv.png'))

            ws = ccore.constrainedWatershed(img_inv, img_bin)

        elif method==2:
            # use of the gradient
            img_grad = ccore.morphoGradient(img_in, 1, 8)
            #ccore.writeImage(img_grad, os.path.join(self.debug_dir, 'grad.png'))

            ws = ccore.constrainedWatershed(img_grad, img_bin)

        #ccore.writeImage(ws, os.path.join(self.debug_dir, 'ws.png'))

        # we first get the regions
        maxreslab = ws.getMinmax()[1]
        img_bin_ws = ccore.threshold(ws, 1, maxreslab, 0, 255)
        #ccore.writeImage(img_bin_ws, os.path.join(self.debug_dir, 'ws_bin.png'))

        img_bin_out = ccore.copyImageIf(img_thresh, img_bin_ws)
        #ccore.writeImage(img_bin_ws, os.path.join(self.debug_dir, 'bin_out.png'))

        img_temp = ccore.copyImageIf(img_labels, img_bin_out)
        img_out = ccore.relabelImage(img_bin_out, img_temp)
        #ccore.writeImage(img_out, os.path.join(self.debug_dir, 'relabel.png'))

        return img_out
