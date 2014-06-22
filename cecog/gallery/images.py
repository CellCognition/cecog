"""
image.py

Image classes to tile sub images of e.g single objects (cells) beside each other.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['GalleryRGBImage', 'MergedChannelGalleryRGBImage']

from matplotlib.colors import hex2color, is_color_like
import numpy as np

from cecog.colors import Colors

def grey2rgb(image, color="#FFFFFF"):
    if is_color_like(color):
        color = hex2color(color)
    # be aware that color contains floats ranging from 0 to 1
    return np.dstack((image, image, image))*np.array(color)


class GalleryRGBImage(np.ndarray):

    def __new__(cls, shape, nsub=1, *args, **kw):
        if len(shape) != 3:
            raise RuntimeError("rgb image need a shape of lenght 3")
        obj = np.ndarray.__new__(cls, shape, *args, **kw)
        obj._nsub = nsub
        return obj

    def __init__(self, *args, **kw):
        # np.ndarray.__init__(self, *args, **kw)
        np.ndarray.__init__(self)
        self.contours = list()
        self._swidth = None
        self._colors = list()
        self[:,:,:] = 0

    def __array_finalize__(self, obj):
        # np.ndarray.__array_finalze__(self, obj)
        pass

    @property
    def swidth(self):
        """Width of a single sub image (column)"""
        if self._swidth is None:
            self._swidth = self.shape[0]/self._nsub
        return self._swidth

    def set_sub_image(self, position, image, color=Colors.white):
        if len(image.shape) in (3, 4):
            rgb_img = image
        else:
            rgb_img = grey2rgb(image, color)

        xmin = position*self.swidth
        xmax = (position+1)*self.swidth
        self[xmin:xmax, :, :] = rgb_img

    def add_contour(self, position, contour, color):
        if is_color_like(color):
            color = hex2color(color)

        if color is None:
            color = hex2color(Colors.white)

        color = np.array(color)
        color = np.round(color*np.iinfo(self.dtype).max)

        # filter pixels that do not lie in the sub image
        contour = np.array(filter(
                lambda c: c[0]<self.swidth and c[1]<self.swidth, contour))
        contour = contour + np.array((position*self.swidth, 0))
        # rgb color according to dtype of the image
        self.contours.append((contour[:, 0], contour[:, 1], color))

    def draw_contour(self):
        for ix, iy, color in self.contours:
            self[ix, iy] = color

    def draw_merge_contour(self, color, idx=0):
        if is_color_like(color):
            color = hex2color(color)
        color = np.array(color)
        color = np.round(color*np.iinfo(self.dtype).max)
        ix, iy, _ = self.contours[idx]

        # shift contour from subimage to the last column
        xoff = (self._nsub-1-idx)*self.swidth
        self[ix+xoff, iy] = color


class MergedChannelGalleryRGBImage(GalleryRGBImage):

    def __init__(self, *args, **kw):
        GalleryRGBImage.__init__(self, *args, **kw)

    def set_sub_image(self, position, image, color, grey_subimages=True):

        if grey_subimages:
            rgb_img = grey2rgb(image, Colors.white)
        else:
            rgb_img = grey2rgb(image, color)

        xmin = position*self.swidth
        xmax = (position+1)*self.swidth
        self[xmin:xmax, :, :] = rgb_img

        # column of the merged channel
        # ensure that the same color is not added twice
        # i. e. if 2 channels are gft but have different segmentation
        if color not in self._colors:
            self._colors.append(color)
            mimg =   self[(self._nsub-1)*self.swidth:, :, :]
            mimg += grey2rgb(image, color)
            self[(self._nsub-1)*self.swidth:, :, :] = mimg
