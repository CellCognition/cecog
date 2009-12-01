"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2009 Michael Held
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

import sys, \
       os, \
       math, \
       copy,\
       pprint, \
       subprocess, \
       types, \
       logging, \
       gc

from exceptions import IOError, ValueError
import cPickle as pickle

#-------------------------------------------------------------------------------
# extension module imports:
#

from numpy import asarray, NAN, median
#from rpy import r

from pdk.options import Option
from pdk.optionmanagers import OptionManager

from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            FloatProperty,
                            IntProperty,
                            ListProperty,
                            TupleProperty,
                            StringProperty,
                            InstanceProperty,
                            DictionaryProperty,
                            Property,
                            )
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)
from pdk.attributes import Attribute
from pdk.map import dict_values, dict_append_list
from pdk.fileutils import safe_mkdirs
from pdk.iterator import unique, flatten
from pdk.ordereddict import OrderedDict
from pdk.errors import NotImplementedMethodError
#from pdk.containers.tableio import (importTable,
#                                    exportTable)
#from pdk.containers.tablefactories import newTable

#-------------------------------------------------------------------------------
# cecog module imports:
#

from cecog import ccore

from cecog.util import *
from cecog.analyzer.celltracker import CellTracker, DotWriter
from cecog.segmentation.strategies import (PrimarySegmentation,
                                          SecondarySegmentation)
from cecog.learning.learning import ClassPredictor


#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#

class Region(object):

    def __init__(self, oRoi=None, tplCoords=None):
        if oRoi is not None:
            self.upperLeft = (oRoi.upperLeft.x, oRoi.upperLeft.y)
            self.lowerRight = (oRoi.lowerRight.x, oRoi.lowerRight.y)
        elif tplCoords is not None:
            self.upperLeft = (tplCoords[0], tplCoords[1])
            self.lowerRight = (tplCoords[2], tplCoords[3])
        else:
            self.upperLeft = None
            self.lowerRight = None


class ImageObject(object):

    def __init__(self, oObject=None):
        #self.oRoi = oObject.oRoi
        #self.oCenterAbs2 = oObject.oCenterAbs
        if oObject is not None:
            self.oCenterAbs = (oObject.oCenterAbs.x, oObject.oCenterAbs.y)
            self.oRoi = Region(oRoi=oObject.oRoi)
        else:
            self.oCenterAbs = None
            self.oRoi = None
        self.iLabel = None
        self.dctProb = {}
        self.strClassName = None
        self.strHexColor = None
        self.iId = None
        self.aFeatures = None

#    def __copy__(self):
#        oImageObject = ImageObject()
#        oImageObject.oCenterAbs = self.oCenterAbs
#        oImageObject.aChromatinFeatures = copy.copy(self.aChromatinFeatures)
#        oImageObject.aSecondaryFeatures = copy.copy(self.aSecondaryFeatures)
#        oImageObject.iLabel = self.iLabel
#        oImageObject.dctProb = self.dctProb
#        oImageObject.strClassName = self.strClassName
#        oImageObject.strHexColor = self.strHexColor
#        oImageObject.iId = self.iId
#        return oImageObject

    def squaredMagnitude(self, oObj):
        x = float(oObj.oCenterAbs[0] - self.oCenterAbs[0])
        y = float(oObj.oCenterAbs[1] - self.oCenterAbs[1])
        return x*x + y*y


class QualityControl(object):

    FILENAME_TOKEN = ['prefix', 'P', 'C', 'R', 'A']

    def __init__(self, strFilePath, oMetaData, dctProcessInfos, dctPlotterInfos=None):
        super(QualityControl, self).__init__()

        self.dctProcessInfos = dctProcessInfos

        if dctPlotterInfos is None:
            dctPlotterInfos = {}
        #self._oPlotter = RPlotter(**dctPlotterInfos)
        #self._oPlate = oPlate
        self._strFilePath = strFilePath
        self._dctPositions = {}
        self._iCurrentP = None
        self._oMetaData = oMetaData

    def initPosition(self, iP, origP):
        self._iCurrentP = iP
        self._origP = origP
        self._dctPositions[iP] = {}

    def processPosition(self, oTimeHolder):
        iP = self._iCurrentP
        for strChannelId, dctInfo in self.dctProcessInfos.iteritems():

            strRegionId = dctInfo['regionId']
            strTask = dctInfo['task']

            if strTask == 'proliferation':

                oTable = newTable(['Frame', 'Timestamp', 'Cellcount'],
                                  columnTypeCodes=['i','f','i'])

                for iT, dctChannels in oTimeHolder.iteritems():
                    try:
                        oRegion = dctChannels[strChannelId].getRegion(strRegionId)
                    except KeyError:
                        iCellcount = 0
                    else:
                        iCellcount = len(oRegion)

                    fTimestamp = self._oMetaData.getTimestamp(self._origP, iT)

                    oTable.append({'Frame'     : iT,
                                   'Timestamp' : fTimestamp,
                                   'Cellcount' : iCellcount,
                                   })

                #self._plotProliferation()
                exportTable(oTable,
                            os.path.join(self._strFilePath,
                                         "qc_P%s_C%s_R%s_A%s.tsv" % (iP, strChannelId, strRegionId, strTask)),
                            fieldDelimiter='\t',
                            writeRowLabels=False)



