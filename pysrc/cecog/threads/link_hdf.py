# -*- coding: utf-8 -*-
"""
link_hdf5.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from os.path import join, split, exists
import h5py
import logging

def link_hdf5_files(post_hdf5_link_list):
    logger = logging.getLogger()

    PLATE_PREFIX = '/sample/0/plate/'
    WELL_PREFIX = PLATE_PREFIX + '%s/experiment/'
    POSITION_PREFIX = WELL_PREFIX + '%s/position/'

    def get_plate_and_postion(hf_file):
        plate = hf_file[PLATE_PREFIX].keys()[0]
        well = hf_file[WELL_PREFIX % plate].keys()[0]
        position = hf_file[POSITION_PREFIX % (plate, well)].keys()[0]
        return plate, well, position

    all_pos_hdf5_filename = join(split(post_hdf5_link_list[0])[0],
                                 '_all_positions.ch5')

    if exists(all_pos_hdf5_filename):
        f = h5py.File(all_pos_hdf5_filename, 'a')
        ### This is dangerous, several processes open the file for writing...
        logger.info(("_all_positons.hdf file found, "
                     "trying to reuse it by overwrite old external links..."))

        if 'definition' in f:
            del f['definition']
            f['definition'] = h5py.ExternalLink(post_hdf5_link_list[0],
                                                '/definition')

        for fname in post_hdf5_link_list:
            fh = h5py.File(fname, 'r')
            fplate, fwell, fpos = get_plate_and_postion(fh)
            fh.close()

            msg = "Linking into _all_positons.hdf:" + \
                ((POSITION_PREFIX + '%s') % (fplate, fwell, fpos))
            logger.info(msg)
            if (POSITION_PREFIX + '%s') % (fplate, fwell, fpos) in f:
                del f[(POSITION_PREFIX + '%s') % (fplate, fwell, fpos)]
            f[(POSITION_PREFIX + '%s') % (fplate, fwell, fpos)] = \
                h5py.ExternalLink(fname, (POSITION_PREFIX + '%s')
                                  % (fplate, fwell, fpos))
        f.close()

    else:
        f = h5py.File(all_pos_hdf5_filename, 'w')
        logger.info("_all_positons.hdf file created...")

        f['definition'] = h5py.ExternalLink(post_hdf5_link_list[0],'/definition')

        for fname in post_hdf5_link_list:
            fh = h5py.File(fname, 'r')
            fplate, fwell, fpos = get_plate_and_postion(fh)
            fh.close()
            msg = "Linking into _all_positons.hdf:" + \
                ((POSITION_PREFIX + '%s') % (fplate, fwell, fpos))
            logger.info(msg)
            f[(POSITION_PREFIX + '%s') % (fplate, fwell, fpos)] = \
                h5py.ExternalLink(fname, (POSITION_PREFIX + '%s')
                                  % (fplate, fwell, fpos))
        f.close()
