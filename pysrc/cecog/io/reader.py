"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland
                            www.cellcognition.org

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""
from pdk.fileutils import collect_files

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL:: $'


#------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       exceptions, \
       re, \
       pprint, \
       weakref, \
       cPickle as pickle, \
       logging, \
       sys

from types import ListType, TupleType

#------------------------------------------------------------------------------
# extension module imports:
#
from numpy import asarray, mean, std

from pdk.options import Option
from pdk.optionmanagers import OptionManager
from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            FloatProperty,
                            IntProperty,
                            Property,
                            StringProperty,)
from pdk.attributes import Attribute
from pdk.attributemanagers import (get_slot_values,
                                   set_slot_values)
from pdk.ordereddict import OrderedDict

#------------------------------------------------------------------------------
# mito imports:
#
from cecog import ccore
from cecog.util import LoggerMixin
from cecog.util import rgbToHex

#------------------------------------------------------------------------------
# constants:
#
IMAGECONTAINER_FILENAME = 'ImageContainer.pkl'
UINT8 = 'UINT8'
UINT16 = 'UINT16'
PIXEL_TYPES = [UINT8, UINT16]

#------------------------------------------------------------------------------
# classes:
#

class MetaData(object):

    def __init__(self):
        self.iDimX, self.iDimY, self.iDimZ, self.iDimC = (0,0,0,0)
        self.iDimT, self.iDimP = (0,0)
        self.strDimOrder = ''
        self.fVoxelX, self.fVoxelY, self.fVoxelZ = (.0, .0, .0)
        self.pixelType = None
        self.dctTimestamps = {}
        self.dctTimestampsAbsolute = {}
        self.dctChannelMapping = {'gfp':  '#00FF00',
                                  'rfp':  '#FF0000',
                                  'fitc': '#0000FF',
                                  'dapi': '#0000FF',
                                  }
        self.dctTimestampStrs = {}
        self.dctTimestampDeltas = {}

    def _analyzeTimestamps(self):
        for P, dctPosTimestamps in self.dctTimestamps.iteritems():
            lstTKeys = dctPosTimestamps.keys()
            lstTKeys.sort()
            lstDeltas = [dctPosTimestamps[lstTKeys[iIdx+1]] -
                         dctPosTimestamps[lstTKeys[iIdx]]
                         for iIdx in range(len(lstTKeys)-1)]
            self.dctTimestampDeltas[P] = lstDeltas
            if len(lstDeltas) > 1:
                fMean = mean(lstDeltas)
                fStd  = std(lstDeltas)
                self.dctTimestampStrs[P] = "%.2fmin (+/- %.3fmin)" % (fMean / 60.0, fStd / 60.0)
            else:
                self.dctTimestampStrs[P] = "-"

    def getTimestamp(self, oPos, iT):
        try:
            fResult = self.dctTimestamps[oPos][iT]
        except KeyError:
            return float('NAN')
        else:
            return fResult

    def appendAbsoluteTime(self, pos, frame, absTime):
        if not pos in self.dctTimestampsAbsolute:
            self.dctTimestampsAbsolute[pos] = OrderedDict()
        self.dctTimestampsAbsolute[pos][frame] = absTime

    def setup(self):
        for pos in self.dctTimestampsAbsolute:
            self.dctTimestampsAbsolute[pos].sort()
        for pos, absTimes in self.dctTimestampsAbsolute.iteritems():
            baseTime = absTimes.values()[0]
            self.dctTimestamps[pos] = OrderedDict()
            for frame, absTime in absTimes.iteritems():
                self.dctTimestamps[pos][frame] = absTime - baseTime

    def format(self, time=True):
        if len(self.dctTimestampStrs) == 0:
            self._analyzeTimestamps()
        oPrinter = pprint.PrettyPrinter(indent=6, depth=6, width=1)
        lstStr = []
        strHead = "*   Imaging MetaData   *"
        strLine = "*"*len(strHead)
        lstStr += [strLine]
        lstStr += [strHead]
        lstStr += [strLine]
        lstStr += ["* Width: %s" % self.iDimX]
        lstStr += ["* Height: %s" % self.iDimY]
        lstStr += ["* Z-slices: %s" % self.iDimZ]
        lstStr += ["* Channels: %s" % self.iDimC]
        lstStr += ["* Time-points: %s" % self.iDimT]
        lstStr += ["* Positions: %s" % self.iDimP]
        if time:
            lstStr += ["* Timestamp(s):\n" + oPrinter.pformat(self.dctTimestampStrs) + "\n"]
        lstChannels = ["%s: %s" % (key, value)
                       for key, value in self.dctChannelMapping.iteritems()
                       if key in self.setC]
        lstStr += ["* Channel Mapping:\n" + oPrinter.pformat(lstChannels) + "\n"]
        lstStr += [strLine]
        return "\n".join(lstStr)

    def __str__(self):
        return self.format()