class ObjectHolder(dict):

    def __init__(self, strName):
        super(ObjectHolder, self).__init__()
        self.strName = strName
        self._lstFeatureNames = None
        self._dctNamesIdx = None

    def setFeatureNames(self, lstFeatureNames):
        self._lstFeatureNames = lstFeatureNames[:]
        self._dctNamesIdx = {}
        # build mapping: featureName -> index
        for iIdx, strFeatureName in enumerate(self._lstFeatureNames):
            self._dctNamesIdx[strFeatureName] = iIdx

    def getFeatureNames(self):
        return self._lstFeatureNames[:]

    def getFeaturesByNames(self, iObjId, lstFeatureNames):
        if lstFeatureNames is None:
            lstFeatureNames = self._lstFeatureNames
        aData = asarray([self[iObjId].aFeatures[self._dctNamesIdx[strFeatureName]]
                         for strFeatureName in lstFeatureNames])
        return aData


class _Channel(PropertyManager):

    NAME = None

    RANK = None

    PROPERTIES = \
        dict(strChannelId =
                 StringProperty(None,
                                is_mandatory=True,
                                doc=''),

             oZSliceOrProjection =
                 Property(1,
                          doc='either the number of the z-slice (starting by 1) '
                              'or the type of Z-projection: "max", "min", "mean"'),

             channelRegistration =
                 TupleProperty(None),

             strChannelColor =
                 StringProperty('#FFFFFF'),
             iMedianRadius =
                 IntProperty(0,
                             doc='strength of median-filtering'),

             strImageOutCompression =
                 StringProperty('80'),
             strPathOutDebug =
                 StringProperty(None),
             bDebugMode =
                 BooleanProperty(False),

             bDoClassification =
                 BooleanProperty(False,
                                 doc=''),
             strClassificationEnv =
                 StringProperty('',
                                doc=''),
             strClassificationModel =
                 StringProperty('',
                                doc=''),
             lstFeatureCategories =
                 ListProperty(None,
                              doc=''),
             dctFeatureParameters =
                 DictionaryProperty(None,
                                    doc=''),
             lstFeatureNames =
                 ListProperty(None,
                              doc=''),

             dctAreaRendering =
                 DictionaryProperty(None,
                                    doc=''),

             bPostProcessing =
                 BooleanProperty(True,
                                 doc='post-processing: filter objects by size, '
                                     'shape, intensity, etc.'),
             lstPostprocessingFeatureCategories =
                 ListProperty(None,
                              doc=''),
             strPostprocessingConditions =
                 StringProperty('roisize > 50',
                                doc=''),
             bPostProcessDeleteObjects =
                 BooleanProperty(True,
                                 doc=''),

             tplScale =
                TupleProperty(None, doc=''),

             tplCropRegion =
                TupleProperty(None, doc=''),


             bFlatfieldCorrection =
                 BooleanProperty(False,
                                 doc=''),
             strImageType =
                 StringProperty('UInt8',
                                doc=''),
             strBackgroundImagePath =
                 StringProperty('',
                                doc=''),
             fBackgroundCorrection =
                 FloatProperty('',
                               doc=''),
             fNormalizeMin =
                 FloatProperty('',
                               doc=''),
             fNormalizeMax =
                 FloatProperty('',
                               doc=''),
             fNormalizeRatio =
                 FloatProperty('',
                               doc=''),
             fNormalizeOffset =
                 FloatProperty('',
                               doc=''),
             )

    __attributes__ = [Attribute('_lstZSlices'),
                      Attribute('_oLogger'),
                      Attribute('_dctRegions'),
                      Attribute('oMetaImage'),
                      Attribute('dctContainers'),
                      ]

    def __init__(self, **dctOptions):
        super(_Channel, self).__init__(**dctOptions)
        self._oLogger = logging.getLogger(self.__class__.__name__)
        self.clear()

    def __cmp__(self, oOther):
        return cmp(self.RANK, oOther.RANK)

    def __getstate__(self):
        # FIXME: not very elegant way to prevent logger from getting pickled
        dctState = get_attribute_values(self)
        del dctState['_oLogger']
        return dctState

    def __setstate__(self, state):
        set_attribute_values(self, state)
        # FIXME: restore logger instance
        self._oLogger = logging.getLogger(self.NAME)

    def clear(self):
        self._lstZSlices = []
        self._dctRegions = {}
        self.oMetaImage = None
        self.dctContainers = {}

    def getRegionNames(self):
        return self._dctRegions.keys()

    def getRegion(self, name):
        return self._dctRegions[name]

    def hasRegion(self, name):
        return name in self._dctRegions

    def getContainer(self, name):
        return self.dctContainers[name]

    def purge(self, features=None):
        self.oMetaImage = None
        self._lstZSlices = []
        for x in self.dctContainers.keys():
            del self.dctContainers[x]

        # purge features
        if not features is None:
            channelFeatures = []
            for featureNames in features.values():
                if not featureNames is None:
                    channelFeatures.extend(featureNames)
            channelFeatures = sorted(unique(channelFeatures))

            # reduce features per region and object to given list
            for regionName in self.getRegionNames():
                region = self.getRegion(regionName)
                for objId in region:
                    try:
                        region[objId].aFeatures = region.getFeaturesByNames(objId, channelFeatures)
                    except KeyError:
                        pass
                region.setFeatureNames(channelFeatures)


    def appendZSlice(self, oMetaImage):
        self._lstZSlices.append(oMetaImage)

    def applyZSelection(self):
        if self.oZSliceOrProjection in ['max', 'min', 'mean']:
            lstZImages = [img.imgXY for img in self._lstZSlices]
            if self.oZSliceOrProjection == "max":
                self._oLogger.debug("* applying Max Z-Projection to stack of %d images..." % len(lstZImages))
                imgXYProj = ccore.projectImage(lstZImages, ccore.ProjectionType.MaxProjection)
            elif self.oZSliceOrProjection == "min":
                self._oLogger.debug("* applying Min Z-Projection to stack of %d images..." % len(lstZImages))
                imgXYProj = ccore.projectImage(lstZImages, ccore.ProjectionType.MinProjection)
            elif self.oZSliceOrProjection == "mean":
                self._oLogger.debug("* applying Mean Z-Projection to stack of %d images..." % len(lstZImages))
                imgXYProj = ccore.projectImage(lstZImages, ccore.ProjectionType.MeanProjection)

            # overwrite the first MetaImage found with the projected image data
            oMetaImage = self._lstZSlices[0]
            oMetaImage.imgXY = imgXYProj
        else:
            self.oZSliceOrProjection = int(self.oZSliceOrProjection)
            self._oLogger.debug("* selecting z-slice %d..." % self.oZSliceOrProjection)
            oMetaImage = self._lstZSlices[self.oZSliceOrProjection-1]
            #print oMetaImage

