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

__all__ = ('CHANNEL_PREFIX', )

# move this constants to version.py module

JOB_CONTROL_SUSPEND = 'Suspend'
JOB_CONTROL_RESUME = 'Resume'
JOB_CONTROL_TERMINATE = 'Terminate'

# XXX move this constants to the channels module
CH_PRIMARY = ["primary"]
CH_VIRTUAL = ["merged"]
CH_OTHER = ["secondary", "tertiary"]
CHANNEL_PREFIX = CH_PRIMARY + CH_OTHER + CH_VIRTUAL
