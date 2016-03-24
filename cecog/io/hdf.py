"""
hdf.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('Ch5File', 'ch5open')


import os
from contextlib import contextmanager

import h5py
import numpy as np

from cellh5 import CH5FileWriter, CH5Const


@contextmanager
def ch5open(filename, mode='r'):
    """Open a cellh5 file using the with statement. The file handle is closed
    automatically.

    >>>with ch5open('datafile.ch5', 'r') as ch5:
    >>>   ch5.get_position("0", "0038")
    """

    ch5 = Ch5File(filename, mode=mode)
    yield ch5
    ch5.close()


class Ch5File(CH5FileWriter):

    def _init_basic_structure(self):
        # because the parent method is crap
        pass

    def __getitem__(self, key):
        self._file_handle[key]

    def __setitem__(self, key, value):
        self._file_handle[key] = value

    def __delitem__(self, key):
        del self._file_handle[key]

    def hasLayout(self, plate):
        """Check if file contains a experimental layout for a specific plate."""
        return "%s/%s" %(CH5Const.LAYOUT, plate) in self._file_handle

    def hasDefinition(self):
        """Check if file contains a experimental layout for a specific plate."""
        return CH5Const.DEFINITION in self._file_handle

    def copyDefinition(self, other):
        if isinstance(other, basestring):
            source = h5py.File(filename, "r")[CH5Const.DEFINITION]
        else:
            source = other[CH5Const.DEFINITION]

        self._file_handle.copy(source, CH5Const.DEFINITION)

    def savePlateLayout(self, plate_layout, platename):
        """Save experimental layout for using the platename."""

        if not os.path.isfile(plate_layout):
            raise RuntimeError("File not found %s" %plate_layout)

        grp = self._file_handle.require_group(CH5Const.LAYOUT)

        if platename not in grp:
            rec = np.recfromcsv(plate_layout, delimiter="\t")
            dset = grp.create_dataset(platename, data=rec)

    def linkFile(self, filename):

        sf = h5py.File(filename, "r")

        if not self.hasDefinition():
            self.copyDefinition(sf)


        Plate = '/sample/0/plate/'
        Well = Plate + '%s/experiment/'
        Site = Well + '%s/position/%s'

        plate = sf[Plate].keys()[0]
        well = sf[Well %plate].keys()[0]
        site = sf[Site[:-2] %(plate, well)].keys()[0]
        sf.close()

        path = Site %(plate, well, site)
        source_file = filename.split(os.sep)[-2:]
        source_file = os.sep.join(source_file)

        self[path] = h5py.ExternalLink(source_file, path)