#        elif type(self.oZSliceOrProjection) == types.IntType:
#            self._oLogger.debug("* selecting z-slice %d..." % self.oZSliceOrProjection)
#            oMetaImage = self._lstZSlices[self.oZSliceOrProjection-1]
#        else:
#            raise ValueError("Wrong 'oZSliceOrProjection' value '%s' for channel Id '%s'" %\
#                             (self.oZSliceOrProjection, self.strChannelId))

#        if not self.channelRegistration is None:
#            shift = self.channelRegistration.values()[0]
#            w = oMetaImage.iWidth - shift[0]
#            h = oMetaImage.iHeight - shift[1]
#            if self.strChannelId in self.channelRegistration:
#                s = (0,0)
#            else:
#                s = shift
#            oMetaImage.imgXY = ccore.subImage(oMetaImage.imgXY,
#                                              ccore.Diff2D(*s),
#                                              ccore.Diff2D(w, h))

        self.oMetaImage = oMetaImage



    def applyBinning(self, iFactor):
        self.oMetaImage.binning(iFactor)

    def applySegmentation(self):
        raise NotImplementedMethodError()

    def applyFeatures(self):

        for strKey, oContainer in self.dctContainers.iteritems():

            oObjectHolder = ObjectHolder(strKey)

            if not oContainer is None:

                for strFeatureCategory in self.lstFeatureCategories:
                    oContainer.applyFeature(strFeatureCategory)

                # calculate set of haralick features
                # (with differnt distances)
                if 'haralick_categories' in self.dctFeatureParameters:
                    for strHaralickCategory in self.dctFeatureParameters['haralick_categories']:
                        for iHaralickDistance in self.dctFeatureParameters['haralick_distances']:
                            oContainer.haralick_distance = iHaralickDistance
                            oContainer.applyFeature(strHaralickCategory)

                lstValidObjectIds = []
                lstRejectedObjectIds = []

                for iObjectId, oObject in oContainer.getObjects().iteritems():
                    dctFeatures = oObject.getFeatures()

                    bAcceptObject = True