class MetaImage(PropertyManager):
    """
    Simple container to hold an image with its direct meta information.
    Image reading is implemented lazy.
    """

    __attributes__ = \
        [Attribute("_imgXY"),
         ]

    PROPERTIES = dict(imgXY  = Property(None, getCallback="getImageXY", setPreCallback="setImageXY"),
                      oImageContainer = Property(None, is_mandatory=False),
                      P      = StringProperty(None, is_mandatory=True),
                      iT     = IntProperty(None, is_mandatory=True),
                      strC   = StringProperty("", is_mandatory=True),
                      iZ     = IntProperty(None, is_mandatory=True),
                      strFormat = StringProperty(UINT8, is_mandatory=False),
                      iWidth = IntProperty(None, getCallback="getWidth", isReadOnly=True),
                      iHeight= IntProperty(None, getCallback="getHeight", isReadOnly=True),
                      )

    def __init__(self, **dctOptions):
        super(MetaImage, self).__init__(**dctOptions)
        if not hasattr(self, "_imgXY"):
            self._imgXY = None
        #if self._imgXY is None and self.oImageContainer is None:
        #    raise ValueError("error")

    def getImageXY(self):
        # finally read the image from disk
        if self._imgXY is None:
            self._imgXY = self.oImageContainer.getXYImage(self.P,
                                                          self.iT,
                                                          self.strC,
                                                          self.iZ,
                                                          self.strFormat)
        return self._imgXY

    def setImageXY(self, imgXY):
        self._imgXY = imgXY

    def getWidth(self):
        return self.imgXY.width

    def getHeight(self):
        return self.imgXY.height

    def format(self, strSuffix=None, bP=True, bT=True, bC=True, bZ=True, strSep='_'):
        lstFormat = []
        if bP:
            lstFormat.append("P%s" % self.P)
        if bT:
            lstFormat.append("T%05d" % self.iT)
        if bC:
            lstFormat.append("C%s" % self.strC)
        if bZ:
            lstFormat.append("Z%02d" % self.iZ)
        if strSuffix is not None:
            lstFormat.append(strSuffix)
        return strSep.join(lstFormat)

    def binning(self, iFactor):
        """
        simulate camera binning of the image by averaging n x n pixel blocks
        """
        if iFactor > 1:
            iWidth = self.iWidth
            iHeight = self.iHeight
            imgTmp1 = ccore.Image(iWidth, iHeight)
            ccore.binImage(self.imgXY, imgTmp1, iFactor)
            iWidth /= iFactor
            iHeight /= iFactor
            self._imgXY = ccore.scaleImage(imgTmp1, ccore.Diff2D(iWidth, iHeight), "no")

    def scale(self, tplSize, method='linear'):
        self._imgXY = ccore.scaleImage(self.imgXY, ccore.Diff2D(*tplSize), method)



