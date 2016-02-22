"""
ues.py

Unsupervised event selection for the tc3 framework.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['TC3EventFilter']

import warnings
import numpy as np
from cecog.errorcorrection.hmm import MultinomialHMM

class TC3EventFilter(object):
    """Additional Event filter for unsupervised event selection:

    1) smooth trajectories using an hmm (k=2)
    2) find mitotic trajectories using various filter conditions
    """

    # event filter codes for method filter_stats
    EVENT = 0
    MITOTIC_FRAMES = 1
    PREEVENT_NOISE = 2
    EVENT_LENGTH = 3
    NOISE = 4

    def __init__(self, tracks, n_frames, event_start, event_tol,
                 n_clusters, verbose=False):
        self.verbose = verbose
        self.tracks = tracks
        self._filter_stats = []
        self.n_frames = n_frames
        self.event_start = event_start
        self.event_tol = event_tol
        self.n_clusters = n_clusters

    def __call__(self, outdir=None):

        self.tracks = self._smooth(self.tracks)
        if outdir is not None:
            np.savetxt(join(odir, "hmm.csv"),
                       tracks, fmt="%d", delimiter=",")

        self.tracks = self._assign_mitotic_labels(self.tracks)
        if outdir is not None:
            np.savetxt(join(odir, "assigned_tracks.csv"),
                       tracks, fmt="%d", delimiter=",")

        return self._filter(self.tracks)

    @property
    def filter_stats(self):
        return np.bincount(self._filter_stats)

    def _assign_mitotic_labels(self, labels):
        """Majority vote in the pre-duration.

        Assuming that most occouring event in the preduration is non-mitoic
        This criteria might fail if more that 50% are non-mitotic
        """
        pre = labels[:,:self.event_start]
        if pre[pre==0].size <= pre[pre==1].size:
            labels = np.where(labels, 0, 1)
        return labels

    def _smooth(self, tracks, maxiter=250):
        """Smooth trajectories using a MultinomialHMM.

        Fit the Multinomial hmm using all tracks, but prediction is performed
        on single tracks.
        """

        hmm_ = hmm.MultinomialHMM(n_components=2, n_iter=maxiter)
        # in newer version of hmm n_symbols can be set in the init method.
        hmm_.n_symbols = 2
        logprob = hmm_.fit(tracks)

        if self.verbose:
            print "# hmm iterations: ", len(logprob)
        if len(logprob) >= maxiter:
            warnings.warn("Warning: HMM is not converged after %d" %maxiter)
            warnings.resetwarnings()

        tracks2 = []
        for track in tracks:
            tracks2.append(hmm_.predict(track))
        return np.array(tracks2)

    def delete(self, array, axis=0):
        return np.delete(array, self._non_events, axis)

    def _filter(self, tracks):
        """Filter out all non mitotic events. If no valid event is found,
        _filter returns an array of zeros is returned."""

        non_events = []
        for i, track in enumerate(tracks):
            if not self._is_event(track):
                non_events.append(i)
        self._non_events = non_events

        ftracks = np.delete(tracks, non_events, 0)

        if not ftracks.size:
            ftracks = np.zeros(tracks.shape)

        return ftracks

    def _is_event(self, track):
        """Applys the filter condtions."""

        # min number of mitotic frames is n_clusters
        if track.sum() < self.n_clusters:
            self._filter_stats.append(self.MITOTIC_FRAMES)
            return False

        # no mitotic frames in before the transition
        # no noise in the before the transition
        if track[0:self.event_start-1].sum() > 0:
            self._filter_stats.append(self.PREEVENT_NOISE)
            return False

        # transition within certain frames
        if track[self.event_start:self.event_start+self.event_tol].sum() == 0:
            self._filter_stats.append(self.EVENT_LENGTH)
            return False

        # no noise in the tracks. This allows one transions from 0 to 1,
        # or 2, 3...
        if (np.diff(track) == 1).sum() > 1:
            self._filter_stats.append(self.NOISE)
            return False

        self._filter_stats.append(self.EVENT)
        return True
