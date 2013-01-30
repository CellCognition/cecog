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

from xml.dom.minidom import parse
from pdk.ordereddict import OrderedDict

class CellCounterReader(OrderedDict):

    def __init__(self, regex_result, strFilename, reference,
                 strFieldDelimiter='\t', scale=1.0, timelapse=True):
        super(CellCounterReader, self).__init__()
        self.regex_result = regex_result
        self.strFilename = strFilename
        self._strFieldDelimiter = strFieldDelimiter
        self._fScale = float(scale)
        self._oReference = reference
        if timelapse:
            iOffset = self._oReference.index(self.getTimePoint())
        else:
            iOffset = self._oReference.index(self.getPosition())

        self._importData(iOffset)
        self.sort()

    def _importData(self, iOffset):
        self._oTable = importTable(self.strFilename,
                                   fieldDelimiter=self._strFieldDelimiter)
        for oRecord in self._oTable:
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

    def __init__(self, regex_result, strFilename, reference,
                 scale=1.0, timelapse=True):
        super(CellCounterReaderXML, self).__init__(regex_result,
                                                   strFilename,
                                                   reference,
                                                   scale=scale,
                                                   timelapse=timelapse)

    def _importData(self, iOffset):
        oDom = parse(self.strFilename)
        for oMarkerType in oDom.getElementsByTagName('Marker_Type'):
            iMarkerType = int(oMarkerType.getElementsByTagName('Type')[0].childNodes[0].data)

            for oMarker in oMarkerType.getElementsByTagName('Marker'):
                iX = int(oMarker.getElementsByTagName('MarkerX')[0].childNodes[0].data)
                iY = int(oMarker.getElementsByTagName('MarkerY')[0].childNodes[0].data)
                iZ = int(oMarker.getElementsByTagName('MarkerZ')[0].childNodes[0].data)

                try:
                    idx = self._oReference[iZ - 1 + iOffset]
                except IndexError:
                    pass
                else:
                    if not idx in self:
                        self[idx] = []
                    self[idx].append(dict([('iClassLabel', iMarkerType),
                                           ('iPosX', int(iX / self._fScale)),
                                           ('iPosY', int(iY / self._fScale))])
                                     )
