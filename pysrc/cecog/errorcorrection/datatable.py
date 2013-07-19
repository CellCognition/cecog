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

    def add_track(self, track, prob, pos, mapping, gallery_file):
        if self._probs is None and self._tracks is None:
            self._tracks = np.empty(track.shape, dtype=int)[np.newaxis, :]
            self._tracks[0, :] = track[:]
            self._probs = np.empty(prob.shape)[np.newaxis, :, :]
            self._probs[0, :, :] = prob[:, :]
            self._gallery_files = np.array([gallery_file])

            self._pos[pm.POSITION] = np.array([pos])
            try:
                for k, v in mapping.iteritems():
                    self._pos[k] = np.array([v])
            except AttributeError:
                pass

        else:
            assert track.shape == self._tracks.shape[1:]
            assert prob.shape == self._probs.shape[1:]
            self._tracks = np.vstack((self._tracks, track[np.newaxis, ::]))
            self._probs = np.vstack((self._probs, prob[np.newaxis,::]))
            self._gallery_files = np.concatenate((self._gallery_files, [gallery_file]))
            self._pos[pm.POSITION] = np.concatenate((self._pos[pm.POSITION], np.array([pos])))
            try:
                for k, v in mapping.iteritems():
                    self._pos[k] = np.concatenate((self._pos[k], np.array([v])))
            except AttributeError:
                pass

    @property
    def ntracks(self):
        """Total number of tracks."""
        return self._tracks

    @property
    def probabilities(self):
        return self._probs

    def groups(self, key, name):
        """Plate mapping for a destinct sorting scheme (key) and name."""
        grps = dict()
        for k, v in self._pos.iteritems():
            grps[k] = v[self._pos[key] == name][0]
        return grps

    def ntracks_of_group(self, key):
        """Number of tracks for a given key (position, gene, ...)"""
        return len(np.unique(self._pos[key]))

    def iterby(self, key):

        if not self._pos.has_key(key):
            raise StopIteration()

        for k in np.unique(self._pos[key]):
            i = (k == self._pos[key])
            yield k, self._tracks[i], self._probs[i], self._gallery_files[i]

    def iterpos(self):
        return self.iterby(pm.POSITION)

    def iteroligo(self):
        return self.iterby(pm.OLIGO)

    def itergene(self):
        return self.iterby(pm.GENE)