class AxisIterator(object):
    """
    Concept of iterator-generator chains, which are linked according the given
    experiment scan-order and result in nested loops of scan-order dimensions.

    e.g. for scan-order PTCZYX the generators are linked:
      P->T->C->Z where the last returns the XY image (here a MetaImage instance)

    The definition of break-points allows to yield a generator at any nd-space,
    which can yield a generator of the sub-space again or directly return the
    XY-images in the their scan-order.
    """

    def __init__(self, oImgContainer, oDim, setDim,
                 strName="???", bBreak=False, nextIt=None):
        self._oImgContainer = oImgContainer
        self._nextIt = nextIt
        self._bBreak = bBreak
        if oDim is None:
            self._setDim = setDim
        elif type(oDim) in [ListType, TupleType]:
            self._setDim = oDim
        elif oDim in setDim:
            self._setDim = [oDim]
        else:
            raise ValueError("Selected %s '%s' not available. Candidates are %s." %\
                             (strName, oDim, setDim))

    def __call__(self, oV=None, lstDims=None):
        #print lstDims, self._setDim
        if lstDims is None:
            lstDims = []
        else:
            lstDims.append(oV)
        if not self._nextIt is None:
            for i in self._setDim:
                # break: stop the iteration and return the generator
                if self._bBreak:
                    # return the generator
                    yield i, self._nextIt(i, lstDims[:])
                else:
                    # iterate over the next generator: return elements of the
                    # next dimension
                    for x in self._nextIt(i, lstDims[:]):
                        yield x
        else:
            # end of generator-chain reached: return the MetaImages
            for i in self._setDim:
                #print "zappa", tuple(lstDims[:]+[i])
                yield i, self._oImgContainer.getMetaImage(*tuple(lstDims[:]+[i]))



class _ImageContainer(OptionManager):

    OPTIONS = {'lstDirFiles'       : Option(None),
               'lstPositions'      : Option(None),
               'dctChannelMapping' : Option(None),
               'iBinningFactor'    : Option(None),
               'dctScaleChannels'  : Option(None),
               'strPixelFormat'    : Option(UINT8),
               'hasContinuousFrames': Option(True),
               }

    __slots__ = ['strPath',
                 'lstNameTags',
                 'oMetaData',
                 'dctNamesByDimensions',
                 '_oIteratorFirst',
                 'dctReverseChannelMapping',
                 '_oPathMappingFunction',
                 ]

    def __init__(self, strPath, **dctOptions):
        super(_ImageContainer, self).__init__(**dctOptions)
        self.strPath = strPath
        self.lstNameTags = []
        self.dctNamesByDimensions = {}
        self._oPathMappingFunction = None

        self.oMetaData = MetaData()
        self._oIteratorFirst = None

#        self.dctReverseChannelMapping = {}
#        if self.getOption('dctChannelMapping') is None:
#            raise ValueError("'dctChannelMapping' must be specified!")
#        else:
#            for strMarker, tplData in self.getOption('dctChannelMapping').iteritems():
#                strChannelId, strRgb = tplData
#                self.dctReverseChannelMapping[strChannelId] = strMarker

        if self.getOption('dctScaleChannels') is None:
            self.setOption('dctScaleChannels', {})

    def __getstate__(self):
        dctSlots = {}
        dctSlots.update(super(_ImageContainer, self).__getstate__())
        dctSlots.update(get_slot_values(self))
        #print dctSlots
        return dctSlots

    def __setstate__(self, state):
        super(_ImageContainer, self).__setstate__(state)
        set_slot_values(self, state)

    def getImageNDByFrame(self, iFrame):
        pass

    def setPathMappingFunction(self, func):
        self._oPathMappingFunction = func

    def getXYImageByMeta(self, oMetaImage):
        P, iT, iC, iZ = oMetaImage.P, oMetaImage.iT, oMetaImage.iC, oMetaImage.iZ
        return self.getXYImage(P, iT, iC, iZ)

    def getXYImage(self, iDimP, iDimT, iDimC, iDimZ):
        raise exceptions.NotImplementedError("Not implemented in abstract class.")

