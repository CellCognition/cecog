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
from setuptools import setup
import shutil
import os
import sys

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.fileutils import safe_mkdirs, collect_files

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.config import (ANALYZER_CONFIG_FILENAME,
                                 FONT12_FILENAME,
                                 NAMING_SCHEMA_FILENAME,
                                 PATH_MAPPING_FILENAME,
                                 RESOURCE_PATH,
                                 )

#-------------------------------------------------------------------------------
# constants:
#
MAIN_SCRIPT = 'CecogAnalyzer.py'

APP = [MAIN_SCRIPT]
INCLUDES = ['sip', 'netCDF4_utils', 'netcdftime', ]
EXCLUDES = ['PyQt4.QtDesigner', 'PyQt4.QtNetwork',
            'PyQt4.QtOpenGL', 'PyQt4.QtScript',
            'PyQt4.QtSql', 'PyQt4.QtTest',
            'PyQt4.QtWebKit', 'PyQt4.QtXml',
            'PyQt4.phonon',
            'scipy', 'rpy',
            'Tkconstants', 'Tkinter', 'tcl',
            ]
PACKAGES = ['cecog', ]

RESOURCE_FILES = [ANALYZER_CONFIG_FILENAME,
                  FONT12_FILENAME,
                  NAMING_SCHEMA_FILENAME,
                  PATH_MAPPING_FILENAME,
                  ]

#-------------------------------------------------------------------------------
# functions:
#
def tempsyspath(path):
    def decorate(f):
        def handler():
            sys.path.insert(0, path)
            value = f()
            del sys.path[0]
            return value
        return handler
    return decorate

def read_pkginfo_file(setup_file):
    path = os.path.dirname(setup_file)
    @tempsyspath(path)
    def _import_pkginfo_file():
        if '__pgkinfo__' in sys.modules:
            del sys.modules['__pkginfo__']
        return __import__('__pkginfo__')
    return _import_pkginfo_file()

#-------------------------------------------------------------------------------
# main:
#
pkginfo = read_pkginfo_file(__file__)

# delete target folder before execution of py2app
for path in ['dist', 'build']:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)

if sys.platform == 'darwin':
    OPTIONS = {'app' : APP}
    SYSTEM = 'py2app'
    DATA_FILES = []
    EXTRA_OPTIONS = {'argv_emulation': False,
                     'includes': INCLUDES,
                     'excludes': EXCLUDES,
                     'dylib_excludes': ['R.framework',],
                     #'frameworks': ['R.framework',],
                     'strip' : False,
                     'packages': PACKAGES,
                     'resources': [],
                     'optimize': 0,
                     'compressed': False,
                     'iconfile': 'resources/cecog_analyzer_icon.icns',
                    }
elif sys.platform == 'win32':
    import py2exe # pylint: disable-msg=F0401,W0611
    FILENAME_ZIP = 'data.zip'
    #FILENAME_ZIP = 'CecogAnalyzer.exe'
    OPTIONS = {'windows': [{'script': MAIN_SCRIPT,
                            'icon_resources': \
                               [(1, r'resources\cecog_analyzer_icon.ico')],
                           }],
               # FIXME: the one-file version is currently not working!
               'zipfile' : FILENAME_ZIP,
               }
    SYSTEM = 'py2exe'
    DATA_FILES = []
    EXTRA_OPTIONS = {'includes': INCLUDES,
                     'excludes': EXCLUDES,
                     'packages': PACKAGES,
                     'optimize': 2,
                     'compressed': True,
                     'bundle_files': 3,

                     #'ascii': True,
                     #'xref': True,
                    }


setup(
    data_files=DATA_FILES,
    options={SYSTEM: EXTRA_OPTIONS},
    setup_requires=[SYSTEM],
    name=pkginfo.name,
    version=pkginfo.version,
    author=pkginfo.author,
    author_email=pkginfo.author_email,
    license=pkginfo.license,
    description=pkginfo.description,
    long_description=pkginfo.long_description,
    url=pkginfo.url,
    download_url=pkginfo.download_url,
    classifiers=pkginfo.classifiers,
    package_dir=pkginfo.package_dir,
    packages=pkginfo.packages,
    platforms=pkginfo.platforms,
    provides=pkginfo.provides,
    **OPTIONS
)


