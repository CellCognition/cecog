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


__all__ = ('Ch5File', )


import os
import time
import random
import filelock


import h5py
import glob
import h5py
import numpy as np

from cellh5 import CH5FileWriter, CH5Const

Plate = '/sample/0/plate/'
Well = Plate + '%s/experiment/'
Site = Well + '%s/position/%s'


LayoutDtype = np.dtype(
    [('File', 'S10'), ('Well', 'S3'), ('Site', '<i8'),
     ('Row', 'S1'), ('Column', '<i8'), ('GeneSymbol', 'S6'),
     ('siRNA', 'S8'), ('Group', 'S10')])


def mergeHdfFiles(target, source_dir, remove_source=True):

    hdffiles = glob.glob(os.path.join(source_dir, '*.ch5'))
    target = h5py.File(target, 'r+')

    for i, h5 in enumerate(hdffiles):
        source = h5py.File(h5, 'r')

        if i == 0:
            target.copy(source['/definition'], "/definition")

        first_item = lambda view: next(iter(view))
        plate = first_item(hf_file[Plate].keys())
        well = first_item(hf_file[Well % plate].keys())
        position = first_item(hf_file[Site %(plate, well)].keys())

        path = Site %(plate, well, position)

        path = pwp_path(source)
        target.copy(source[path], path)
        source.close()

        if remove_source:
            os.remove(h5)

    target.close()




class FileLock(filelock.FileLock):

    def release(self, *args, **kw):
        super(FileLock, self).release(*args, **kw)

        if not self.is_locked:
            try:
                os.remove(self.lock_file)
            except OSError:
                pass


class Ch5File(CH5FileWriter):

    def __init__(self, filename, timeout=60, *args, **kw):

        # randomize acces times in different processes
        # time.sleep(random.random()*1.4)

        self.lock = FileLock(filename.replace("ch5", "lock"))
        try:
            self.lock.acquire(timeout=timeout)
        except filelock.Timeout as e:
            raise IOError("Cannot open hdf file %s" %(str(e)))

        super(Ch5File, self).__init__(filename, *args, **kw)

    def close(self):
        super(Ch5File, self).close()
        self.lock.release()

    def _init_basic_structure(self):
        # because the parent method is crap
        pass

    def __getitem__(self, key):
        return self._file_handle[key]

    def __setitem__(self, key, value):
        self._file_handle[key] = value

    def __delitem__(self, key):
        del self._file_handle[key]

    def layout(self, plate):
        path = "%s/%s" %(CH5Const.LAYOUT, plate)
        return self[path].value

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
            msg = "No Plate Layout provided. File not found %s" %plate_layout
            raise IOError(msg)

        grp = self._file_handle.require_group(CH5Const.LAYOUT)

        if platename not in grp:
            rec = np.recfromtxt(plate_layout, dtype=LayoutDtype,
                                delimiter="\t", skip_header=True)
            dset = grp.create_dataset(platename, data=rec)

    # def linkFile(self, filename):

    #     sf = h5py.File(filename, "r")

    #     if not self.hasDefinition():
    #         self.copyDefinition(sf)

    #     plate = sf[Plate].keys()[0]
    #     well = sf[Well %plate].keys()[0]
    #     site = sf[Site[:-2] %(plate, well)].keys()[0]
    #     sf.close()

    #     path = Site %(plate, well, site)
    #     source_file = filename.split(os.sep)[-2:]
    #     source_file = os.sep.join(source_file)

    #     self[path] = h5py.ExternalLink(source_file, path)


    # def isLinkedFile(self, filename, plate):

    #     if filename in self.linkedFiles(plate):
    #         return True
    #     else:
    #         return False

    # def linkedFiles(self, plate):
    #     files = list()

    #     try:
    #         wells = self[Well %plate].keys()
    #         for well in wells:
    #             sites = self[Site[:-2] %(plate, well)].values()
    #             files.extend([s.file.filename for s in sites])
    #     except (KeyError, AttributeError):
    #         pass

    #     return tuple(set(files))

    def existingSites(self, plate):

        wsites = dict()

        try:
            wells = self[Well %plate].keys()
            for well in wells:
                sites = self[Site[:-2] %(plate, well)].keys()
                wsites[well] = sites
        except (KeyError, AttributeError):
            pass

        return wsites

    def numberSites(self, plate):
        return sum([len(site) for site in self.existingSites(plate).values()])

    def copySample(self, filename, delete_source=True):

        source = h5py.File(filename, "r")

        if not self.hasDefinition():
            self.copyDefinition(source)

        plate = source[Plate].keys()[0]
        well = source[Well %plate].keys()[0]
        site = source[Site[:-2] %(plate, well)].keys()[0]
        path = Site %(plate, well, site)

        self._file_handle.copy(source[path], path)

        source.close()

        if delete_source:
            os.remove(filename)
