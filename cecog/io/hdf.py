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
    target = Ch5File(target, mode=mode)

    for i, h5 in enumerate(hdffiles):
        source = Ch5File(h5, 'r')

        if i == 0:
            target.copy(source['/layout'], '/layout')
            target.copy(source['/definition'], "/definition")

        first_item = lambda view: next(iter(view))
        plate = first_item(source[Plate].keys())
        well = first_item(source[Well % plate].keys())
        position = first_item(source[Site %(plate, well, "")].keys())

        path = Site %(plate, well, position)
        target.copy(source[path], path)

        source.close()

        if remove_source:
            os.remove(h5)
            os.remove(h5.replace(".ch5", ".tmp"))

    target.close()

class TimeoutError(filelock.Timeout):
    pass

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

    # this class is a workaround of the broken cellh5 implemation.

    def __init__(self, filename, timeout=60, mode='a', cached=False):

        self.lock = FileLock(filename.replace("ch5", "lock"))
        try:
            self.lock.acquire(timeout=timeout)
        except filelock.Timeout as e:
            raise TimeoutError("Cannot open hdf file %s" %(str(e)))

        # cellh5 workaround
        self._cached = cached
        if isinstance(filename, basestring):
            self.filename = filename
            self._file_handle = h5py.File(filename, mode)
        else:
            self._file_handle = filename
            self.filename = filename.filename

        self._f = self._file_handle

    def iter_positions(self):

        if not hasattr(self, "positions"):
            self.plate = self._get_group_members('/sample/0/plate/')[0]
            self.wells = self._get_group_members(
                '/sample/0/plate/%s/experiment/' % self.plate)
            self.positions = collections.OrderedDict()
            for w in sorted(self.wells):
                self.positions[w] = self._get_group_members(
                    '/sample/0/plate/%s/experiment/%s/position/' %(self.plate, w))
            self._position_group = {}
            self._coordinates = []
            for well, positions in self.positions.iteritems():
                for pos in positions:
                    self._coordinates.append(
                        CH5PositionCoordinate(self.plate, well, pos))
                    self._position_group[(well, pos)] = self._open_position(
                        self.plate, well, pos)
                    self.current_pos = self._position_group.values()[0]

        for well, positions in self.positions.items():
            for pos in positions:
                yield self._position_group[(well, pos)]

    def __getitem__(self, key):
        return self._file_handle[key]

    def __setitem__(self, key, value):
        self._file_handle[key] = value

    def __delitem__(self, key):
        del self._file_handle[key]

    def copy(self, source, path):
        """Wrapper h5py's copy method."""
        self._file_handle.copy(source, path)

    def close(self):
        super(Ch5File, self).close()
        self.lock.release()

    def hasDefinition(self):
        """Check if file contains a experimental layout for a specific plate."""
        return CH5Const.DEFINITION in self._file_handle

    def plates(self):
        """Return a tuple of plate names."""
        return tuple(self[Plate])

    def layout(self, plate):
        path = "%s/%s" %(CH5Const.LAYOUT, plate)
        return self[path].value

    def hasLayout(self, plate):
        """Check if file contains a experimental layout for a specific plate."""
        return "%s/%s" %(CH5Const.LAYOUT, plate) in self._file_handle

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
            rec = np.recfromtxt(filename, dtype=LayoutDtype, delimiter="\t",
                                skip_header=True)

        return rec

    # def createSite(self, filename):
    #     """Create an empty group for a Site."""

    #     sf = h5py.File(filename, "r")
    #     plate = sf[Plate].keys()[0]
    #     well = sf[Well %plate].keys()[0]
    #     site = sf[Site[:-2] %(plate, well)].keys()[0]
    #     path = Site %(plate, well, site)
    #     sf.close()

    #     if not path in self._file_handle:
    #         self._file_handle.create_group(path)

    def existingSites(self, plate):

        wsites = dict()

        try:
            wells = self[Well %plate].keys()
            for well in wells:
                sites = self[Site[:-2] %(plate, well)]
                # remove empty sites from list
                sites = [k for k, s in sites.items() if len(s.keys()) > 0]
                wsites[well] = sites
        except (KeyError, AttributeError):
            pass

        return wsites

    def numberSites(self, plate):
        return sum([len(site) for site in self.existingSites(plate).values()])

    def numberSitesEmpty(self, plate):
        """Number of hdf groups created in the file. The groups might be still
        empty.
        """

        nsites = 0
        wells = self[Well %plate].keys()
        for well in wells:
            sites = self[Site[:-2] %(plate, well)]
            nsites += len(sites)

        return nsites
