"""
datatable.py

Custumized data table for hmm error correction.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['HmmDataTable']

import numpy as np

from cecog.errorcorrection import PlateMapping as pm


class HmmDataTable(object):

    def __init__(self, *args, **kw):
        super(HmmDataTable, self).__init__(*args, **kw)
        self._probs = None
        self._tracks = None
        self._objids = None
        self._gallery_files = None
        self._pos = dict()
        self._all_pos = dict()
        for cn in pm.colnames:
            self._all_pos.setdefault(cn, [])
            self._pos.setdefault(cn, [])

    def _update_pos(self, pos, mapping, ntracks):
        self._pos[pm.POSITION].extend([pos]*ntracks)
        try:
            for k, v in mapping.iteritems():
                self._pos[k].extend([v]*ntracks)
        except AttributeError:
            for cn in (cols for cols in pm.colnames if cols != pm.POSITION):
                self._pos[cn].extend([None]*ntracks)

    def add_tracks(self, tracks, probs, pos, mapping, objids):

        if self._tracks is None and self._objids is None:
            self._tracks = tracks
            if probs is not None:
                self._probs = probs
            self._objids = objids
            self._update_pos(pos, mapping, tracks.shape[0])
        else:
            assert tracks.shape[1:] == self._tracks.shape[1:]
            self._tracks = np.vstack((self._tracks, tracks))
            if probs is not None:
                self._probs = np.vstack((self._probs, probs))
            self._objids = np.vstack((self._objids, objids))
            self._update_pos(pos, mapping, tracks.shape[0])

    def add_position(self, pos, mapping):
        self._all_pos[pm.POSITION].append(pos)
        try:
            for k, v in mapping.iteritems():
                self._all_pos[k].append(v)
        except AttributeError:
            for cn in pm.colnames:
                if cn is pm.POSITION:
                    continue
                self._all_pos[cn].append(None)

    @property
    def ntracks(self):
        """Total number of tracks."""
        return self._tracks.shape[0]

    def is_empty(self):
        if self._tracks is None:
            return True
        else:
            return False

    @property
    def probabilities(self):
        return self._probs

    def groups(self, key, name):
        """Plate mapping for a destinct sorting scheme (key) and name."""
        grps = dict()
        for k, v in self._pos.iteritems():
            try:
                grps[k] = v[self._pos[key].index(name)]
            except IndexError:
                grps[k] = None
        return grps

    def iterby(self, key, include_empty_positions=False):

        if not self._pos.has_key(key):
            raise StopIteration()

        for k in np.unique(self._all_pos[key]):
            if k is None: # no rich comparision here...
                i = np.array([v is None for v in self._pos[key]])
            else:
                i = (k == np.array(self._pos[key]))

            # return only the key, no tracks available
            if k not in self._pos[key] and include_empty_positions:
                yield (k, None, None, None)
            # tracks but no prediction probabilities
            elif self._probs is None:
                yield k, self._tracks[i], None, self._objids[i]
            # tracks with prediction probabilities
            else:
                yield k, self._tracks[i], self._probs[i], self._objids[i]
