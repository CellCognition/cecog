"""
channelgallery.py

Image gallery for single objects vs. channel

"""
from __future__ import absolute_import

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['ChannelGallery']

from os.path import isdir, join
import numpy as np
import vigra

from cecog.colors import Colors
from cecog.gallery import MergedChannelGalleryRGBImage
from cecog.util.util import makedirs


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

    def _i_sub_image(self, center, xxx_todo_changeme):
        """Return the pixel indices of the sub image according to the size of
        the gallery and an offset for the crack contours."""
        (height, width) = xxx_todo_changeme
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

    def cut(self, image, xxx_todo_changeme1):
        (xmin, xmax, ymin, ymax) = xxx_todo_changeme1
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
            gallery = MergedChannelGalleryRGBImage( \
                ((n_ch)*self._size, self._size, 3), dtype=np.uint8, nsub=n_ch)

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