#                    # post-processing
#                    if self.bPostProcessing:
#
#                        if not eval(self.strPostprocessingConditions, dctFeatures):
#                            if self.bPostProcessDeleteObjects:
#                                #del dctObjects[iObjectId]
#                                oContainer.delObject(iObjectId)
#                                bAcceptObject = False
#                            lstRejectedObjectIds.append(iObjectId)
#                        else:
#                            lstValidObjectIds.append(iObjectId)
#                    else:
#                        lstValidObjectIds.append(iObjectId)
#
#                    oContainer.lstValidObjectIds = lstValidObjectIds
#                    oContainer.lstRejectedObjectIds = lstRejectedObjectIds

                    if bAcceptObject:
                        # build a new ImageObject
                        oImageObject = ImageObject(oObject)
                        oImageObject.iId = iObjectId

                        if self.lstFeatureNames is None:
                            self.lstFeatureNames = sorted(dctFeatures.keys())

                        # assign feature values in sorted order as NumPy array
                        oImageObject.aFeatures = \
                            asarray(dict_values(dctFeatures, self.lstFeatureNames))

                        oObjectHolder[iObjectId] = oImageObject

            if not self.lstFeatureNames is None:
                oObjectHolder.setFeatureNames(self.lstFeatureNames)
            self._dctRegions[strKey] = oObjectHolder



class PrimaryChannel(_Channel):

    NAME = 'Primary'

    RANK = 1

    PROPERTIES = \
        dict(bSpeedup =
                 BooleanProperty(False,
                                 doc=''),
             iLatWindowSize =
                 IntProperty(None,
                             doc='size of averaging window for '
                                 'local adaptive thresholding.'),
             iLatLimit =
                 IntProperty(None,
                             doc='lower threshold for '
                                 'local adaptive thresholding.'),

             iLatWindowSize2 =
                 IntProperty(None,
                             doc='size of averaging window for '
                                 'local adaptive thresholding.'),
             iLatLimit2 =
                 IntProperty(None,
                             doc='lower threshold for '
                                 'local adaptive thresholding.'),

             bDoShapeWatershed =
                 BooleanProperty(True,
                                 doc='shape-based watershed: '
                                     'split objects by distance-transformation.'),
             iGaussSizeShape =
                 IntProperty(4,
                             doc=''),
             iMaximaSizeShape =
                 IntProperty(12,
                             doc=''),

             bDoIntensityWatershed =
                 BooleanProperty(False,
                                 doc='intensity-based watershed: '
                                     'split objects by intensity.'),
             iGaussSizeIntensity =
                 IntProperty(5,
                             doc=''),
             iMaximaSizeIntensity =
                 IntProperty(11,
                             doc=''),

             iMinMergeSize = IntProperty(75,
                                         doc='watershed merge size: '
                                             'merge all objects below that size'),

             bRemoveBorderObjects =
                 BooleanProperty(True,
                                 doc='remove all objects touching the image borders'),

             iEmptyImageMax =
                 IntProperty(30,
                             doc=''),

             )

    def __init__(self, **dctOptions):
        super(PrimaryChannel, self).__init__(**dctOptions)

    def applySegmentation(self, oDummy):
        if (not self.channelRegistration is None and
            len(self.channelRegistration) == 2):
            shift = self.channelRegistration
            imgIn = self.oMetaImage.imgXY
            w = imgIn.width - abs(shift[0])
            h = imgIn.height - abs(shift[1])
            ul_x = shift[0] if shift[0] >= 0 else 0
            ul_y = shift[1] if shift[1] >= 0 else 0

            self.oMetaImage.imgXY = ccore.subImage(imgIn,
                                                   ccore.Diff2D(ul_x, ul_y),
                                                   ccore.Diff2D(w, h))

        oSegmentation = PrimarySegmentation(strImageOutCompression = self.strImageOutCompression,
                                            strPathOutDebug = self.strPathOutDebug,
                                            bDebugMode = self.bDebugMode,
                                            iMedianRadius = self.iMedianRadius,
                                            bSpeedup = self.bSpeedup,
                                            iLatWindowSize = self.iLatWindowSize,
                                            iLatLimit = self.iLatLimit,
                                            iLatWindowSize2 = self.iLatWindowSize2,
                                            iLatLimit2 = self.iLatLimit2,
                                            bDoShapeWatershed = self.bDoShapeWatershed,
                                            iGaussSizeShape = self.iGaussSizeShape,
                                            iMaximaSizeShape = self.iMaximaSizeShape,
                                            bDoIntensityWatershed = self.bDoIntensityWatershed,
                                            iGaussSizeIntensity = self.iGaussSizeIntensity,
                                            iMaximaSizeIntensity = self.iMaximaSizeIntensity,
                                            iMinMergeSize = self.iMinMergeSize,
                                            bRemoveBorderObjects = self.bRemoveBorderObjects,
                                            iEmptyImageMax = self.iEmptyImageMax,
                                            bPostProcessing = self.bPostProcessing,
                                            lstPostprocessingFeatureCategories = self.lstPostprocessingFeatureCategories,
                                            strPostprocessingConditions = self.strPostprocessingConditions,
                                            bPostProcessDeleteObjects = self.bPostProcessDeleteObjects,
                                            bFlatfieldCorrection = self.bFlatfieldCorrection,
                                            strImageType = self.strImageType,
                                            strBackgroundImagePath = self.strBackgroundImagePath,
                                            fBackgroundCorrection = self.fBackgroundCorrection,
                                            fNormalizeMin = self.fNormalizeMin,
                                            fNormalizeMax = self.fNormalizeMax,
                                            fNormalizeRatio = self.fNormalizeRatio,
                                            fNormalizeOffset = self.fNormalizeOffset,
                                            tplCropRegion = self.tplCropRegion,
                                            )
        oContainer = oSegmentation(self.oMetaImage)
        if not oContainer is None:
            self.dctContainers['primary'] = oContainer
            return True
        else:
            return False