#    def getXYCPArray(self, iZ, iT):
#        assert iZ in self.oMetaData.setZ
#        assert iT in self.oMetaData.setT
#        lstImages = []
#        for P in self.oMetaData.setP:
#            for iC in self.oMetaData.setC:
#                lstImages.append(self.getXYImage(iZ, iC, iT, P))
#        return ccore.transformImageListToArray4D(lstImages, self.oMetaData.iDimC, self.oMetaData.iDimP)

    def iterator(self, oP=None, oT=None, oC=None, oZ=None,
                 bBreakT=False, bBreakC=False, bBreakZ=False):
        # FIXME: depending of the scan-order the iterators can be linked with each other
        oIteratorZ = AxisIterator(self, oZ, self.oMetaData.setZ, "Z")
        oIteratorC = AxisIterator(self, oC, self.oMetaData.setC, "C", nextIt=oIteratorZ, bBreak=bBreakZ)
        oIteratorT = AxisIterator(self, oT, self.oMetaData.setT, "T", nextIt=oIteratorC, bBreak=bBreakC)
        oIteratorP = AxisIterator(self, oP, self.oMetaData.setP, "P", nextIt=oIteratorT, bBreak=bBreakT)
        return oIteratorP()

    __call__ = iterator

    def getMetaImage(self, P, iT, strC, iZ):
        oMetaImage = MetaImage(oImageContainer=self,
                               P=P, iT=iT, strC=strC, iZ=iZ,
                               strFormat=self.getOption('strPixelFormat'))
        if strC in self.getOption('dctScaleChannels'):
            oMetaImage.scale(self.getOption('dctScaleChannels')[strC])
        if not self.getOption('iBinningFactor') is None:
            oMetaImage.binning(self.getOption('iBinningFactor'))
        return oMetaImage

    def getNameTokens(self, strName, dctNameTags=None):
        if dctNameTags is None:
            dctNameTags = {}
        oTokenSearch = self.oTokenRe.search(strName)
        if oTokenSearch is not None:
            strTokens = oTokenSearch.group('Token')
            #print strTokens

            if 'P' not in dctNameTags:
                oRe = self.oPositionRe.search(strTokens)
                if oRe is not None:
                    P = oRe.group('P')
                    self.bHasP = True
                else:
                    P = 1
                dctNameTags['P'] = P


            oRe = self.oTimeRe.search(strTokens)
            if oRe is not None:
                iT = int(oRe.group('T'))
                self.bHasT = True
            else:
                iT = 1
            dctNameTags['T'] = iT

            oRe = self.oChannelRe.search(strTokens)
            if oRe is not None:
                strC = oRe.group('C')
                self.bHasC = True
                #print strC
            else:
                strC = "1"
            dctNameTags['C'] = strC

            oRe = self.oZSliceRe.search(strTokens)
            if oRe is not None:
                iZ = int(oRe.group('Z'))
                self.bHasZ = True
            else:
                iZ = 1
            dctNameTags['Z'] = iZ
        return dctNameTags


    def _resolveTokens(self, strPath, strFilename, dctTokens):
        self.getNameTokens(strFilename, dctTokens)
        # get last modification time for every file to calculate the time-lapse
        dctTokens['mtime'] = os.path.getmtime(os.path.join(strPath, strFilename))
        #dctNameTags.update(dctTokens)




