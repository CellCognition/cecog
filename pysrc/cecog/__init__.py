"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

__all__ = ['VERSION',
           'VERSION_NUM',
           'PLUGIN_MANAGERS',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.config import (init_constants,
                          init_application_support_path)
#-------------------------------------------------------------------------------
# constants:
#
VERSION_NUM = (1, 2, 4)
VERSION = '.'.join([str(digit) for digit in VERSION_NUM])

HAS_GUI = False

JOB_CONTROL_SUSPEND = 'Suspend'
JOB_CONTROL_RESUME = 'Resume'
JOB_CONTROL_TERMINATE = 'Terminate'

SEGMENTATION_MANAGERS = []
PLUGIN_MANAGERS = []

init_application_support_path()
init_constants()

