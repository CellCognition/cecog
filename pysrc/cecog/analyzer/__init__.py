"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = []

CONTROL_1 = 'CONTROL_1'
CONTROL_2 = 'CONTROL_2'

FEATURE_CATEGORIES = ['roisize',
                      'circularity',
                      'irregularity',
                      'irregularity2',
                      'axes',
                      'normbase',
                      'normbase2',
                      'levelset',
                      'convexhull',
                      'dynamics',
                      'granulometry',
                      'distance',
                      'moments']


ZSLICE_PROJECTION_METHODS = ['maximum', 'average']

COMPRESSION_FORMATS = ['raw', 'bz2', 'gz']
TRACKING_METHODS = ['ClassificationCellTracker',]
TRACKING_DURATION_UNIT_FRAMES = 'frames'
TRACKING_DURATION_UNIT_MINUTES = 'minutes'
TRACKING_DURATION_UNIT_SECONDS = 'seconds'
TRACKING_DURATION_UNITS_DEFAULT = [TRACKING_DURATION_UNIT_FRAMES]

TRACKING_DURATION_UNITS_TIMELAPSE = [TRACKING_DURATION_UNIT_FRAMES,
                                     TRACKING_DURATION_UNIT_MINUTES,
                                     TRACKING_DURATION_UNIT_SECONDS]

R_LIBRARIES = ['hwriter', 'igraph']


class TimeUnit(object):
    """Convert time units from frames to minutes or seconds and vice versa."""

    MINUTES = 'minutes'
    FRAMES = 'frames'
    SECONDS = 'seconds'

    def __init__(self, timelapse, unit):

        if unit not in (self.MINUTES, self.SECONDS):
            msg = ("use TimeUnit.FRAMES, TimeUnit.MINUTES or TimeUnit.Seconds",
                   "to set the correct unit")
            raise RuntimeError(msg)
        self._unit = unit

        if not isinstance(timelapse, float):
            raise RuntimeError("provide a float as timelapse")

        # convert unit strait to seconds
        if unit == self.MINUTES:
            self._timelapse = timelapse*60.0
        else:
            self._timelapse = timelapse

    @staticmethod
    def sec2min(secs):
        return secs/60.0

    @staticmethod
    def min2secs(minutes):
        return minutes/60.0

    def frames2minutes(self, frames):
        return frames*self._timelapse/60.0

    def frames2seconds(self, frames):
        return frames*self._timelapse

    def minutes2frames(self, minutes):
        return minutes*60.0/self._timelapse

    def seconds2frames(self, seconds):
        return seconds/self._timelapse

    def any2frames(self, time, unit):

        if unit not in (self.MINUTES, self.SECONDS):
            raise RuntimeError("Use eg. TimeUnit.SECONDS as units")

        if unit == self.MINUTES:
            return minutes2frames(time)
        else:
            return seconds2frames(time)

    def frames2any(self, frames, unit):

        if unit not in (self.MINUTES, self.SECONDS):
            raise RuntimeError("Use eg. TimeUnit.SECONDS as units")

        if unit == self.MINUTES:
            return self.frames2minutes(frames)
        else:
            return self.frames2seconds(frames)
