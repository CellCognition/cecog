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

#------------------------------------------------------------------------------
# standard library imports:
#
import logging, \
       os, \
       traceback, \
       random, \
       time, \
       sys

#------------------------------------------------------------------------------
# extension modules:
#
import numpy

from pyamf import register_class

from mito.learning.learning import BaseLearner
from mito.reader import loadImageContainer
from mito import ccore
from mito.settings import Settings
from mito.analyzer.analyzer import *
from mito.analyzer.celltracker import *
from mito.experiment.plate import *

from pdk.containers.ordereddict import OrderedDict
from pdk.util.imageutils import rgbToHex, hexToRgb
from pdk.util.fileutils import collectFilesByRegex
from pdk.util.iterator import flatten

#------------------------------------------------------------------------------
# classifier modules:
#
from classifier.lib.amf import AmfMixin
from classifier.lib.helpers import hexToFlexColor
from classifier.lib.base import session

#------------------------------------------------------------------------------
# classes:
#

class Position(object):

    def __init__(self, name=None, oligoId="", geneSymbol=""):
        self.name = name
        self.oligoId = oligoId
        self.geneSymbol = geneSymbol


class Channel(object):

    def __init__(self, name=None, color=None):
        self.name = name
        self.color = color


class Experiment(object):

    def __init__(self, name=None, path=None):
        self.path = path
        self.name = name
        self.dimX = None
        self.dimY = None
        self.dimT = None
        self.dimZ = None
        self.dimC = None
        self.dimP = None
        self.channels = None
        self.positions = None
        self.primary = "rfp"

class ImageObject2(object):

    def __init__(self, id=None):
        self.id = id
        self.coords = None

class ExperimentService(object):

    def __init__(self, path):
        self.strPath = path

        self.dctExperiments = OrderedDict()

        for strDir in os.listdir(self.strPath):
            strPathExp = os.path.join(self.strPath, strDir)
            if strDir[0] not in ['_', '.'] and os.path.isdir(strPathExp):
                self.dctExperiments[strDir] = Experiment(strDir, strPathExp)

    def getAll(self):
        print self.dctExperiments
        return self.dctExperiments.values()

    def getExperimentByName(self, experimentName):
        oExperiment = self.dctExperiments[experimentName]
        strDumpFile = os.path.join(oExperiment.path, 'dump')
        oImageContainer = loadImageContainer(strDumpFile)
        oMetaData = oImageContainer.oMetaData

        oExperiment.dimX = oMetaData.iDimX
        oExperiment.dimY = oMetaData.iDimY
        oExperiment.dimT = oMetaData.iDimT
        oExperiment.dimC = oMetaData.iDimC
        oExperiment.dimZ = oMetaData.iDimZ
        oExperiment.dimP = oMetaData.iDimP
        oExperiment.oImageContainer = oImageContainer

        oExperiment.positions = []
        for iP in sorted(oMetaData.setP):
            oExperiment.positions.append(Position(str(iP)))

        oExperiment.channels = []
        for strC in sorted(oMetaData.setC):
            oChannel = Channel(strC, hexToFlexColor(oMetaData.dctChannelMapping[strC]))
            oExperiment.channels.append(oChannel)

        print "moo1"
        session['experimentName'] = experimentName
        print "moo2"
        session.save()
        print "moo3"
        print oExperiment
        return oExperiment

    def getImageViewBySelection(self, selection):
        print selection
        experimentName = session['experimentName']
        oExperiment = self.dctExperiments[experimentName]
        oImageContainer = oExperiment.oImageContainer
        oChannel = selection['C']
        try:
            img = oImageContainer.getXYImage(selection['P'], selection['T'], oChannel.name, selection['Z'])
        except KeyError:
            traceback.print_exc()
            print oImageContainer.oMetaData.setC
        else:
            session['viewSelection'] = selection
            session.save()
            strImagePath = '/tmp/cecog_flex_temp.jpg'
            ccore.writeImage(img, strImagePath, strCompression='100')

            return "/site_media"+strImagePath
        #return ""


    def detectObjects(self):

        print "hello"
        oSettings = Settings("/Users/miheld/src/mito_svn/trunk/mito/commonanalysis/settings/flexTestData/exp836_PCNA_MD_10x_96well.classification_prophase.settings.py", dctGlobals=globals())

        strC = 'rfp'
        clsChannel, strSettings = oSettings.dctChannelMapping[strC]
        dctSettings = getattr(oSettings, strSettings)
        dctSettings['lstFeatureCategories'] = []
        dctSettings['dctFeatureParameters'] = {}
        oChannel = clsChannel(strChannelId=strC,
                              bDebugMode=oSettings.bDebugMode,
                              strPathOutDebug='/Users/miheld/data/',
                              **dctSettings)

        experimentName = session['experimentName']
        oExperiment = self.dctExperiments[experimentName]
        oImageContainer = oExperiment.oImageContainer
        viewSelection = session['viewSelection']
        oChannel.appendZSlice(oImageContainer.getMetaImage(oImageContainer.oMetaData.setP[viewSelection['P']-1], viewSelection['T'], strC, viewSelection['Z']))

        oTimeHolder = TimeHolder()
        oCellAnalyzer = CellAnalyzer(oTimeHolder=oTimeHolder,
                                     iP = oImageContainer.oMetaData.setP[viewSelection['P']-1],
                                     bCreateImages = oSettings.bCreateImages,
                                     iBinningFactor = oSettings.iBinningFactor,
                                     )

        oCellAnalyzer.initTimepoint(viewSelection['T'])
        oCellAnalyzer.registerChannel(oChannel)
        oCellAnalyzer.process()
        #oCellAnalyzer.purge()
        oRegion = oChannel.getRegion('primary')
        oContainer = oChannel.getContainer('primary')

        lstResults = []
        for iObjId, oObj in oRegion.iteritems():
            oImageObject = ImageObject2(iObjId)
            oImageObject.coords = ",".join(map(str,flatten(oContainer.getCrackCoordinates(iObjId))))
            print iObjId, len(oImageObject.coords), oImageObject.coords
            lstResults.append(oImageObject)
        print len(lstResults)
        return lstResults


#------------------------------------------------------------------------------
#

DOMAIN_NS = 'org.cecog'
META_DATA = ['amf3']
register_class(Position, DOMAIN_NS+'.Position', metadata=META_DATA, attrs=['name', 'oligoId', 'geneSymbol'])
register_class(Channel, DOMAIN_NS+'.Channel', metadata=META_DATA, attrs=['name', 'color'])
register_class(Experiment, DOMAIN_NS+'.Experiment', metadata=META_DATA,
               attrs=['path', 'name', 'dimX', 'dimY', 'dimT', 'dimZ', 'dimC', 'dimP', 'channels', 'positions', 'primary'])
register_class(ImageObject2, DOMAIN_NS+'.ImageObject', metadata=META_DATA, attrs=['id', 'coords'])