# post-processing steps for py2app /py2exe
if sys.platform == 'darwin':

    base_path = 'dist/CecogAnalyzer.app'

    # delete all Qt4 debug files
    target_path = os.path.join(base_path, 'Contents/Frameworks')
    filenames = collect_files(target_path, [], absolute=True, recursive=True)
    filenames = [x for x in filenames if 'debug' in os.path.split(x)[1]]
    for filename in filenames:
        if os.path.isdir(filename):
            shutil.rmtree(filename)
        elif os.path.isfile(filename):
            os.remove(filename)

    # one more special py2app hack forcing Qt to load libs from the app only!
    shutil.copy('qt.conf', os.path.join(base_path, 'Contents/Resources'))

    # delete .DS_Store files
    target = os.path.join(base_path, '')
    for filepath in collect_files(target, ['.DS_Store'],
                                  absolute=True, recursive=True):
        print filepath
        os.remove(filepath)

    # delete ALL .py files from lib (and use .pyc/.pyo instead)
    target = os.path.join(base_path, 'Contents/Resources/lib/python2.7/')
    for filepath in collect_files(target, ['.py'],
                                  absolute=True, recursive=True):
        filename = os.path.split(filepath)[1]
        if not filename in ['site.py', '__init__.py'] and os.path.isfile(filepath):
            os.remove(filepath)
    filenames = ['graph_template.txt',
                 'hmm.R',
                 'hmm_report.R',
                 'run_hmm.R',
                 ]

    cecog_pyd = os.path.join(target, 'cecog', 'ccore', '_cecog.pyd')
    if os.path.isfile(cecog_pyd):
        os.remove(cecog_pyd)

    resource_path = os.path.join(base_path, 'Contents/Resources/resources')
    target = os.path.join(resource_path, 'rsrc/hmm')
    safe_mkdirs(target)
    for filename in filenames:
        shutil.copy(os.path.join('../../rsrc/hmm', filename), target)

    for filename in RESOURCE_FILES:
        # make sure we use the unchanged versions from the repository
        filename = os.path.join('resources', os.path.split(filename)[1])
        print filename
        shutil.copy(filename, resource_path)

    shutil.copytree(os.path.join(RESOURCE_PATH, 'palettes', 'zeiss'),
                    os.path.join(resource_path, 'palettes', 'zeiss'))


elif sys.platform == 'win32':
#    import zipfile, glob
#    lib_filename = os.path.join('dist', FILENAME_ZIP)
#    zfile = zipfile.PyZipFile(lib_filename, 'a')
#    filenames = [r'C:\Source\Lib\libfftw3-3.dll',
#                 ] +\
#                 glob.glob(r'C:\Source\Microsoft.VC90.CRT\*.*')
#    for filename in filenames:
#        print "adding '%s' to '%s'" % (filename, lib_filename)
#        zfile.write(filename, os.path.split(filename)[1])
#    zfile.close()

    filenames = ['graph_template.txt',
                 'hmm.R',
                 'hmm_report.R',
                 'run_hmm.R',
                 ]
    resource_path = os.path.join('dist', 'resources')
    target = os.path.join(resource_path, 'rsrc', 'hmm')
    safe_mkdirs(target)
    for filename in filenames:
        shutil.copy(os.path.join('../../rsrc/hmm', filename), target)

    for filename in RESOURCE_FILES:
        # make sure we use the unchanged versions from the repository
        filename = os.path.join('resources', os.path.split(filename)[1])
        print filename
        shutil.copy(filename, resource_path)

    shutil.copytree(os.path.join(RESOURCE_PATH, 'palettes', 'zeiss'),
                    os.path.join(resource_path, 'palettes', 'zeiss'))

    w9 = os.path.join('dist', 'w9xpopen.exe')
    if os.path.isfile(w9):
        os.remove(w9)

