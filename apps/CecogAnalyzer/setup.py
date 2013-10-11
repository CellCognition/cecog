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

#-------------------------------------------------------------------------------
# standard library imports:
#
from setuptools import setup
import shutil
import os
import sys
import matplotlib
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

INCLUDES = [ 'sip',
             'scipy.sparse.csgraph._validation',
             'scipy.spatial.kdtree',
             'scipy.sparse.csgraph._shortest_path',
             'sklearn.utils.sparsetools._graph_validation',
             'sklearn.utils.lgamma',
             'sklearn.neighbors.typedefs',
             'sklearn.utils.weight_vector']

EXCLUDES = ['PyQt4.QtDesigner', 'PyQt4.QtNetwork',
            'PyQt4.QtOpenGL', 'PyQt4.QtScript',
            'PyQt4.QtSql', 'PyQt4.QtTest',
            'PyQt4.QtWebKit', 'PyQt4.QtXml',
            'PyQt4.phonon',
            'rpy',
            '_gtkagg', '_tkagg', '_agg2', '_cairo', '_cocoaagg',
            '_fltkagg', '_gtk', '_gtkcairo',
            'Tkconstants', 'Tkinter', 'tcl', 'zmq']

PACKAGES = ['cecog', 'h5py', 'vigra', 'matplotlib']

DLL_EXCLUDES = [ 'libgdk-win32-2.0-0.dll',
                 'libgobject-2.0-0.dll',
                 'libgdk_pixbuf-2.0-0.dll',
                 'w9xpopen.exe' ] # is not excluded for some reason

RESOURCE_FILES = [ANALYZER_CONFIG_FILENAME, FONT12_FILENAME,
                   NAMING_SCHEMA_FILENAME, PATH_MAPPING_FILENAME]

DATA_FILES = matplotlib.get_py2exe_datafiles()

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

pkginfo = read_pkginfo_file(__file__)

# delete target folder before execution of py2app
for path in ['dist', 'build']:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)

if sys.platform == 'darwin':
    OPTIONS = {'app' : APP}
    SYSTEM = 'py2app'
    EXTRA_OPTIONS = {'argv_emulation': False,
                     'includes': INCLUDES,
                     'excludes': EXCLUDES,
                     'dylib_excludes': ['R.framework',],
                     #'frameworks': ['R.framework',],
                     'strip' : True,
                     'packages': PACKAGES,
                     'resources': [],
                     'optimize': 2,
                     'compressed': False,
                     'skip_archive': True,
                     'iconfile': 'resources/cecog_analyzer_icon.icns',
                    }
elif sys.platform == 'win32':
    import py2exe # pylint: disable-msg=F0401,W0611
    FILENAME_ZIP = 'data.zip'
    OPTIONS = {'windows': [{'script': MAIN_SCRIPT,
                            'icon_resources': \
                               [(1, r'resources\cecog_analyzer_icon.ico')],
                           }],
               # FIXME: the one-file version is currently not working!
               'zipfile' : FILENAME_ZIP,
               }
    SYSTEM = 'py2exe'
    EXTRA_OPTIONS = {'includes': INCLUDES,
                     'excludes': EXCLUDES,
                     'packages': PACKAGES,
                     'dll_excludes': DLL_EXCLUDES,
                     'optimize': 1, #don't strip doc strings
                     'compressed': False,
                     'skip_archive': False,
                     'bundle_files': 3,
                    }

elif sys.platform.startswith('linux'):
    from cx_Freeze import setup, Executable
    FILENAME_ZIP = 'data.zip'
    OPTIONS = {'executables':[Executable(MAIN_SCRIPT,initScript = None,)]}
    SYSTEM = 'cx_Freeze'
    EXTRA_OPTIONS = {'includes': INCLUDES,
                     'excludes': EXCLUDES,
                     'packages': PACKAGES,
                     'optimize': 2,
                     'compressed': False,
                     'skip_archive': True,
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
    filenames = ['graph_template.txt',
                 'hmm.R',
                 'hmm_report.R',
                 'run_hmm.R']
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

    # copy vigranumpycory to correct filename
    shutil.copy(os.path.join('dist', 'vigra.vigranumpycore.pyd'),
                os.path.join('dist', 'vigranumpycore.pyd'))

    shutil.copytree(os.path.join(RESOURCE_PATH, 'palettes', 'zeiss'),
                    os.path.join(resource_path, 'palettes', 'zeiss'))

    w9 = os.path.join('dist', 'w9xpopen.exe')
    if os.path.isfile(w9):
        os.remove(w9)

elif sys.platform.startswith('linux'):
    filenames = ['graph_template.txt',
                 'hmm.R',
                 'hmm_report.R',
                 'run_hmm.R',
                 ]
    resource_path = os.path.join('build/exe.linux-x86_64-2.7', 'resources')
    target = os.path.join(resource_path, 'rsrc', 'hmm')
    safe_mkdirs(target)
    for filename in filenames:
        print target
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

try:
    shutil.copytree(os.path.join(RESOURCE_PATH, 'battery_package', 'Classifier'),
                    os.path.join(resource_path, 'battery_package', 'Classifier'))
    shutil.copytree(os.path.join(RESOURCE_PATH, 'battery_package', 'Images'),
                    os.path.join(resource_path, 'battery_package', 'Images'))
    shutil.copytree(os.path.join(RESOURCE_PATH, 'battery_package', 'Settings'),
                    os.path.join(resource_path, 'battery_package', 'Settings'))
except:
    print 'No battery_package data found in resource folder to include in dist package.\nTry adding "git submodule update --init"'
