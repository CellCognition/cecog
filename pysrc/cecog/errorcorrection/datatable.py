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
        self._gallery_files = None
        self._pos = dict()
        self._all_pos = dict()
        for cn in pm.colnames:
            self._all_pos.setdefault(cn, [])
            self._pos.setdefault(cn, [])

    def _update_pos(self, pos, mapping, concatenate=False):
        self._pos[pm.POSITION].append(pos)
        try:
            for k, v in mapping.iteritems():
                self._pos[k].append(v)
        except AttributeError:
            for cn in (cols for cols in pm.colnames if cols != pm.POSITION):
                self._pos[cn].append(None)

    def add_track(self, track, prob, pos, mapping, gallery_file):

        if self._probs is None and self._tracks is None:
            self._tracks = np.empty(track.shape, dtype=int)[np.newaxis, :]
            self._tracks[0, :] = track[:]
            self._probs = np.empty(prob.shape)[np.newaxis, :, :]
            self._probs[0, :, :] = prob[:, :]
            self._gallery_files = np.array([gallery_file])
            self._update_pos(pos, mapping, concatenate=False)
        else:
            assert track.shape == self._tracks.shape[1:]
            assert prob.shape == self._probs.shape[1:]
            self._tracks = np.vstack((self._tracks, track[np.newaxis, ::]))
            self._probs = np.vstack((self._probs, prob[np.newaxis,::]))
            self._gallery_files = np.concatenate( \
                (self._gallery_files, [gallery_file]))
            self._update_pos(pos, mapping, concatenate=True)

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

            if k not in self._pos[key] and include_empty_positions:
                yield (k, None, None, None)
            else:
                yield k, self._tracks[i], self._probs[i], self._gallery_files[i]
