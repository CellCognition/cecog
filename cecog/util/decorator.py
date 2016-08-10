"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import

__all__ = ['stopwatch']

import logging
from functools import wraps
from cecog.util.stopwatch import StopWatch

# def stopwatch(f):
#     """Simple decorator wrapping a function by measuring its execution time
#     and print result to a logger instance.
#     """
#     def wrap(*args, **options):
#         fname = f.__name__
#         sw = StopWatch(start=True)
#         logger = logging.getLogger()
#         logger.debug('%s start' % fname)
#         result = f(*args, **options)
#         logger.debug('%s finished: %s' % (fname, sw.stop()))
#         return result
#     return wrap


class stopwatch(object):
    """Decorator class for measuring the execution time of methods."""

    def __init__(self, level=logging.DEBUG):
        self._level = level

    def __call__(self, method):
        @wraps(method)
        def wrapped_f(*args, **options):
            _self = args[0]
            fname = method.__name__
            class_name = _self.__class__.__name__
            name = _self.name
            sw = StopWatch(start=True)
            logger = logging.getLogger()
            logger.log(self._level, '%s[%s].%s - start'
                       %(class_name, name, fname))
            result = method(*args, **options)
            logger.log(self._level, '%s[%s].%s - finished in %s'
                       %(class_name, name, fname, sw.stop()))
            return result
        return wrapped_f
