# -*- coding: utf-8 -*-
"""
stopwatch.py - provide simple time measurement capability

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import time
from collections import OrderedDict

class StopWatch(object):
    """StopWatch holds the start time, interims and end total time."""

    START = 0
    STOP = "STOP"

    def __init__(self, start=False, name=""):
        self.name = name
        self._times = OrderedDict()

        if start:
            self.start()

    def start(self):
        self._times[self.START] = time.time()

    def stop(self):
        self._times[self.STOP] = time.time()
        return self.total

    def interim(self):
        i = len(self._times)
        self._times[i] = time.time()
        return self._times[i] - self.start_time

    def interval(self):
        i = len(self._times)
        self._times[i] = time.time()
        return self._times[i] - self._times[i-1]

    def reset(self, start=False):
        self._times = OrderedDict()
        if start:
            self.start()

    @property
    def total(self):
        return self.stop_time - self.start_time

    @property
    def start_time(self):
        try:
            return self._times[self.START]
        except KeyError:
            raise RuntimeError('Stopwatch was not started')

    @property
    def stop_time(self):
        try:
            return self._times[self.STOP]
        except KeyError:
            raise RuntimeError('Stopwatch still running')

    @property
    def interims(self):
        return self._times
