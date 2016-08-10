"""
annotations.py

Read and parse annotation files i.e. file that contain imformation the
training set withing the raw images
"""
from __future__ import absolute_import

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['Annotations']


from os.path import isfile
from xml.dom.minidom import parse
from collections import OrderedDict


class Annotations(OrderedDict):

    def __init__(self, regex, filename, reference, scale=1.0, timelapse=True):
        super(Annotations, self).__init__()

        if not filename.endswith("xml"):
            raise RuntimeError(("This classifier was trained with an outdated "
                                "version of CellCognition. You can retrain the "
                                "classifier or use the old version that you used "
                                "in the first place. Sorry."))

        if not isfile:
            raise IOError("File %s does not exist!")

        self.regex = regex
        self.filename = filename
        self._scale = float(scale)
        self._reference = reference

        if timelapse:
            offset = reference.index(self.timepoint())
        else:
            offset = reference.index(self.position())

        dom = parse(filename)
        for markertype in dom.getElementsByTagName('Marker_Type'):
            imt = int(markertype.getElementsByTagName('Type')[0].childNodes[0].data)

            for marker in markertype.getElementsByTagName('Marker'):
                iX = int(marker.getElementsByTagName('MarkerX')[0].childNodes[0].data)
                iY = int(marker.getElementsByTagName('MarkerY')[0].childNodes[0].data)
                iZ = int(marker.getElementsByTagName('MarkerZ')[0].childNodes[0].data)

                try:
                    i = reference[iZ - 1 + offset]
                except IndexError:
                    pass
                else:
                    if not i in self:
                        self[i] = []
                    self[i].append(dict([('iClassLabel', imt),
                                           ('iPosX', int(iX/self._scale)),
                                           ('iPosY', int(iY/self._scale))]))

    def position(self):
        return self.regex.group('position')

    def timepoint(self):
        return int(self.regex.group('time'))

    def timepoints(self):
        return list(self.keys())
