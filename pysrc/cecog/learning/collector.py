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

import os, \
       re, \
       logging
from xml.dom.minidom import parse

#-------------------------------------------------------------------------------
# extension module imports:
#

from numpy import asarray

from pdk.options import Option
from pdk.optionmanagers import OptionManager
#from pdk.containers.tableio import importTable, exportTable
#from pdk.containers.tablefactories import newTable
from pdk.ordereddict import OrderedDict


#-------------------------------------------------------------------------------
# cecog module imports:
#


#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#

class _Dimension(object):
    pass

class PlateDimension(_Dimension):

    def __init__(self):
        super(PlateDimension, self).__init__()

class PositionDimension(_Dimension):

    def __init__(self):
        super(PositionDimension, self).__init__()

class TimeDimension(_Dimension):

    def __init__(self):
        super(TimeDimension, self).__init__()

#
#
#
#class CellCounterReader(OrderedDict):
#
#    ANNOTATION_SUFFIXES = ['.tsv']
#
#    def __init__(self, path, positions, timepoints, axis='time'):
#        super(CellCounterReader, self).__init__()
#        self._path = path
#        self.positions = positions.copy()
#        self.timepoints = timepoints.copy()
#        self._reference = self.timepoints if axis == 'time' else self.positions
#        self._axis = axis
#        self._read_path()
#
#    def _read_path(self):
#        for filename in os.listdir(self._path):
#            file_path = os.path.join(self._path, filename)
#            exp_id = filename
#            if (os.path.isfile(file_path) and
#                os.path.splitext(filename)[1] in self.ANNOTATION_SUFFIXES):
#
#                table = importTable(file_path,
#                                    fieldDelimiter='\t')
#                table.sort(['Slice', 'Type'])
#                for record in table:
#                    idx = record['Slice'] - 1
#                    ref = self._reference[idx]
#                    if not ref in self:
#                        self[ref] = []
#                    self[ref].append({'label' : record['Type'],
#                                      'x'     : record['X'],
#                                      'y'     : record['Y']}
#                                      )
#
#            for ref in self._reference.copy():
#                if not ref in self:
#                    self._reference.remove(ref)
#



class CellCounterReader(OrderedDict):

    def __init__(self, regex_result, strFilename, reference, strFieldDelimiter='\t', scale=1.0, timelapse=True):
        super(CellCounterReader, self).__init__()
        self.regex_result = regex_result
        self.strFilename = strFilename
        self._strFieldDelimiter = strFieldDelimiter
        self._fScale = float(scale)
        self._oReference = reference
        if timelapse:
            iOffset = self._oReference.index(self.getTimePoint())
        else:
            #print reference
            #print self.getPosition()
            iOffset = self._oReference.index(self.getPosition())
        #print 'offset', iOffset

        self._importData(iOffset)
        self.sort()

    def _importData(self, iOffset):
        self._oTable = importTable(self.strFilename,
                                   fieldDelimiter=self._strFieldDelimiter)
        #self._oTable.sort(['Slice', 'Type'])
        for oRecord in self._oTable:
            #print reference, oRecord['Slice'] - 1 + offset
            try:
                idx = self._oReference[oRecord['Slice'] - 1 + iOffset]
            except IndexError:
                pass
            else:
                if not idx in self:
                    self[idx] = []
                self[idx].append(dict([('iClassLabel', int(oRecord['Type'])),
                                       ('iPosX', int(oRecord['X'] / self._fScale)),
                                       ('iPosY', int(oRecord['Y'] / self._fScale))])
                                 )

    def getPosition(self):
        return self.regex_result.group('position')

    def getTimePoint(self):
        return int(self.regex_result.group('time'))

    def getTimePoints(self):
        return self.keys()



class CellCounterReaderXML(CellCounterReader):

    def __init__(self, regex_result, strFilename, reference, scale=1.0, timelapse=True):
        super(CellCounterReaderXML, self).__init__(regex_result, strFilename, reference, scale=scale, timelapse=timelapse)

    def _importData(self, iOffset):

        oDom = parse(self.strFilename)
        for oMarkerType in oDom.getElementsByTagName('Marker_Type'):
            iMarkerType = int(oMarkerType.getElementsByTagName('Type')[0].childNodes[0].data)
            print 'type', iMarkerType

            for oMarker in oMarkerType.getElementsByTagName('Marker'):
                iX = int(oMarker.getElementsByTagName('MarkerX')[0].childNodes[0].data)
                iY = int(oMarker.getElementsByTagName('MarkerY')[0].childNodes[0].data)
                iZ = int(oMarker.getElementsByTagName('MarkerZ')[0].childNodes[0].data)

                try:
                    idx = self._oReference[iZ - 1 + iOffset]
                except IndexError:
                    pass
                else:
                    #print idx
                    if not idx in self:
                        self[idx] = []
                    self[idx].append(dict([('iClassLabel', iMarkerType),
                                           ('iPosX', int(iX / self._fScale)),
                                           ('iPosY', int(iY / self._fScale))])
                                     )
