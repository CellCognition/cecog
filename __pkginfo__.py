"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""
# many thanks for inspiration to F. Oliver Gathmann from the pyVIGRA project


from setuptools import find_packages

name = 'cecog'
numversion = (0, 0, 1)
version = '.'.join([str(digit) for digit in numversion])
author='Michael Held, ...'
author_email='held(at)cellcognition.org'
license='LGPL',
description = 'Fast bio-image processing framework.'
long_description = \
"""
"""
url = 'http://www.cellcognition.org'
download_url='https://www.cellcognition.org/downloads/cecog'
package_dir={'' : 'pysrc'}
packages = find_packages('pysrc')
classifiers = ['Development Status :: 4 - Beta',
               'Intended Audience :: Developers',
               'License :: OSI Approved :: LGPL License',
               'Operating System :: MacOS',
               'Operating System :: Microsoft',
               'Operating System :: POSIX :: Linux',
               'Programming Language :: C++',
               'Programming Language :: Python',
               'Topic :: Scientific/Engineering :: Image Recognition',
               ]
platforms=['Win32', 'Linux', 'Mac OS-X']
provides=['cecog']
