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

__all__ = ['VERSION', 'VERSION_NUM', 'PLUGIN_MANAGERS',
           'CHANNEL_PREFIX', 'APPNAME']

# move this constants to version.py module
VERSION_NUM = (1, 3, 5)
VERSION = '.'.join([str(n) for n in VERSION_NUM])
APPNAME = 'CecogAnalyzer'

# XXX function in CecogEnvironment class
HAS_GUI = False

JOB_CONTROL_SUSPEND = 'Suspend'
JOB_CONTROL_RESUME = 'Resume'
JOB_CONTROL_TERMINATE = 'Terminate'

SEGMENTATION_MANAGERS = []
PLUGIN_MANAGERS = []

# XXX move this constants to the channels module
CH_PRIMARY = ["primary"]
CH_VIRTUAL = ["merged"]
CH_OTHER = ["secondary", "tertiary"]
CHANNEL_PREFIX = CH_PRIMARY + CH_OTHER + CH_VIRTUAL
