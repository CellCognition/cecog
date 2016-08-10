"""
time.py
"""
from __future__ import absolute_import

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["TimeConverter"]

import datetime

def seconds2datetime(seconds):
    secs = int(seconds % 60)
    minutes = int(((seconds - secs)/60) % 60)
    hours = int((seconds - minutes*60 - secs)/3600)
    return datetime.time(hour=hours, minute=minutes, second=secs)

class TimeConverter(object):
    """Convert time units from frames to minutes or seconds and vice versa."""

    MINUTES = 'minutes'
    FRAMES = 'frames'
    SECONDS = 'seconds'

    units = (FRAMES, MINUTES, SECONDS)

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