class ImageContainerLsm(_ImageContainer):

    CHANNEL_LOOKUP = {'ChD-T2': 'dic',
                      'Ch1-T2': 'rfp',
                      'Ch3-T1': 'gfp',
                      }

    OPTIONS = {'strPositionPattern': Option('_[PL](?P<P>\d+)'),
               }

    __slots__ = ['_dctMarkerToChannelId',
                 ]

    def __setstate__(self, state):
        super(ImageContainerLsm, self).__setstate__(state)
        self._dctLsmFiles = {}

    def __init__(self, strPath, **dctOptions):
        super(ImageContainerLsm, self).__init__(strPath, **dctOptions)

        oPositionRe = re.compile(self.getOption('strPositionPattern'), re.I)

        self.dctNamesByDimensions = {}
        self._dctLsmFiles = {}

        lstPositions = self.getOption('lstPositions')

        for strFilename in self.getOption('lstDirFiles'):
            oRe = oPositionRe.search(strFilename)
            if oRe is not None:
                P = oRe.group('P')
                if lstPositions is None or P in lstPositions:
                    dctNameTags = {'name' : strFilename,
                                      'P' : P,
                                   }
                    self.dctNamesByDimensions[P] = strFilename
                    self.lstNameTags.append(dctNameTags)

        self.lstNameTags.sort(cmp=self._sortFilenames)

        if len(self.lstNameTags) > 0:

            P = self.lstNameTags[0]['P']
            oLsmFile = self._getLsmFile(P)
            oLsmMeta = oLsmFile.oMetaData

            self.oMetaData.setP  = set([dctNameTag['P'] for dctNameTag in self.lstNameTags])
            self.oMetaData.iDimP = len(self.oMetaData.setP)

            self.oMetaData.iDimX = oLsmMeta.iDimX
            self.oMetaData.iDimY = oLsmMeta.iDimY
            self.oMetaData.iDimZ = oLsmMeta.iDimZ
            self.oMetaData.iDimT = oLsmMeta.iDimT
            self.oMetaData.iDimC = oLsmMeta.iDimC
            self.oMetaData.setZ = set(range(1, self.oMetaData.iDimZ+1))
            self.oMetaData.setT = set(range(1, self.oMetaData.iDimT+1))

            # map marker names to LSM channels Ids (numeric, start at 0)
            self._dctMarkerToChannelId = {}
            self.oMetaData.dctChannelData = {}
            self.oMetaData.dctChannelMapping = {}
            for iIdx, (strLsmChannelName, oRgbValue) in enumerate(oLsmMeta.getChannelData()):
                strMarkerName = self.CHANNEL_LOOKUP[strLsmChannelName]
                #print oLsmMeta.getChannelData()
                #self.oMetaData.dctChannelData = dict(oLsmMeta.getChannelData())
                self.oMetaData.dctChannelMapping[strMarkerName] = rgbToHex(oRgbValue[0],
                                                                           oRgbValue[1],
                                                                           oRgbValue[2])
                self._dctMarkerToChannelId[strMarkerName] = iIdx

            self.oMetaData.setC = set(self.oMetaData.dctChannelMapping.keys())
            self.oMetaData.iDimC = len(self.oMetaData.setC)

            #self.oMetaData.dctChannelMapping
            #print self.oMetaData

        # this non-lazy mechanism is necessary to get the timestamps of every
        # LSM file. not that ALL LSM files are opened at this time and kept
        # open until the MetaData object dies (image data is not touched here)
        for P in self.dctNamesByDimensions:
            self._getLsmFile(P)

        #self.oMetaData.iDimX = imgProbe.width
        #self.oMetaData.iDimY = imgProbe.height


    def _getLsmFile(self, P):
        """
        read LSM files (lazy)
        """
        oLsmFile = None
        if P in self._dctLsmFiles:
            oLsmFile = self._dctLsmFiles[P]
        else:
            oLsmFile = ccore.LsmReader(os.path.join(self.strPath,
                                                    self.dctNamesByDimensions[P]))
            self._dctLsmFiles[P] = oLsmFile
            # update the time-series data
            # start at T=1 and use an dict internally (in case frames are missing)
            self.oMetaData.dctTimestamps[P] = dict([(x+1,y)
                                                     for x,y in enumerate(oLsmFile.oMetaData.getTimestampData())])
        return oLsmFile


    def getXYImage(self, P=1, iT=1, strC="1", iZ=1):
        oLsmFile = self._getLsmFile(P)
        return oLsmFile.getXYImage(iT-1, iZ-1, self._dctMarkerToChannelId[strC])


    def getImageNDByFrame(self, iFrame):
        pass



    @staticmethod
    def _sortFilenames(a, b):
        return cmp(a['P'],b['P'])



