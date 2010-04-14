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

import logging, \
       types

#-------------------------------------------------------------------------------
# extension module imports:
#

from pdk.options import Option
from pdk.optionmanagers import OptionManager


#-------------------------------------------------------------------------------
# functions:
#

def hexToRgb(string):
    hex = eval(string.replace('#','0x'))
    b = hex & 0xff
    g = hex >> 8 & 0xff
    r = hex >> 16 & 0xff
    return (r,g,b)

def rgbToHex(r,g,b, scale=1):
    r,g,b = [int(x*float(scale)) for x in (r,g,b)]
    return "#%s" % "".join(map(lambda c: hex(c)[2:].zfill(2), (r, g, b)))


def read_table(filename, has_column_names=True, sep='\t'):
    '''
    Reads a list of dicts ordered by header_names to file.
    Unfortunately Python's csv is unable of writing headers.
    '''
    f = file(filename, 'r')
    if has_column_names:
        column_names = f.readline().strip().split(sep)
    else:
        column_names = None
    rows = []
    for line in f:
        items = line.strip().split(sep)
        if column_names is None:
            column_names = range(len(items))
        rows.append(dict(zip(column_names, items)))
    f.close()
    return column_names, rows

def write_table(filename, rows, column_names=None, sep='\t'):
    '''
    Write a list of dicts ordered by header_names to file, or a list of lists
    if no column_names are specified.

    Unfortunately Python's csv is unable of writing headers.
    '''
    f = file(filename, 'w')
    if not column_names is None:
        f.write('%s\n' % sep.join(column_names))
        for row in rows:
            f.write('%s\n' % sep.join([str(row[n]) for n in column_names]))
    else:
        for row in rows:
            if type(row) == types.DictType:
                func = lambda x: x.values()
            else:
                func = lambda x: x
            f.write('%s\n' % sep.join(map(str, func(row))))
    f.close()


#-------------------------------------------------------------------------------
# classes:
#


class ReverseDict(dict):

    def __init__(self, dataD={}):
        super(ReverseDict, self).__init__(dataD)
        self._reverseD = {}
        for k, v in self.iteritems():
            if not v in self._reverseD:
                self._reverseD[v] = k

    def __call__(self):
        return self._reverseD


class LoggerMixin(OptionManager):

    OPTIONS = {"strLoggerName": Option("", callback="_onLoggerName"),
              }

    def __init__(self, **dctOptions):
        super(LoggerMixin, self).__init__(**dctOptions)

    def _onLoggerName(self, strLoggerName):
        self.oLogger = logging.getLogger(strLoggerName)