class SecondaryChannel(_Channel):

    NAME = 'Secondary'

    RANK = 2

    PROPERTIES = \
        dict(iExpansionSize =
                 IntProperty(None,
                             is_mandatory=True,
                             doc='final thickness of area around '
                                 'primary object (in pixel)'),
             iExpansionSeparationSize =
                 IntProperty(None,
                             is_mandatory=True,
                             doc='separation outside of the primary object'),
             iShrinkingSeparationSize =
                 IntProperty(None,
                             is_mandatory=True,
                             doc='separation inside of the primary object'),
             fExpansionCostThreshold =
                 IntProperty(None,
                             is_mandatory=True,
                             doc=''),
             lstAreaSelection =
                 ListProperty(None,
                              is_mandatory=True,
                              doc='values: "expanded", "inside", "outside"'),

             bEstimateBackground =
                 BooleanProperty(False),
             iBackgroundMedianRadius =
                 IntProperty(None),
             iBackgroundLatSize =
                 IntProperty(None),
             iBackgroundLatLimit =
                 IntProperty(None),
             )


    __attributes__ = [Attribute('fBackgroundAverage'),
                      Attribute('bSegmentationSuccessful'),
                      ]

    def __init__(self, **dctOptions):
        super(SecondaryChannel, self).__init__(**dctOptions)
        self.fBackgroundAverage = float('NAN')
        self.bSegmentationSuccessful = False

    def applySegmentation(self, oChannel):
        if (not self.channelRegistration is None and
            len(self.channelRegistration) == 2):
            shift = self.channelRegistration
            imgIn = self.oMetaImage.imgXY
            w = imgIn.width - abs(shift[0])
            h = imgIn.height - abs(shift[1])
            ul_x = -shift[0] if shift[0] < 0 else 0
            ul_y = -shift[1] if shift[1] < 0 else 0

            self.oMetaImage.imgXY = ccore.subImage(imgIn,
                                                   ccore.Diff2D(ul_x, ul_y),
                                                   ccore.Diff2D(w, h))

        if 'primary' in oChannel.dctContainers:
            oSegmentation = SecondarySegmentation(strImageOutCompression = self.strImageOutCompression,
                                                  strPathOutDebug = self.strPathOutDebug,
                                                  bDebugMode = self.bDebugMode,
                                                  iMedianRadius = self.iMedianRadius,
                                                  iExpansionSize = self.iExpansionSize,
                                                  iExpansionSeparationSize = self.iExpansionSeparationSize,
                                                  iShrinkingSeparationSize = self.iShrinkingSeparationSize,
                                                  fExpansionCostThreshold = self.fExpansionCostThreshold,
                                                  lstAreaSelection = self.lstAreaSelection,
                                                  bFlatfieldCorrection = self.bFlatfieldCorrection,
                                                  strImageType = self.strImageType,
                                                  strBackgroundImagePath = self.strBackgroundImagePath,
                                                  fBackgroundCorrection = self.fBackgroundCorrection,
                                                  fNormalizeMin = self.fNormalizeMin,
                                                  fNormalizeMax = self.fNormalizeMax,
                                                  tplCropRegion = self.tplCropRegion,
                                                  )
            self.dctContainers = oSegmentation(self.oMetaImage, oChannel.dctContainers['primary'])

            if self.bEstimateBackground:
                self.fBackgroundAverage = oSegmentation.estimateBackground(self.oMetaImage,
                                                                           self.iBackgroundMedianRadius,
                                                                           self.iBackgroundLatSize,
                                                                           self.iBackgroundLatLimit)
            self.bSegmentationSuccessful = True


