"""
channel_gallery.py

Make little image galleries for single objects vs. channel

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


from os.path import isdir, join
from matplotlib.colors import hex2color, is_color_like
import numpy as np
import vigra

from cecog.colors import Colors
from cecog.util.util import makedirs


class GalleryRGBImage(np.ndarray):

    def __new__(cls, shape, nsub=1, *args, **kw):
        if len(shape) != 3:
            raise RuntimeError("rgb image need a shape of lenght 3")
        obj = np.ndarray.__new__(cls, shape, *args, **kw)
        obj._nsub = nsub
        return obj

    def __init__(self, *args, **kw):
        super(GalleryRGBImage, self).__init__(*args, **kw)
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

    def set_sub_image(self, position, image, color, grey_subimages=True):
        if grey_subimages:
            rgb_img = self._grey2rgb(image, Colors.white)
        else:
            rgb_img = self._grey2rgb(image, color)

        xmin = position*self.swidth
        xmax = (position+1)*self.swidth
        self[xmin:xmax, :, :] = rgb_img

        # column of the merged channel
        # ensure that the same color is not added twice
        # i. e. if 2 channels are gft but have different segmentation
        if color not in self._colors:
            self._colors.append(color)
            mimg =   self[(self._nsub-1)*self.swidth:, :, :]
            mimg += self._grey2rgb(image, color)
            self[(self._nsub-1)*self.swidth:, :, :] = mimg


    def _grey2rgb(self, image, color="#FFFFFF"):
        if is_color_like(color):
            color = hex2color(color)
        # be aware that color contains floats ranging from 0 to 1
        return np.dstack((image, image, image))*np.array(color)

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


class ChannelGallery(object):

    def __init__(self, channel, frame, outdir, size=200):

        if not channel.is_virtual():
            raise RuntimeError("ChannelGallery needs a virtual channel")
        if not isdir(outdir):
            raise RuntimeError("Output directory does not exist")

        self._channel = channel
        self._outdir = outdir

        # want even number
        if size%2:
            size += 1
        self._size = size
        self._frame = frame

    def gallery_name(self, label):
        fname = "T%05d_L%s.png" %(self._frame, label)
        subdir = "-".join(self._channel.merge_regions).lower()
        return join(self._outdir, subdir, fname)

    def _i_sub_image(self, center, (height, width)):
        """Return the pixel indices of the sub image according to the size of
        the gallery and an offset for the crack contours."""

        xmin = center[0] - self._size/2
        xmax = center[0] + self._size/2
        ymin = center[1] - self._size/2
        ymax = center[1] + self._size/2
        contur_offset = np.array((0, 0))

        # range checks
        if xmin < 0:
            contur_offset[0] = xmin
            xmin, xmax = 0, self._size
        elif xmax > width:
            contur_offset[0] = xmax - width - 1
            xmin, xmax = width-self._size, width

        if ymin < 0:
            contur_offset[1] = ymin
            ymin, ymax = 0, self._size
        elif ymax > height:
            contur_offset[1] = ymax - height - 1
            ymin, ymax = height-self._size, height

        return (xmin, xmax, ymin, ymax), contur_offset

    def cut(self, image, (xmin, xmax, ymin, ymax)):
        return np.transpose(image[ymin:ymax, xmin:xmax])

    def make_target_dir(self):
        makedirs(join(self._outdir,
                      "-".join(self._channel.merge_regions).lower()))

    def make_gallery(self, grey_subimages=True):
        # n_ch >= 2
        n_ch = len(self._channel.merge_regions)+1
        self.make_target_dir()

        holder = self._channel.get_region(self._channel.regkey)
        for label in holder:
            iname = self.gallery_name(label)
            center = holder[label].oCenterAbs
            gallery = GalleryRGBImage(((n_ch)*self._size, self._size, 3),
                                      dtype=np.uint8, nsub=n_ch)

            for i, (channel, region) in enumerate(self._channel.sub_channels()):
                image = channel.meta_image.image.toArray()
                hexcolor = Colors.channel_hexcolor(channel.strChannelId)
                sholder = channel.get_region(region)
                sample = sholder[label]

                roi, coff = self._i_sub_image(center, image.shape)
                sub_img = self.cut(image, roi)
                gallery.set_sub_image(i, sub_img, hexcolor, grey_subimages)

                # contour in a single sub image
                contour = np.array(sample.crack_contour) - \
                    np.array(sample.oCenterAbs)
                contour += self._size/2 + coff
                gallery.add_contour(i, contour, sample.strHexColor)

            gallery.draw_contour()
            gallery.draw_merge_contour(holder[label].strHexColor)
            vigra.RGBImage(gallery).writeImage(iname)
