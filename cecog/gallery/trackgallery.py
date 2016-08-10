"""
trackgallery.py
"""
from __future__ import absolute_import
import six

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['TrackGallery']

import csv
from os.path import join

import vigra
import numpy as np
from cecog.gallery import GalleryRGBImage
from cecog.analyzer.tracker import Tracker
from cecog.util.util import makedirs

class TrackGallery(object):

    def __init__(self, centers, indir, outdir, position,
                 size=200, write_tables=True):
        self.centers = centers
        self._indir = indir
        self._outdir = outdir
        self.position = position

        if size%2:
            size += 1
        self._size = size
        self._write_tables = write_tables

        self._image_cache = dict()
        self.make_gallery()

    def load_image(self, file_):
        if file_ not in self._image_cache:
            image = vigra.readImage(file_)
            # numpy array convention
            image.swapaxes(0, 1)
            self._image_cache[file_] = np.squeeze(image)
        return self._image_cache[file_]

    def _split_nodeid(self, nodeid):
        ret = Tracker.split_nodeid(nodeid)
        if len(ret) == 2:
            ret = ret + (1, )
        return ret

    def write_center_tables(self):
        """Write a csv file with frame number and bounding boxes."""
        dir_ = join(self._outdir, '_info_')
        makedirs(dir_)
        for startid, centers in six.iteritems(self.centers):
            fname =  join(dir_, "P%s__T%05d__O%04d__B%02d.csv" \
                              %((self.position, )+self._split_nodeid(startid)))
            with open(fname, 'w') as fp:
                writer = csv.writer(fp, delimiter=',')
                writer.writerow(['Frame', 'ObjId', 'centerX', 'centerY'])
                for frame, objid, center in centers:
                    writer.writerow((frame, objid)+center)

    def cut(self, image, xxx_todo_changeme):
        (xmin, xmax, ymin, ymax) = xxx_todo_changeme
        return image[xmin:xmax, ymin:ymax, :]

    def _i_sub_image(self, center, xxx_todo_changeme1):
        """Return the pixel indices of the sub image according to the size of
        the gallery and an offset for the crack contours."""
        (width, height) = xxx_todo_changeme1
        xmin = center[0] - self._size/2
        xmax = center[0] + self._size/2
        ymin = center[1] - self._size/2
        ymax = center[1] + self._size/2

        # range checks
        if xmin < 0:
            xmin, xmax = 0, self._size
        elif xmax > width:
            xmin, xmax = width-self._size, width

        if ymin < 0:
            ymin, ymax = 0, self._size
        elif ymax > height:
            ymin, ymax = height-self._size, height
        return (xmin, xmax, ymin, ymax)

    def make_gallery(self):
        if self._write_tables:
            self.write_center_tables()

        for startid, centers in six.iteritems(self.centers):
            iname = join(self._outdir, "P%s__T%05d__O%04d__B%02d.png" \
                             %((self.position, )+self._split_nodeid(startid)))
            gallery = GalleryRGBImage(((len(centers))*self._size, self._size, 3),
                                      dtype=np.uint8, nsub=len(centers))

            for i, (frame, objid, center) in enumerate(centers):
                ifile = join(self._indir, 'P%s_T%05d.jpg' %(self.position, frame))
                image = self.load_image(ifile)
                bbox = self._i_sub_image(center, image.shape[:2])
                sub_img = self.cut(image, bbox)
                gallery.set_sub_image(i, sub_img)
            vigra.RGBImage(gallery).writeImage(iname)