class TimeHolder(OrderedDict):

    def __init__(self, channels):
        super(TimeHolder, self).__init__()
        self._iCurrentT = None
        self.channels = channels

    def initTimePoint(self, iT):
        self._iCurrentT = iT

    def getCurrentTimePoint(self):
        return self._iCurrentT

    def getCurrentChannels(self):
        return self[self._iCurrentT]

    def applyChannel(self, oChannel):
        iT = self._iCurrentT
        if not iT in self:
            self[iT] = {}
        self[iT][oChannel.strChannelId] = oChannel


class CellAnalyzer(PropertyManager):

    PROPERTIES = \
        dict(P =
                 StringProperty(True, doc=''),
             bCreateImages =
                 BooleanProperty(True, doc="Create output images"),
             iBinningFactor =
                 IntProperty(None,
                             is_mandatory=True,
                             doc=''),


             oTimeHolder =
                 InstanceProperty(None,
                                  TimeHolder,
                                  doc="Instance of TimeHolder.",
                                  is_mandatory=True),
             oCellTracker =
                 InstanceProperty(None,
                                  CellTracker,
                                  doc="Instance of CellTracker.",
                                  is_mandatory=True),
            )

    __attributes__ = [Attribute('_dctChannels'),
                      Attribute('_iT'),
                      Attribute('_oLogger'),
                      ]

    def __init__(self, **dctOptions):
        super(CellAnalyzer, self).__init__(**dctOptions)
        self._oLogger = logging.getLogger(self.__class__.__name__)

    def initTimepoint(self, iT):
        self._dctChannels = OrderedDict()
        self._iT = iT
        self.oTimeHolder.initTimePoint(iT)

    def registerChannel(self, oChannel):
        strChannelId = oChannel.strChannelId
        self._dctChannels[strChannelId] = oChannel

    def getChannel(self, strChannelId):
        return self._dctChannels[strChannelId]

    def process(self):
        bSuccess = True
        # sort by Channel `RANK`
        lstChannels = self._dctChannels.values()
        lstChannels.sort()
        oPrimaryChannel = None
        for oChannel in lstChannels:

            oChannel.applyZSelection()
