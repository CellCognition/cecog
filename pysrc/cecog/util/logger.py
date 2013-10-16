# -*- coding: utf-8 -*-
"""
logger.py - logging at class level
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["LoggerObject"]

import os
import sys
import logging

class LoggerObject(object):
    """Parent for classes with logging capability"""

    _fmt = '%(asctime)s %(name)-24s %(levelname)-6s %(message)s'

    class _lvl(object):
        """Log levels"""
        WARN = logging.WARN
        WARNING = logging.WARNING
        ERROR = logging.ERROR
        CRITICAL = logging.CRITICAL
        INFO = logging.INFO
        DEBUG = logging.DEBUG
        NOTSET = logging.NOTSET

    def __init__(self, *args, **kw):
        super(LoggerObject, self).__init__(*args, **kw)

        # FIXME - special casing to get it running for
        # multiprocessing
        if self.__class__.__name__.startswith("PositionAnalyzer"):
            name = str(os.getpid())
        else:
            name = "%s_pid.%d" %(self.__class__.__name__, os.getpid())

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.NOTSET)
#        self.add_stream_handler()

    def add_stream_handler(self, level=logging.DEBUG):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._stream_handler.setLevel(level)
        fmt = logging.Formatter(self._fmt)
        self._stream_handler.setFormatter(fmt)
        self.logger.addHandler(self._stream_handler)

    def add_file_handler(self, logfile, level=logging.DEBUG):
        assert isinstance(logfile, basestring)
        self.logger.setLevel(level)
        fmt = logging.Formatter(self._fmt)
        self._file_handler = logging.FileHandler(logfile, 'w')
        self._file_handler.setLevel(level)
        self._file_handler.setFormatter(fmt)
        self.logger.addHandler(self._file_handler)

    def close(self):
        self._file_handler.close()
        self.logger.removeHandler(self._file_handler)        
        
