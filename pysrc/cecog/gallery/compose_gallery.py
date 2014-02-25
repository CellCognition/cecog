"""
compose_gallery.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['compose_galleries']

import os
import random
import logging

from cecog.util.util import makedirs
from cecog import ccore
from cecog.util.util import read_table
from cecog.export.regexp import re_events


def compose_galleries(path, path_hmm, quality="90",
                      one_daughter=True, sample=30):
    logger = logging.getLogger('compose_galleries')
    column_name = 'Trajectory'
    path_index = os.path.join(path_hmm, '_index')
    if not os.path.isdir(path_index):
        logger.warning(("Index path '%s' does not exist. Make sure the error"
                        " correction was executed successfully." %path_index))
        return

    for filename in os.listdir(path_index):
        logger.info('Creating gallery overview for %s' % filename)
        group_name = os.path.splitext(filename)[0]
        t = read_table(os.path.join(path_index, filename))[1]
        t.reverse()

        if one_daughter:
            for record in t[:]:
                match = re_events.match(record[column_name])
                if match is None:
                    raise RuntimeError("file name does not regular expression:")

                if match.group('branch') != '01':
                    t.remove(record)

        n = len(t)
        if not sample is None and sample <= n:
            idx = random.sample(xrange(n), sample)
            idx.sort()
            d = [t[i] for i in idx]
        else:
            d = t

        n = len(d)
        results = {}
        for idx, record in enumerate(d):
            match = re_events.match(record[column_name])
            pos = match.group('position')
            key = 'P%s__T%s__O%s__B%s' %match.groups()[1:5]

            gallery_path = os.path.join(path, 'analyzed', pos, 'gallery')
            if os.path.isdir(gallery_path):
                for gallery_name in os.listdir(gallery_path):
                    imgdir = os.path.join(gallery_path, gallery_name)
                    if not os.path.isdir(imgdir):
                        continue

                    img = ccore.readImageRGB(os.path.join(imgdir, '%s.png' %key))
                    if gallery_name not in results:
                        results[gallery_name] = ccore.RGBImage(img.width, img.height*n)
                    img_out = results[gallery_name]
                    ccore.copySubImage(img,
                                       ccore.Diff2D(0, 0),
                                       ccore.Diff2D(img.width, img.height),
                                       img_out,
                                       ccore.Diff2D(0, img.height*idx))

        for gallery_name in results:
            path_out = os.path.join(path_hmm, '_gallery', gallery_name)
            makedirs(path_out)
            image_name = os.path.join(path_out, '%s.jpg' % group_name)
            ccore.writeImage(results[gallery_name], image_name, quality)
            logger.debug("Gallery image '%s' successfully written." % image_name)

        yield group_name
