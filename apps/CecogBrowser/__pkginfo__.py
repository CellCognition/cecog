"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL license.
                     See the LICENSE.txt for details.

"""

from setuptools import find_packages

name = 'CecogBrowser'
numversion = (0, 1, 0)
version = '.'.join([str(digit) for digit in numversion])
author='Michael Held'
author_email='held@cellcognition.org'
license='LGPL'
description = 'A fast bio-image browser.'
long_description = \
"""
"""
url = 'http://trac.cellcognition.org'
download_url='https://www.cellcognition.org/downloads/cecogbrowser'
#package_dir={'' : 'pysrc'}
#packages = find_packages('pysrc')
classifiers = [
#               'Development Status :: 4 - Beta',
#               'Intended Audience :: Developers',
#               'License :: OSI Approved :: MIT License',
#               'Operating System :: MacOS',
#               'Operating System :: Microsoft',
#               'Operating System :: POSIX :: Linux',
#               'Programming Language :: C++',
#               'Programming Language :: Python',
#               'Topic :: Scientific/Engineering :: Image Recognition',
               ]
platforms=['Win32', 'Linux', 'Mac OS-X']
provides=['cecogbrowser']
