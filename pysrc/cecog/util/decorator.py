"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['stopwatch']

#-------------------------------------------------------------------------------
# standard library imports:
#
import logging

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.datetimeutils import StopWatch

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#
def stopwatch(f):
    """
    Simple decorator wrapping a function by measuring its execution time and reporting to a logger
    """
    def wrap(*args, **options):
        fname = f.__name__
        s = StopWatch()
        logger = logging.getLogger()
        logger.debug('%s start' % fname)
        result = f(*args, **options)
        logger.debug('%s finished: %s' % (fname, s))
        return result
    return wrap

#-------------------------------------------------------------------------------
# classes:
#

#-------------------------------------------------------------------------------
# main:
#

