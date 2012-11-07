# -*- coding: utf-8 -*-
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

__author__ = 'rudolf.hoefler@imba.gmail.com'

import os
import glob
import matplotlib
import colorbrewer
from os.path import basename, join
from cecog.traits.config import (ANALYZER_CONFIG_FILENAME,
                                 FONT12_FILENAME,
                                 NAMING_SCHEMA_FILENAME,
                                 PATH_MAPPING_FILENAME,
                                 RESOURCE_PATH)

_rfiles = ['graph_template.txt', 'hmm.R', 'hmm_report.R', 'run_hmm.R']
_rfiles = [join('..', '..', 'rsrc', 'hmm', rf) for rf in _rfiles]

_rsc = ( ANALYZER_CONFIG_FILENAME, FONT12_FILENAME,
         NAMING_SCHEMA_FILENAME, PATH_MAPPING_FILENAME )
_rsc = [join(RESOURCE_PATH, basename(rf)) for rf in _rsc]

_palettes = join(RESOURCE_PATH, 'palettes', 'zeiss')
_battery_package = join(RESOURCE_PATH, 'battery_package')

def get_data_files():
    """
    Returns a list of tuples to serve as argument for
    distutils.core.setup as 'data_files' argument
    """
    dfiles = matplotlib.get_py2exe_datafiles()
    dfiles.append(('colorbrewer/data',
                   [join(colorbrewer.__path__[0], 'data',
                         'ColorBrewer_all_schemes_RGBonly3.csv')]))
    dfiles.append((join(RESOURCE_PATH, 'rsrc', 'hmm'), _rfiles))
    dfiles.append((RESOURCE_PATH, _rsc))
    dfiles.append((_palettes, glob.glob(join(_palettes, '*.zip'))))

    for root, subdirs, files in os.walk(_battery_package):
        for file_ in files:
            if file_ not in (".git", ):
                dfiles.append((root, [join(root, file_)]))
    return dfiles