class ImageContainerStack(_ImageContainer):

    OPTIONS = {'strRegexToken'    : Option(None),
               'strRegexPosition' : Option(None),
               'strRegexTime'     : Option(None),
               'strRegexChannel'  : Option(None),
               'strRegexZSlice'   : Option(None),
               }

    __slots__ = ['bHasMultiImages']

    def __init__(self, strPath, **dctOptions):
        super(ImageContainerStack, self).__init__(strPath, **dctOptions)

        self.oTokenRe    = re.compile(self.getOption('strRegexToken'))

        self.oPositionRe = re.compile(self.getOption('strRegexPosition'))
        self.oTimeRe     = re.compile(self.getOption('strRegexTime'))
        self.oChannelRe  = re.compile(self.getOption('strRegexChannel'))
        self.oZSliceRe   = re.compile(self.getOption('strRegexZSlice'))

        self.lstNameTags = []
        self.bHasP = False
        self.bHasT = False
        self.bHasC = False
        self.bHasZ = False
        self.bHasMultiImages = False
        self._generateNameTags()

        # filter by position - again - since they might be encoded in the
        # filename only
        lstPositions = self.getOption('lstPositions')
        self.lstNameTags = [dctNameTags for dctNameTags in self.lstNameTags
                            if lstPositions is None or dctNameTags['P'] in lstPositions
                            ]

        self.lstNameTags.sort(cmp=self._sort)

        print self.lstNameTags[:20]

        if self.bHasP:
            self.oMetaData.setP = sorted(set([dctNameTags['P'] for dctNameTags in self.lstNameTags]))
        else:
            self.oMetaData.setP = set([1])

        if self.bHasT:
            # find minimum time-points for break-during-acquisition experiments

            if not self.getOption('hasContinuousFrames'):
                # replace the T information by a continuous count starting from 1
                all_times = sorted(set([dctNameTags['T'] for dctNameTags in self.lstNameTags]))
                times_lookup = dict([(t, idx+1) for idx, t in enumerate(all_times)])
                for idx in range(len(self.lstNameTags)):
                    #print self.lstNameTags[idx]['T'], times_lookup[self.lstNameTags[idx]['T']]
                    self.lstNameTags[idx]['T'] = times_lookup[self.lstNameTags[idx]['T']]

            if self.bHasP:
                lstT = []
                for P in self.oMetaData.setP:
                    lstTNew = [dctNameTags['T'] for dctNameTags in self.lstNameTags
                               if dctNameTags['P'] == P
                               ]
                    if len(lstT) == 0 or len(lstTNew) < len(lstT):
                        lstT = lstTNew[:]
            else:
                lstT = [dctNameTags['T'] for dctNameTags in self.lstNameTags]
            self.oMetaData.setT = sorted(set(lstT))
        else:
            self.oMetaData.setT = set([1])

        if self.bHasC:
            #print self.dctReverseChannelMapping
            #print self.lstNameTags
            #print self.dctReverseChannelMapping
            #print [dctNameTags
            #       for dctNameTags in self.lstNameTags
            #       if dctNameTags['C'] == '1']
            self.oMetaData.setC = sorted(set([dctNameTags['C']
                                              for dctNameTags in self.lstNameTags]))
        else:
            self.oMetaData.setC = set(['1'])

        if self.bHasZ:
            self.oMetaData.setZ = sorted(set([dctNameTags['Z'] for dctNameTags in self.lstNameTags]))
        else:
            self.oMetaData.setZ = set([1])

        #print self.oMetaData.setT

        self.oMetaData.iDimP = len(self.oMetaData.setP)
        self.oMetaData.iDimT = len(self.oMetaData.setT)
        self.oMetaData.iDimC = len(self.oMetaData.setC)
        self.oMetaData.iDimZ = len(self.oMetaData.setZ)


        self.dctNamesByDimensions = {}
        for dctNameTags in self.lstNameTags:
            #print dctNameTags

            P = dctNameTags['P']
            iT = dctNameTags['T']
            iZ = dctNameTags['Z']

            strChannelId = dctNameTags['C']
            #strMarker = self.dctReverseChannelMapping[strChannelId]

            if P not in self.dctNamesByDimensions:
                self.dctNamesByDimensions[P] = {}

            if iT not in self.dctNamesByDimensions[P]:
                self.dctNamesByDimensions[P][iT] = {}

