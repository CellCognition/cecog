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
def stopwatch(func):
    def wrap(*args, **options):
        func_name = func.__name__
        s = StopWatch()
        logger = logging.getLogger()
        logger.debug('Start: %s' % func_name)
        result = func(*args, **options)
        logger.debug('Finish: %s, %s' % (func_name, s))
        return result
    return wrap

#-------------------------------------------------------------------------------
# classes:
#

#-------------------------------------------------------------------------------
# main:
#

