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

#-------------------------------------------------------------------------------
# standard library imports:
#
from setuptools import find_packages

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog import (VERSION_NUM,
                   VERSION,
                   )

#-------------------------------------------------------------------------------
# constants:
#
name = 'CecogAnalyzer'
numversion = VERSION_NUM
version = VERSION
author = 'Michael Held'
author_email = 'held(at)cellcognition.org'
license = 'LGPL',
description = ''
long_description = \
"""
"""
url = 'http://www.cellcognition.org'
download_url = ''
package_dir = {}
packages = find_packages()
classifiers = []
platforms = ['Win32', 'Linux', 'Mac OS-X']
provides = ['cecog']
