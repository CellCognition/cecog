"""
datafiles.py - collect resources for distutils setup
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['get_data_files', 'find_uifiles',
           'INCLUDES', 'EXCLUDES', 'CC_INCLUDES',
           'TARGET_BUNDLE', 'TARGET_SYS']

import os
import glob
import numpy.distutils
import matplotlib
from os.path import basename, join, abspath, dirname, isfile

import PyQt5

TARGET_BUNDLE = 'resources'
TARGET_SYS = join('share', 'cellcognition', 'resources')
RESOURCE_DIR = 'resources'


_rsc = ('naming_schemas.ini', 'path_mappings.txt', 'font12.png')
_rsc = [join(abspath(RESOURCE_DIR), basename(rf)) for rf in _rsc]

_palettes = join(RESOURCE_DIR, 'palettes', 'zeiss')
_battery_package = join(RESOURCE_DIR, 'battery_package')

# for py2app and py2exe
INCLUDES = [ 'sip',
             'h5py.*',
             'scipy.sparse.csgraph._validation',
             'scipy.spatial.kdtree',
             'scipy.sparse.csgraph._shortest_path',
             'scipy.special._ufuncs',
             'scipy.special._ufuncs_cxx',
             'sklearn.utils.sparsetools._graph_validation',
             'cellh5',
             'ontospy',
             'rdflib',
             'rdflib.plugins.memory',
             'rdflib.plugins.parsers.rdfxml',
             'sklearn.utils.lgamma',
             'sklearn.neighbors.typedefs',
             'sklearn.utils.weight_vector' ]

EXCLUDES = [#'PyQt5.QtDesigner', 'PyQt5.QtNetwork',
            #'PyQt5.QtOpenGL', 'PyQt5.QtScript',
            #'PyQt5.QtTest', 'PyQt5.QtWebKit', 'PyQt5.QtXml', 'PyQt5.phonon',
            'PyQt4.QtCore', 'PyQt4.QtGui',  'PyQt4.QtSvg', 'PyQt4',
            '_gtkagg', '_cairo', '_gtkcairo', '_fltkagg',
            '_tkagg',
            'Tkinter',
            'zmq',
            'wx']

CC_INCLUDES = ['csrc/include'] + \
    numpy.distutils.misc_util.get_numpy_include_dirs()

def find_uifiles(package_dir, target_dir=TARGET_BUNDLE):
    uifiles = list()
    uidir = join(RESOURCE_DIR, 'ui')
    for root, dirs, files in os.walk(package_dir):
        for file_ in files:
            print file_
            if file_.endswith('.ui'):
                uifiles.append(join(root, file_))

    return (uidir, uifiles)


def get_data_files(target_dir=TARGET_BUNDLE,
                   mpl_data=True, qt_plugins=True):
    """Pack data files into list of (target-dir, list-of-files)-tuples"""

    dfiles = []
    if mpl_data:
        dfiles.extend(matplotlib.get_py2exe_datafiles())

    paltarget = join(target_dir, 'palettes', 'zeiss')
    dfiles.append((target_dir, _rsc))
    dfiles.append((paltarget, glob.glob(join(abspath(_palettes), '*.zip'))))
    # schema files
    dfiles.append((join(target_dir, 'schemas'),
                   glob.glob(join(RESOURCE_DIR, 'schemas', "*.xsd"))))
    dfiles.append((join(target_dir, 'ontologies'),
                   glob.glob(join(RESOURCE_DIR, 'ontologies', "*.owl"))))

    for root, subdirs, files in os.walk(_battery_package):
        for file_ in files:
            if file_ not in (".git", ):
                target = root.replace(RESOURCE_DIR, target_dir)
                dfiles.append((target, [join(abspath(root), file_)]))

    if qt_plugins:
        for dir_ in ['sqldrivers', 'platforms']:
            # Pyqt5 does not start without platform plugins.
            # sorry for not finding a better hack
            qt5plugins = glob.glob(
                join(dirname(PyQt5.__file__), "plugins", dir_, "*.*"))
            qt5plugins = (dir_, qt5plugins)
            dfiles.append(qt5plugins)

        # suddenly py2exe decide to not find this dll
        for dll in ("libEGL.dll", ):
            dll_ = join(dirname(PyQt5.__file__), dll)

            if not isfile(dll_):
                raise RunTimeError("Could not find file %s" %dll)
            dfiles.append(dll_)


    # qt help files
    dfiles.append((join(target_dir, 'doc'),
                   glob.glob(join(RESOURCE_DIR, 'doc', "*.qhc"))))
    dfiles.append((join(target_dir, 'doc'),
                   glob.glob(join(RESOURCE_DIR, 'doc', "*.qch"))))

    return dfiles