#            # assign time-stamp information to every timepoint for every position
#            if iP not in dctBaseTimes:
#                self.oMetaData.dctTimestamps[iP] = {}
#                dctBaseTimes[iP] = dctNameTags['mtime']
#            # store raw timestamps
#            self.oMetaData.dctTimestamps[iP][iT] = dctNameTags['mtime'] - dctBaseTimes[iP]

            self.oMetaData.appendAbsoluteTime(P, iT, dctNameTags['mtime'])

            if strChannelId not in self.dctNamesByDimensions[P][iT]:
                self.dctNamesByDimensions[P][iT][strChannelId] = {}

            if iZ not in self.dctNamesByDimensions[P][iT][strChannelId]:
                self.dctNamesByDimensions[P][iT][strChannelId][iZ] = dctNameTags['name']

        self.oMetaData.setup()

        #FIXME: read first image beforehand
        #print self.lstNameTags
        if len(self.lstNameTags) > 0:
            imgInfo = ccore.ImageImportInfo(self.lstNameTags[0]['name'])
            self.oMetaData.iDimX = imgInfo.width
            self.oMetaData.iDimY = imgInfo.height
            self.oMetaData.pixelType = imgInfo.pixel_type
            self.setOption('strPixelFormat', imgInfo.pixel_type)
            #print imgInfo.pixel_type
            if imgInfo.images > 1:
                self.oMetaData.iDimZ = imgInfo.images
                self.bHasMultiImages = True
        else:
            raise IOError("No valid files found to analyze in '%s'." % self.strPath)


    def getXYImage(self, P, T, C, Z, strFormat=UINT8):
        try:
            # check for backwards compatibility
            if hasattr(self, 'bHasMultiImages') and self.bHasMultiImages:
                imageIndex = Z
                Z = 1
            else:
                imageIndex = -1
            strPathImage = self.dctNamesByDimensions[P][T][C][Z]
        except KeyError:
            if strFormat == UINT8:
                return ccore.Image(self.oMetaData.iDimX, self.oMetaData.iDimY)
            elif strFormat == UINT16:
                return ccore.ImageInt16(self.oMetaData.iDimX, self.oMetaData.iDimY)
            else:
                raise ValueError("Unknown image pixel format: '%s'" % strFormat)
        else:
            if not self._oPathMappingFunction is None:
                strPathImage = self._oPathMappingFunction(strPathImage)
            if strFormat == UINT8:
                imgXY = ccore.readImage(strPathImage, imageIndex)
                logging.debug('read UINT8 image')
                return imgXY
            elif strFormat == UINT16:
                imgXY = ccore.readImageUInt16(strPathImage, imageIndex)
                logging.debug('read UINT16 image')
                return imgXY
            else:
                raise ValueError("Unknown image pixel format: '%s'" % strFormat)

    def getImageNDByFrame(self, iFrame):
        pass

    @staticmethod
    def _sort(a, b):
        if 'P' in a and 'P' in b and cmp(a['P'],b['P']) != 0:
            return cmp(a['P'],b['P'])
        elif 'T' in a and 'T' in b and cmp(a['T'],b['T']) != 0:
            return cmp(a['T'],b['T'])
        elif 'C' in a and 'C' in b and cmp(a['C'],b['C']) != 0:
            return cmp(a['C'],b['C'])
            #elif cmp(a['Z'],b['Z']) != 0:
        elif 'Z' in a and 'Z' in b and cmp(a['Z'],b['Z']) != 0:
            return cmp(a['Z'],b['Z'])
        else:
            return 0

    def _generateNameTags(self):
        for strFilename in self.getOption('lstDirFiles'):
            #dctNameTags = {'P': '', 'T': '', 'C': '', 'Z': ''}
            dctNameTags = {'name': os.path.join(self.strPath, strFilename)}
            self._resolveTokens(self.strPath, strFilename, dctNameTags)
            self.lstNameTags.append(dctNameTags)