#            oChannel.applyBinning(self.iBinningFactor)
            oResult = oChannel.applySegmentation(oPrimaryChannel)

            oChannel.applyFeatures()

            if oPrimaryChannel is None:
                if oResult:
                    assert oChannel.RANK == 1
                    oPrimaryChannel = oChannel
                else:
                    bSuccess = False
                    break

        for oChannel in lstChannels:
            self.oTimeHolder.applyChannel(oChannel)
        return bSuccess

    def purge(self, features=None):
        for oChannel in self._dctChannels.values():
            if not features is None and oChannel.strChannelId in features:
                channelFeatures = features[oChannel.strChannelId]
            else:
                channelFeatures = None
            oChannel.purge(features=channelFeatures)

    def exportLabelImages(self, pathOut, compression='LZW'):
        for strChannelId, oChannel in self._dctChannels.iteritems():
            for strRegion, oContainer in oChannel.dctContainers.iteritems():
                strPathOutImage = os.path.join(pathOut,
                                               strChannelId,
                                               strRegion)
                safe_mkdirs(strPathOutImage)
                oContainer.exportLabelImage(os.path.join(strPathOutImage,
                                                         'P%s_T%05d.tif' % (self.P, self._iT)),
                                            compression)

    def getImageSize(self, strChannelId):
        oChannel = self._dctChannels[strChannelId]
        w = oChannel.oMetaImage.iWidth
        h = oChannel.oMetaImage.iHeight
        return (w,h)

    def render(self, strPathOut, dctRenderInfo=None,
               strFileSuffix='.jpg', strCompression='98', writeToDisc=True,
               images=None):
        lstImages = []
        if not images is None:
            lstImages += images

        if dctRenderInfo is None:
            for strChannelId, oChannel in self._dctChannels.iteritems():
                for strRegion, oContainer in oChannel.dctContainers.iteritems():
                    strHexColor, fAlpha = oChannel.dctAreaRendering[strRegion]
                    imgRaw = oChannel.oMetaImage.imgXY
                    imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                    ccore.drawContour(oContainer.getBinary(), imgCon, 255, False)
                    lstImages.append((imgRaw, strHexColor, 1.0))
                    lstImages.append((imgCon, strHexColor, fAlpha))
        else:
            for strChannelId, dctChannelInfo in dctRenderInfo.iteritems():
                if strChannelId in self._dctChannels:
                    oChannel = self._dctChannels[strChannelId]
                    if 'raw' in dctChannelInfo:
                        strHexColor, fAlpha = dctChannelInfo['raw']
                        lstImages.append((oChannel.oMetaImage.imgXY, strHexColor, fAlpha))

                    if 'contours' in dctChannelInfo:
                        # transform the old dict-style to the new tuple-style,
                        # which allows multiple definitions for one region
                        if type(dctChannelInfo['contours']) == types.DictType:
                            lstContourInfos = [(k,)+v
                                               for k,v in dctChannelInfo['contours'].iteritems()]
                        else:
                            lstContourInfos = dctChannelInfo['contours']

                        for tplData in lstContourInfos:
                            strRegion, strNameOrColor, fAlpha, bShowLabels = tplData[:4]
                            if len(tplData) > 4:
                                bThickContours = tplData[4]
                            else:
                                bThickContours = False
                            if strNameOrColor == 'class_label':
                                oContainer = oChannel.dctContainers[strRegion]
                                oRegion = oChannel.getRegion(strRegion)
                                dctLabels = {}
                                dctColors = {}
                                for iObjId, oObj in oRegion.iteritems():
                                    iLabel = oObj.iLabel
                                    if not iLabel is None:
                                        if not iLabel in dctLabels:
                                            dctLabels[iLabel] = []
                                        dctLabels[iLabel].append(iObjId)
                                        dctColors[iLabel] = oObj.strHexColor
                                #print dctLabels
                                imgRaw = oChannel.oMetaImage.imgXY
                                imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                for iLabel, lstObjIds in dctLabels.iteritems():
                                    imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                    oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
                                    lstImages.append((imgCon, dctColors[iLabel], fAlpha))

                                    if type(bShowLabels) == types.BooleanType and bShowLabels:
                                    #    oContainer.drawTextsByIds(lstObjIds, lstObjIds, imgCon2)
                                    #else:
                                        oContainer.drawTextsByIds(lstObjIds, [str(iLabel)]*len(lstObjIds), imgCon2)
                                lstImages.append((imgCon2, '#FFFFFF', 1.0))

                            else:
                                oContainer = oChannel.dctContainers[strRegion]
                                oRegion = oChannel.getRegion(strRegion)
                                lstObjIds = oRegion.keys()
                                imgRaw = oChannel.oMetaImage.imgXY
                                imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                if not strNameOrColor is None:
                                    oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
                                else:
                                    strNameOrColor = '#FFFFFF'
                                lstImages.append((imgCon, strNameOrColor, fAlpha))
                                if bShowLabels:
                                    imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                    oContainer.drawLabelsByIds(lstObjIds, imgCon2)
                                    lstImages.append((imgCon2, '#FFFFFF', 1.0))


        if len(lstImages) > 0:
            imgRgb = ccore.makeRGBImage([x[0].getView() for x in lstImages],
                                        [ccore.RGBValue(*hexToRgb(x[1])) for x in lstImages],
                                        [x[2] for x in lstImages])

            if writeToDisc:
                strFilePath = os.path.join(strPathOut, "P%s_T%05d%s" % (self.P, self._iT, strFileSuffix))
                safe_mkdirs(strPathOut)
                ccore.writeImage(imgRgb, strFilePath, strCompression)
                self._oLogger.debug("* rendered image written '%s'" % strFilePath)
            else:
                strFilePath = ''
            return imgRgb, strFilePath


    def collectObjects(self, P, lstReader, oLearner, byTime=True):

        strChannelId = oLearner.strChannelId
        strRegionId = oLearner.strRegionId
        img_rgb = None

        self._oLogger.debug('* collecting samples...')

        bSuccess = True
        lstChannels = self._dctChannels.values()
        lstChannels.sort()
        oPrimaryChannel = None
        for oChannel2 in lstChannels:

            oChannel2.applyZSelection()
            oResult = oChannel2.applySegmentation(oPrimaryChannel)

            if oPrimaryChannel is None:
                if oResult:
                    assert oChannel2.RANK == 1
                    oPrimaryChannel = oChannel2
                else:
                    bSuccess = False
                    break

        if bSuccess:

            oChannel = self._dctChannels[strChannelId]
            oContainer = oChannel.getContainer(strRegionId)
            objects = oContainer.getObjects()

            object_lookup = {}
            for oReader in lstReader:
                lstCoordinates = None
                if (byTime and P == oReader.getPosition() and self._iT in oReader):
                    lstCoordinates = oReader[self._iT]
                elif (not byTime and P in oReader):
                    lstCoordinates = oReader[P]
                #print "moo", P, oReader.getPosition(), byTime, self._iT in oReader
                #print lstCoordinates, byTime, self.P, oReader.keys()

                if not lstCoordinates is None:
                    #print self.iP, self._iT, lstCoordinates
                    for dctData in lstCoordinates:
                        label = dctData['iClassLabel']
                        if (label in oLearner.dctClassNames and
                            dctData['iPosX'] >= 0 and
                            dctData['iPosX'] < oContainer.width and
                            dctData['iPosY'] >= 0 and
                            dctData['iPosY'] < oContainer.height):
                            center1 = ccore.Diff2D(dctData['iPosX'],
                                                   dctData['iPosY'])
                            dists = []
                            for obj_id, obj in objects.iteritems():
                                diff = obj.oCenterAbs - center1
                                dist_sq = diff.squaredMagnitude()
                                # limit to 30 pixel radius
                                if dist_sq < 900:
                                    dists.append((obj_id, dist_sq))
                            if len(dists) > 0:
                                dists.sort(lambda a,b: cmp(a[1], b[1]))
                                obj_id = dists[0][0]
                                dict_append_list(object_lookup, label, obj_id)

            object_ids = set(flatten(object_lookup.values()))
            objects_del = set(objects.keys()) - object_ids
            for obj_id in objects_del:
                oContainer.delObject(obj_id)

            oChannel.applyFeatures()
            region = oChannel.getRegion(strRegionId)

            learner_objects = []
            for label, object_ids in object_lookup.iteritems():
                class_name = oLearner.dctClassNames[label]
                hex_color = oLearner.dctHexColors[class_name]
                for obj_id in object_ids:
                    obj = region[obj_id]
                    obj.iLabel = label
                    obj.strClassName = class_name
                    obj.strHexColor = hex_color

                    if (obj.oRoi.upperLeft[0] >= 0 and
                        obj.oRoi.upperLeft[1] >= 0 and
                        obj.oRoi.lowerRight[0] < oContainer.width and
                        obj.oRoi.lowerRight[1] < oContainer.height):
                        iCenterX, iCenterY = obj.oCenterAbs

                        strPathOutLabel = os.path.join(oLearner.dctEnvPaths['samples'],
                                                       oLearner.dctClassNames[label])
                        safe_mkdirs(strPathOutLabel)

                        strFilenameBase = 'P%s_T%05d_X%04d_Y%04d' % (self.P, self._iT, iCenterX, iCenterY)

                        obj.sample_id = strFilenameBase
                        learner_objects.append(obj)

                        strFilenameImg = os.path.join(strPathOutLabel, '%s__img.png' % strFilenameBase)
                        strFilenameMsk = os.path.join(strPathOutLabel, '%s__msk.png' % strFilenameBase)
                        #print strFilenameImg, strFilenameMsk
                        oContainer.exportObject(obj_id,
                                                strFilenameImg,
                                                strFilenameMsk)

                oContainer.markObjects(list(object_ids),
                                       ccore.RGBValue(*hexToRgb(hex_color)), False, True)

            if len(learner_objects) > 0:
                oLearner.applyObjects(learner_objects)
                # we dont want to apply None for feature names
                oLearner.setFeatureNames(oChannel.lstFeatureNames)

            strPathOut = os.path.join(oLearner.dctEnvPaths['controls'])
            safe_mkdirs(strPathOut)
            oContainer.exportRGB(os.path.join(strPathOut,
                                              "P%s_T%05d_C%s_R%s.jpg" %\
                                               (self.P, self._iT, oLearner.strChannelId, oLearner.strRegionId)),
                                '90')
            img_rgb = oContainer.img_rgb
            # endif bSuccess
        return img_rgb


    def classifyObjects(self, oPredictor):
        strChannelId = oPredictor.strChannelId
        strRegionId = oPredictor.strRegionId
        oChannel = self._dctChannels[strChannelId]
        oRegion = oChannel.getRegion(strRegionId)
        for iObjId, oObj in oRegion.iteritems():
            iLabel, dctProb = oPredictor.predict(oObj.aFeatures.copy(), oRegion.getFeatureNames())
            oObj.iLabel = iLabel
            oObj.dctProb = dctProb
            oObj.strClassName = oPredictor.dctClassNames[iLabel]
            oObj.strHexColor = oPredictor.dctHexColors[oObj.strClassName]
