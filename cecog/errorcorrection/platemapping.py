"""
platemapping.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['PlateMapping']

import csv
from os.path import isfile
from collections import OrderedDict
from cecog.io.hdf import LayoutDtype


class PlateMapping(OrderedDict):
    """Read/Write plate mappings files. Default for all positions is None.
    After reading, all values are set according to the file."""

    colnames = LayoutDtype.names

    FILE = colnames[0]
    WELL = colnames[1]
    SITE = colnames[2]
    ROW = colnames[3]
    COLUMN = colnames[4]
    GENE = colnames[5]
    SIRNA = colnames[6]
    GROUP = colnames[7]

    def __init__(self, layout):
        super(PlateMapping, self).__init__()

        for line in layout:
            wellsite = "%s_%02d" %(line[1], int(line[2]))
            self.setdefault(wellsite, None)

            dline = dict([(k, v) for k, v in zip(self.colnames[1:],
                                                 line.tolist()[1:])])
            self[wellsite] = dline
