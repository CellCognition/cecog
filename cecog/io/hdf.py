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
import collections
import filelock


import h5py
import glob
import numpy as np

from cellh5 import CH5FileWriter, CH5Const
from cellh5 import CH5PositionCoordinate

Plate = '/sample/0/plate/'
Well = Plate + '%s/experiment/'
Site = Well + '%s/position/%s'


LayoutDtype = np.dtype(
    [('File', 'S10'), ('Well', 'S3'), ('Site', '<i8'),
     ('Row', 'S1'), ('Column', '<i8'), ('GeneSymbol', 'S6'),
     ('siRNA', 'S8'), ('Group', 'S10')])


def mergeHdfFiles(target, source_dir, remove_source=True, mode="a"):

    hdffiles = glob.glob(os.path.join(source_dir, '*.ch5'))
    target = h5py.File(target, mode=mode)

    for i, h5 in enumerate(hdffiles):
        source = h5py.File(h5, 'r')

        if i == 0:
            target.copy(source['/layout'], '/layout')
            target.copy(source['/definition'], "/definition")

        first_item = lambda view: next(iter(view))
        plate = first_item(source[Plate].keys())
        well = first_item(source[Well % plate].keys())
        position = first_item(source[Site %(plate, well, "")].keys())

        path_ = Site %(plate, well, position)

        for group in source[path_].keys():
            path = "%s/%s" %(path_, group)
            target.copy(source[path], path)

        source.close()

        if remove_source:
            os.remove(h5)

    target.close()


class FileLock(filelock.FileLock):

    def release(self, *args, **kw):

        # XXX Dirty work around for the cluster
        try:
            super(FileLock, self).release(*args, **kw)
        except IOError as e:
            pass

        if not self.is_locked:
            try:
                os.remove(self.lock_file)
            except OSError:
                pass


class Ch5File(CH5FileWriter):

    # this init is a dirty hack.
    # Cellh5 tries to load positions (sites) automatically, which are
    # not present.
    def __init__(self, filename, timeout=60, mode='a', cached=False):

        self.lock = FileLock(filename.replace("ch5", "lock"))
        try:
            self.lock.acquire(timeout=timeout)
        except filelock.Timeout as e:
            raise IOError("Cannot open hdf file %s" %(str(e)))

        self._cached = cached
        if isinstance(filename, basestring):
            self.filename = filename
            self._file_handle = h5py.File(filename, mode)
        else:
            self._file_handle = filename
            self.filename = filename.filename

        self._f = self._file_handle

        try:
            self.plate = self._get_group_members('/sample/0/plate/')[0]
            self.wells = self._get_group_members(
                '/sample/0/plate/%s/experiment/' % self.plate)
            self.positions = collections.OrderedDict()
            for w in sorted(self.wells):
                self.positions[w] = self._get_group_members(
                    '/sample/0/plate/%s/experiment/%s/position/' %(self.plate, w))
        except KeyError:
            return

        self._position_group = {}
        self._coordinates = []
        for well, positions in self.positions.iteritems():
            for pos in positions:
                self._coordinates.append(
                    CH5PositionCoordinate(self.plate, well, pos))
                self._position_group[(well, pos)] = self._open_position(
                    self.plate, well, pos)
        self.current_pos = self._position_group.values()[0]

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

    def savePlateLayout(self, layout, platename):
        """Save experimental layout for using the platename."""

        if isinstance(layout, basestring):
            layout = Ch5File.layoutFromTxt(layout)

        grp = self._file_handle.require_group(CH5Const.LAYOUT)

        if platename not in grp:
            dset = grp.create_dataset(platename, data=layout)

    @staticmethod
    def layoutFromTxt(filename):
        """Read plate layout from text file and return a structured array."""

        if not os.path.isfile(filename):
            msg = "No Plate Layout provided. File not found {}".format(filename)
            raise IOError(msg)

        try:
            rec = np.recfromtxt(filename, dtype=LayoutDtype, skip_header=True)
        except ValueError:
            rec = np.recfromtxt(filename, dtype=LayoutDtye, delimiter="\t", skip_header=True)

        return rec

    def createSite(self, filename):
        """Create an empty group for a Site."""

        sf = h5py.File(filename, "r")
        plate = sf[Plate].keys()[0]
        well = sf[Well %plate].keys()[0]
        site = sf[Site[:-2] %(plate, well)].keys()[0]
        path = Site %(plate, well, site)
        sf.close()

        if not path in self._file_handle:
            self._file_handle.create_group(path)

    def existingSites(self, plate):

        wsites = dict()

        try:
            wells = self[Well %plate].keys()
            for well in wells:
                sites = self[Site[:-2] %(plate, well)]
                # remove empty sites from list
                sites = [k for k, s in sites.items() if len(s.keys()) > 0]
                wsites[well] = sites
        except (KeyError, AttributeError, RuntimeError):
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
