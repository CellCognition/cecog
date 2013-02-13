"""

                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See LICENSE.txt for details.
                 See AUTHORS.txt for author contributions.

datafiles.py - collect resources for distutils setup
"""

__author__ = 'rudolf.hoefler@imba.oeaw.ac.at'

import os
import glob
import matplotlib
from os.path import basename, join, abspath
from cecog.config import (ANALYZER_CONFIG_FILENAME,
                          FONT12_FILENAME,
                          NAMING_SCHEMA_FILENAME,
                          PATH_MAPPING_FILENAME,
                          RESOURCE_PATH)

_rfiles = ['graph_template.txt', 'hmm.R', 'hmm_report.R', 'run_hmm.R']
_rfiles = [join('..', '..', 'rsrc', 'hmm', _rf) for _rf in _rfiles]

_rsc = ( ANALYZER_CONFIG_FILENAME, FONT12_FILENAME,
         NAMING_SCHEMA_FILENAME, PATH_MAPPING_FILENAME )
_rsc = [join(abspath(RESOURCE_PATH), basename(rf)) for rf in _rsc]

_palettes = join(RESOURCE_PATH, 'palettes', 'zeiss')
_battery_package = join(RESOURCE_PATH, 'battery_package')

def get_data_files():
    """Pack data files into list of (target-dir, list-of-files)-tuples"""

    dfiles = matplotlib.get_py2exe_datafiles()
    dfiles.append((RESOURCE_PATH, _rsc))
    dfiles.append((join(RESOURCE_PATH, 'rsrc', 'hmm'), _rfiles))
    dfiles.append((_palettes, glob.glob(join(abspath(_palettes), '*.zip'))))

    for root, subdirs, files in os.walk(_battery_package):
        for file_ in files:
            if file_ not in (".git", ):
                dfiles.append((root, [join(abspath(root), file_)]))
    return dfiles
