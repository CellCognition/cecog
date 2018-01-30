"""
setup_mac.py

Setup script for MacOSX.

Usage:
   python setup_mac.py py2app

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import os
from os.path import join
import py2app

from distutils.core import setup, Extension
import build_helpers

# override other -arch options
if not os.environ.has_key("ARCHFLAGS"):
    os.environ["ARCHFLAGS"] = "-arch x86_64"

py2app_opts = {'excludes': build_helpers.EXCLUDES,
               'includes': ['sip',
                            'PyQt5'
                            'PyQt5.Qt'
                            'PyQt5.QtCore',
                            'PyQt5.QtGui',
                            'PyQt5.QtWidgets'],
               "qt_plugins": ['platforms', 'sqldrivers'],
               "argv_emulation":False,
               "strip": True,
               "optimize": 1,
               "iconfile": "resources/cecog_analyzer_icon.icns",
               "packages": ["h5py","vigra","sklearn"],
               "arch": "x86_64",
               "matplotlib_backends": ["agg","qt5agg", "macosx"]}

pyrcc_opts = {'qrc': {'cecog.qrc' : join('cecog', 'cecog_rc.py'),
                      },
              'pyrccbin': 'pyrcc5'}

help_opts = {'infile': join('doc', 'manual.qhcp'),
             'outfile': join('resources', 'doc', 'manual.qhc'),
             'qcollectiongeneator': 'qcollectiongenerator'}

ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'cecog.cxx')],
                  libraries = ['vigraimpex', 'boost_python'],
                  include_dirs = build_helpers.CC_INCLUDES,
                  extra_object = ['tiff'],
                  extra_compile_args = ['-O3', '-fPIC'],
                  language = 'c++')


# python package to distribute
packages = build_helpers.find_submodules("./cecog", "cecog")
scripts = [join('scripts', 'CecogAnalyzer.py')]

dfiles = build_helpers.get_data_files(build_helpers.TARGET_BUNDLE)
# no ui files in package data for py2app
uifiles = build_helpers.find_uifiles('./cecog', build_helpers.TARGET_BUNDLE)
dfiles.append(uifiles)

setup(app = scripts,
      data_files = dfiles,
      options = {"py2app": py2app_opts,
                 "build_help": help_opts,
                 "build_rcc": pyrcc_opts},
      cmdclass = {'build_rcc': build_helpers.BuildRcc,
                  'build_help': build_helpers.BuildHelp,
                  'build': build_helpers.Build},
      packages = packages,
      setup_requires=['py2app'],
      ext_modules = [ccore],
      **build_helpers.metadata)