class ImageContainerSubdirStack(ImageContainerStack):

    def __init__(self, strPath, dctSubDirFiles, **dctOptions):
        self.dctSubDirFiles = dctSubDirFiles
        super(ImageContainerSubdirStack, self).__init__(strPath, **dctOptions)

    def _generateNameTags(self):
        self.bHasP = True
        for P, (strSubDir, lstSubDirFiles) in self.dctSubDirFiles.iteritems():
            for strFilename in lstSubDirFiles:
                strPath = os.path.join(self.strPath, strSubDir)
                strFullpath = os.path.join(strPath, strFilename)
                dctNameTags = {'name': strFullpath}
                dctNameTags['P'] = P
                self._resolveTokens(strPath, strFilename, dctNameTags)
                self.lstNameTags.append(dctNameTags)


#------------------------------------------------------------------------------
# functions:
#


def create_image_container(path, naming_scheme, positions):
        path = path

        re_sub = re.compile(naming_scheme['regex_subdirectories'])
        sub_dirs = {}
        # guess positions as sub-directories
        for filename in os.listdir(path):
            search = re_sub.search(filename)
            if (os.path.isdir(os.path.join(path, filename)) and
                not search is None):
                sub_dirs[search.group('P')] = filename

        logger = logging.getLogger()
        logger.info("Found sub-directories: %s" % 'yes' if len(sub_dirs) > 0 else 'no')

        # filter positions by given list
        if not positions is None:
            for pos in sub_dirs.keys():
                if not pos in positions:
                    del sub_dirs[pos]

        sub_dir_filenames = {}
        for pos, sub_dir in sub_dirs.iteritems():
            filenames = collect_files(os.path.join(path, sub_dir), ['.tif'])
            sub_dir_filenames[pos] = (sub_dir, filenames)

        image_container = ImageContainerSubdirStack(path,
                                                    sub_dir_filenames,
                                                    lstPositions = positions,
                                                    strRegexToken = naming_scheme['regex_token'],
                                                    strRegexPosition = naming_scheme['regex_position'],
                                                    strRegexTime = naming_scheme['regex_time'],
                                                    strRegexChannel = naming_scheme['regex_channel'],
                                                    strRegexZSlice = naming_scheme['regex_zslice'])

        return image_container


def has_image_container(path):
    return os.path.isfile(os.path.join(path, IMAGECONTAINER_FILENAME))

def load_image_container(path):
    f = file(os.path.join(path, IMAGECONTAINER_FILENAME), 'rb')
    image_container = pickle.load(f)
    f.close()
    return image_container

def dump_image_container(path, image_container):
    f = file(os.path.join(path, IMAGECONTAINER_FILENAME), 'wb')
    pickle.dump(image_container, f, 1)
    f.close()

#------------------------------------------------------------------------------
# main:
#

if __name__ ==  "__main__":
    pass