"""
setup.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import os
import sys
sys.path.append(os.path.join(os.pardir, 'pysrc'))

from distutils.core import setup
from cecog import VERSION, VERSION_NUM

if '--prefix' in sys.argv:
    install_opts = {'install_purelib': sys.argv[sys.argv.index('--prefix')+1]}
else:
    raise RuntimeError("option '--prefix <directory>' is mandatory")

setup(name="CecogClusterGateway",
      version = VERSION,
      author = 'Rudolf Hoefler',
      author_email = 'rudolf.hoefler@gmail.com',
      license = 'LGPL',
      description = 'Service to submit jobs from CecogAnalyzer',
      url = 'http://www.cellcognition.org',
      platforms = 'Linux',
      py_modules = ['gateway','cecog.__init__', 'cecog.util.util'],
      package_dir = {'cecog': os.path.join(os.pardir, 'pysrc', 'cecog')},
      data_files = ['cecog-gateway', 'readme.txt', 'cellcognition.albert',
                    'cellcognition.haring'],
      options = {'install': install_opts}
)
