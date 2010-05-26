"""
Experiment definition handling: read position mappings for plates/LabTeks
"""

__author__ =   '$Author$'
__date__ =     '$Date$'
__revision__ = '$Rev$'
__source__ =   '$URL$'

#------------------------------------------------------------------------------
# standard library imports:
#
import types, \
       os, \
       math, \
       itertools

#------------------------------------------------------------------------------
# extension module imports:
#
from numpy import asarray, zeros, equal, empty, isnan

from pdk.containers.tableio import importTable, exportTable
from pdk.containers.tablefactories import newTable
from pdk.containers.ordereddict import OrderedDict
from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            FloatProperty,
                            IntProperty,
                            ListProperty,
                            StringProperty,
                            TupleProperty)
from pdk.optionmanagers import OptionManager
from pdk.options import Option
from pdk.util.iterator import unique
from pdk.util.fileutils import collectFiles

#------------------------------------------------------------------------------
# mito module imports:
#
from mito.plotter import RPlotter


#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# functions:
#
def resolveMappingFile(strPathIn):
    lstFilenames = collectFiles(strPathIn, ['.tsv'], recursive=False)

    lstFilenames = [x for x in lstFilenames
                    if not os.path.split(x)[1][0] in ['_', '.']]
    if len(lstFilenames) > 0:
        strPlateFilename = lstFilenames[0]
    else:
        raise ValueError("No plate mapping file (*.tsv) found in '%s'" % strPathIn)
    return strPlateFilename

#------------------------------------------------------------------------------
# classes:
#

class _PlateMapper(OptionManager):
    """
    interface to access different format/versions of plate mapping
    """
    COLUMNS = (('GeneSymbol', 'c'),
               ('Group', 'c'),
               ('FunctionalGroup', 'c'),
               ('siRNAID', 'c'),
               ('PosX', 'i'),
               ('PosY', 'i'),
               ('Position', 'c'),
               ('Rank', 'i'),
               ('Site', 'i'),
               ('Well', 'c'),
               ('CatalogNo', 'c'),
               )

    OPTIONAL_COLUMNS = (('FunctionalGroup', 'c'),
                        ('GroupAverage', 'c'),
                        )

    POSITION_CONVERT = '%04d'

    def __init__(self, **dctOptions):
        super(_PlateMapper, self).__init__(**dctOptions)


class ExcelMacroPlateMapper(_PlateMapper):

    OPTIONS = dict(strFieldDelimiter = Option('\t'),

                   dctColumns =\
                       Option({'GeneSymbol' : 'GeneSymbol',
                               'siRNAID'    : 'siRNAID',
                               'Position'   : 'Stagepositionnr_',
                               'Group'      : 'Group',
                               }),

                   dctOptionalColumns =\
                       Option({'FunctionalGroup' : 'FunctionalGroup',
                               'GroupAverage'    : 'GroupAverage',
                               'Rank'            : 'Rank',
                               'Site'            : 'Site',
                               'Well'            : 'Well',
                               'PosX'            : 'Spotpos_X',
                               'PosY'            : 'Spotpos_Y',
                               }),
                   )

    def __init__(self, strFilename, **dctOptions):
        super(ExcelMacroPlateMapper, self).__init__(**dctOptions)

        self._oMappingTable = \
            importTable(strFilename,
                        fieldDelimiter=self.getOption('strFieldDelimiter'))
        #print self._oMappingTable

    def getOptionalColumns(self):
        lstColumns = []
        for strColumn, strColumnMapped in self.getOption('dctOptionalColumns').iteritems():
            if strColumnMapped in self._oMappingTable.getColumnKeys():
                lstColumns.append(strColumn)
        return lstColumns

    def iterator(self):
        for oRecord in self._oMappingTable:

            dctRecord = {}
            for strColumn, strColumnMapped in self.getOption('dctColumns').iteritems():
                dctRecord[strColumn] = oRecord[strColumnMapped]

            for strColumn, strColumnMapped in self.getOption('dctOptionalColumns').iteritems():
                if strColumnMapped in oRecord.getColumnKeys():
                    dctRecord[strColumn] = oRecord[strColumnMapped]

            yield dctRecord

    def convertMapping(self, tplSubWells=(3,3)):
        iBlockSize = tplSubWells[0] * tplSubWells[1]
        oTable = self._oMappingTable.copyStructure()
        print oTable
        for oRecord in self._oMappingTable:
            iPosX = oRecord['Spotpos_X']
            iPosY = oRecord['Spotpos_Y']
            iStagePos = oRecord['Stagepositionnr_']
            iCnt = 1
            for y in range(tplSubWells[1]):
                for x in range(tplSubWells[0]):
                    oRecord['Stagepositionnr_'] = iBlockSize * (iStagePos - 1) + iCnt
                    oRecord['Spotpos_X'] = iPosX
                    oRecord['Spotpos_Y'] = iPosY
                    oRecord['Site'] = iCnt
                    oTable.append(oRecord)
                    iCnt += 1

        self._oMappingTable = oTable
        print oTable

    def exportMapping(self, strFilename, strFieldDelimiter='\t'):
        exportTable(self._oMappingTable,
                    strFilename,
                    fieldDelimiter=strFieldDelimiter,
                    stringDelimiter='',
                    useLabelsAsKeys=True)


class QiagenPlateMapper(ExcelMacroPlateMapper):

    OPTIONS = dict(strFieldDelimiter = Option('\t'),

                   dctColumns =\
                       Option({'GeneSymbol' : 'GeneSymbol',
                               'siRNAID'    : 'siRNAID',
                               'PosX'       : 'PosX',
                               'PosY'       : 'PosY',
                               'Position'   : 'Position',
                               'Group'      : 'Group',
                               'Well'       : 'Well',
                               'CatalogNo'  : 'QiagenCatNo',
                               }),

                   dctOptionalColumns =\
                       Option({}),
                   )

class NewExcelPlateMapper(ExcelMacroPlateMapper):

    OPTIONS = dict(dctColumns =\
                       Option({'GeneSymbol' : 'GeneSymbol',
                               'siRNAID'    : 'siRNAID',
                               'Position'   : 'Position',
                               'Group'      : 'Group',
                               'Well'       : 'Well',
                               }),

                   dctOptionalColumns =\
                       Option({}),
                   )

class ExcelMacroPlateMapper2(ExcelMacroPlateMapper):

    OPTIONS = dict(strFieldDelimiter = Option('\t'),

                   dctColumns =\
                       Option({'GeneSymbol' : 'GeneSymbol',
                               'siRNAID'    : 'siRNAID',
                               #'Position'   : 'WellOrder2',
                               'Position'   : 'Position',
                               'Group'      : 'Group',
                               'Well'       : 'Well',
                               }),

                   dctOptionalColumns =\
                       Option({}),
                   )

    def __init__(self, strFilename, **dctOptions):
        super(ExcelMacroPlateMapper2, self).__init__(strFilename, **dctOptions)
        # normalize position infos
        self._oMappingTable.sort('WellOrder2')
        lstIdx = self._oMappingTable.selectIndices(lambda data: data['WellOrder2'] == 0)
        del self._oMappingTable[lstIdx]
        for iCnt, oRecord in enumerate(self._oMappingTable):
            oRecord['WellOrder2'] = iCnt+1


class MetamorphPositionWriter(object):

    def __init__(self, strFilename, iFactorX=1, iFactorY=1):
        self.strFilename = strFilename
        self.iFactorX = iFactorX
        self.iFactorY = iFactorY

    def export(self, lstPositions):
        oFile = file(self.strFilename, "w")
        oFile.write('"Stage Memory List", Version 2.0\n')
        oFile.write('0, 0, 0, 0, 0, 0, 0, "um", "um"\n')
        oFile.write('1\n')
        oFile.write('"mito"\n')
        oFile.write('%d\n' % len(lstPositions))
        for iX, iY, name in lstPositions:
            iX *= self.iFactorX
            iY *= self.iFactorY
            oFile.write('"%s", %d, %d, 0, TRUE, TRUE, 2\n' % (name, iX, iY))
        oFile.close()

def exportMetamorphPositions(strFilename, lstPositions, iFactorX=1, iFactorY=1):
    oM = MetamorphPositionWriter(strFilename, iFactorX=iFactorX, iFactorY=iFactorX)
    oM.export(lstPositions)


class _Plate(OptionManager):

    OPTIONS = \
        dict(strExperimentName   = Option(None),
             lstSortOrder        = Option(['Rank', 'Group',
                                           'GeneSymbol', 'Position']),
             lstRanks            = Option([('Group', 'Neg. Control', 1),
                                           ('Group', 'Pos. Control', 2),
                                           ('Group', 'Control', 3),
                                           ]),
             iDefaultRank        = Option(1000),
             tplDims             = Option(None),
             tplPositionDistance = Option(None),
             tplAxisOrientation  = Option(None),
             tplSubWells         = Option(None),
             )

    def __init__(self, **dctOptions):
        super(_Plate, self).__init__(**dctOptions)
        lstColumns   = [x[0] for x in _PlateMapper.COLUMNS]
        lstTypeCodes = [x[1] for x in _PlateMapper.COLUMNS]
        self._oTable = newTable(lstColumns,
                                columnTypeCodes=lstTypeCodes,
                                convertFromStrings=True)

        tplDims = self.getOption('tplDims')
        tplSubWells = self.getOption('tplSubWells')
        tplAxisOrientation = self.getOption('tplAxisOrientation')
        iPos = 1
        for iCol in range(tplDims[0]):
            for iRow in range(tplDims[1]):
                iX = iCol+1 if tplAxisOrientation[0] > 0 else tplDims[0]-iCol
                iY = iRow if tplAxisOrientation[1] > 0 else tplDims[1]-iRow-1

                strWell = "%s%02d" % (chr(ord('A') + iY), iX)
                for iSite in range(1,tplSubWells[0]*tplSubWells[1]+1):
                    self._oTable.append(data={'PosX'  : iCol,
                                              'PosY'  : iRow,
                                              'Site'  : iSite,
                                              'Well'  : strWell,
                                              #'Position' : '%04d' % iPos,
                                              })
                    iPos += 1
        self._oTable.index('GENE_SYMBOL', 'GeneSymbol')
        self._oTable.index('GENE_GROUP', 'Group')
        self._oTable.index('POSITION', 'Position')
        self._oTable.index('COORDINATES', ('PosX', 'PosY'))
        #print self._oTable

    def optimizePositions(self):
        from mito.ccore import tsp
        lstPosData = self.getCoordinates()
        lstIndices = tsp(lstPosData)
        aData = self._oTable.getData()
        self._oTable.setData(aData.take(lstIndices[:-1], axis=0))
        self._oTable.appendColumn('OptimizedScanPosition',
                                  typeCode='i',
                                  data=range(1, len(lstPosData)+1)
                                  )

    def makeMeander(self):
        t = self._oTable

        xDim, yDim = self.getOption('tplDims')
        alternate = False
        pos = 1
        for x in range(xDim):
            if x == 0:
                yr = range(yDim)
            else:
                yr = range(1,yDim)
            if alternate:
                yr.reverse()
            alternate = not alternate
            for y in yr:
                idx = t.selectIndices(lambda rec: rec['PosX'] == x and rec['PosY'] == y)[0]
                t[idx]['Position'] = _PlateMapper.POSITION_CONVERT % pos
                pos += 1
        for x in reversed(range(1,xDim)):
            idx = t.selectIndices(lambda rec: rec['PosX'] == x and rec['PosY'] == 0)[0]
            t[idx]['Position'] = _PlateMapper.POSITION_CONVERT % pos
            pos += 1


    def importMapping(self, oPlateMapper, importSites=False, ignoreCoordinates=False):
        dctPositions = {}

        lstOptionalColumns = oPlateMapper.getOptionalColumns()
        for strColumn, strTypeCode in oPlateMapper.OPTIONAL_COLUMNS:
            if strColumn in lstOptionalColumns:
                self._oTable.appendColumn(strColumn, typeCode=strTypeCode)

        tplSubWells = self.getOption('tplSubWells')
        iSites = tplSubWells[0]*tplSubWells[1]

        for iCnt, dctRecord in enumerate(oPlateMapper.iterator()):
            #if dctRecord['Position'] in self._oTable['Position']:
            #    raise AssertionError("Position '%s' occurred twice!" % dctRecord['Position'])

            if 'Well' in dctRecord:
                dctRecord['Well'] = '%s%02d' % (dctRecord['Well'][0].upper(),
                                                int(dctRecord['Well'][1:]))

            if not 'Rank' in dctRecord or dctRecord['Rank'] is None:
                dctRecord['Rank'] = self.getOption('iDefaultRank')
                lstRanks = self.getOption('lstRanks')
                if not lstRanks is None:
                    for strKey, strValue, iRank in lstRanks:
                        if dctRecord[strKey] == strValue:
                            dctRecord['Rank'] = iRank
                            break
            if type(dctRecord['Position']) == types.IntType:
                bConvertPosition = True
                iPos = dctRecord['Position']
            else:
                bConvertPosition = False
            #print 'bConvertPosition', bConvertPosition

            if ignoreCoordinates:
                if bConvertPosition:
                    dctRecord['Position'] = oPlateMapper.POSITION_CONVERT % iPos
                self._oTable[iCnt].update(**dctRecord)
            else:
                if 'Well' in dctRecord:
                    lstIdx = self._oTable.selectIndices(lambda data: data['Well'] == dctRecord['Well'])
                    #print "moo", lstIdx
                elif 'PosX' in dctRecord and 'PosY' in dctRecord:
                    lstIdx = self._oTable.selectIndices(lambda data: data['PosX'] == dctRecord['PosX'] and data['PosY'] == dctRecord['PosY'])
                else:
                    lstIdx = [iCnt]
                #print len(lstIdx), iSites, dctRecord['PosX'], dctRecord['PosY']
                assert len(lstIdx) == iSites
                for iCnt2, iIdx in enumerate(lstIdx):
                    if bConvertPosition:
                        iConvPos = (iPos - 1) * iSites + iCnt2 + 1
                    else:
                        iConvPos = iPos
                    dctRecord['Position'] = oPlateMapper.POSITION_CONVERT % iConvPos

                    self._oTable[iIdx].update(**dctRecord)

        self._oTable.updateIndices()
        self._oTable.sort('Position')


    def exportPlate(self, strFilename, strFieldDelimiter='\t'):
        exportTable(self._oTable,
                    strFilename,
                    writeRowLabels=False,
                    fieldDelimiter=strFieldDelimiter,
                    stringDelimiter='')

    def exportScanPositions(self, oScanPositionWriter, bOptimize=False):
        if bOptimize and 'OptimizedScanPosition' not in self._oTable.getColumnKeys():
            self.optimizePositions()
        tplAxisOrientation  = self.getOption('tplAxisOrientation')
        tplPositionDistance = self.getOption('tplPositionDistance')
        lstPositions = [(x*tplAxisOrientation[0]*tplPositionDistance[0],
                         y*tplAxisOrientation[1]*tplPositionDistance[1])
                        for x,y in self.getPositions()]
        oScanPositionWriter.export(lstPositions)

    def getCoordinates(self, oTable=None, oFilter=None):
        if oTable is None:
            oTable = self._oTable
        return [(oRecord['PosX'], oRecord['PosY'])
                for oRecord in oTable
                if oFilter is None or oFilter(oRecord)]

    def selectCoordinates(self, strKey, strValue):
        oTable = self._oTable.select(lambda data: equal(data, strValue), strKey)
        return self.getCoordinates(oTable=oTable)

    def getPositions(self, oTable=None):
        if oTable is None:
            oTable = self._oTable
        return oTable['Position']

    def selectPositions(self, strKey, strValue):
        oTable = self._oTable.select(lambda data: equal(data, strValue), strKey)
        return self.getPositions(oTable=oTable)

    def select(self, strKey, strValue):
        return self._oTable.select(lambda data: equal(data, strValue), strKey)

    def getDataFromPosition(self, oPos):
        return self._oTable.select(lambda data: equal(data, oPos), 'Position')[0]

    #def getDataFromScanPosition(self, oPos):
    #    iPos = (int(oPos)-1) / self.getOption('')
    #    return self._oTable.select(lambda data: equal(data, iPos), 'Position')[0]

    def getTourLength(self):
        tplLastP = None
        fLength = .0
        lstPositions = self.getCoordinates()
        if len(lstPositions) > 0:
            lstPositions.append(lstPositions[0])
            tplPositionDistance = self.getOption('tplPositionDistance')
            for iX, iY in lstPositions:
                iX *= tplPositionDistance[0]
                iY *= tplPositionDistance[1]
                if tplLastP is not None:
                    fLength += math.sqrt(math.pow(iX-tplLastP[0], 2) + math.pow(iY-tplLastP[1], 2))
                tplLastP = (iX, iY)
        return fLength

    def getEmptyArray(self, oValue=None):
        aData = empty(asarray(self.getOption('tplDims'))*asarray(self.getOption('tplSubWells')))
        if oValue is not None:
            aData[:] = oValue
        return aData

    def getRecordIterator(self, lstScanPositions=None):
        if not self._oTable.hasIndex('AnnotationSort'):
            self._oTable.index('AnnotationSort', self.getOption('lstSortOrder'))
        for oRecord in self._oTable.getRecordIterator(indexName='AnnotationSort'):
            if (lstScanPositions is None or
                oRecord['Position'] in lstScanPositions):
                yield oRecord

    def getGroups(self):
        lstGeneGroups = self._oTable['Group']
        return unique(lstGeneGroups)

    def getGeneSymbols(self):
        lstGeneSymbols = self._oTable['GeneSymbol']
        return unique(lstGeneSymbols)

    def generateColors(self, key, colors):
        iter_colors = itertools.cycle(colors)
        keys = self._oTable[key]
        key_colors = []
        for idx, name in enumerate(keys):
            if idx == 0 or keys[idx-1] != name:
                color = iter_colors.next()
            key_colors.append(color)
        return key_colors


    @staticmethod
    def coordinateToLabel(oCoord, strAxis):
        #if type(oCoord) == type.ListType:
        if strAxis == 'x':
            lstLabels = ["%d" % (iV+1) for iV in oCoord]
        elif strAxis == 'y':
            lstLabels = [chr(iV+65) for iV in oCoord]
        return lstLabels

    @staticmethod
    def splitWell(strWell, bColumnToInt=True, bRowUppercase=True):
        strRow = strWell[0].upper()
        oCol =  int(strWell[1:]) if bColumnToInt else strWell[1:]
        return strRow, oCol

    def __str__(self):
        return str(self._oTable)

    def __cmp__(self, oPlate):
        return cmp(self.getOption('strExperimentName'),
                   oPlate.getOption('strExperimentName'))

    def sort(self, *args, **options):
        self._oTable.sort(*args, **options)


class Labtek(_Plate):

    OPTIONS = \
        dict(tplDims             = Option((32,12)),
             tplPositionDistance = Option((1125,1125)),
             tplAxisOrientation  = Option((1,-1)),
             tplSubWells         = Option((1,1)),
             )

class Labtek8(Labtek):

    OPTIONS = \
        dict(tplDims             = Option((4,2)),
             tplPositionDistance = Option((13000,11000)),
             )

class Labtek6(Labtek8):

    OPTIONS = \
        dict(tplDims             = Option((3,2)),
             )


class Plate384(_Plate):

    OPTIONS = \
        dict(tplDims             = Option((24,16)),
             tplPositionDistance = Option((4500,4500)),
             tplAxisOrientation  = Option((1,-1)),
             tplSubWells         = Option((1,1)),
             )

class Plate384Norm(Plate384):

    OPTIONS = \
        dict(tplAxisOrientation  = Option((1,1)),
             )

class Plate384_4x3(Plate384):

    OPTIONS = \
        dict(tplSubWells         = Option((4,3)),
             )

class Plate96(_Plate):

    OPTIONS = \
        dict(tplDims             = Option((12,8)),
             tplPositionDistance = Option((9000,9000)),
             tplAxisOrientation  = Option((1,-1)),
             tplSubWells         = Option((1,1)),
             )

class Plate96Norm(Plate96):

    OPTIONS = \
        dict(tplAxisOrientation  = Option((1,1)),
             )

class Plate96_3x3(Plate96):

    OPTIONS = \
        dict(tplSubWells         = Option((3,3)),
             )

class Plate96_4x4(Plate96):

    OPTIONS = \
        dict(tplSubWells         = Option((4,4)),
             )

class LabtekFgcz(Labtek):

    OPTIONS = \
        dict(tplDims             = Option((33,12)),
             )

    def __init__(self, **dctOptions):
        super(LabtekFgcz, self).__init__(**dctOptions)


class PlateVisualizer(object):

    STR_PLOTTER_CLASS = 'RPlotter'

    def __init__(self, oPlate, **dctOptions):
        self._oPlate = oPlate
        from mito.plotter import RPlotter
        self._oPlotter = eval(self.STR_PLOTTER_CLASS)(**dctOptions)

    def compare(self, lstAnnotations, strColumnKey,
                tplYLim=None, strTitle=None,
                 **dctOptions):

        dctData = self._oPlate.getRecordsByAnnotation(lstAnnotations)
        lstNames = sorted(dctData.keys())
        oP = self._oPlotter
        oP.figure(**dctOptions)
        oP.par(mar=(11,4,3,1))
        oP.boxplot([dctData[x][0][strColumnKey] for x in lstNames],
                   col=[dctData[x][1][3] for x in lstNames],
                   xaxt='n', ylab=strColumnKey, ylim=tplYLim)
        oP.axis(1, range(1,len(dctData)+1),
                labels=["(%d) %s" % (len(dctData[x][0][strColumnKey]),x) for x in lstNames], las=2)

        if strTitle is None:
            strTitle = str(self._oPlate.strPlateId)
        oP.title(strTitle)
        oP.close()


    def histogram(self, strColumnKey, strTitle=None, **dctOptions):
        aData = self._oPlate.getData(strColumnKey)
        oP = self._oPlotter
        oP.figure(**dctOptions)
        #oP.par(mar=(7,4,3,1))
        oP.hist(aData,
                xlab=strColumnKey,
                ylab='likelihood',
                labels=False,
                freq=False)
        #if strTitle is None:
        #    strTitle = str(self._oPlate.strPlateId)
        #oP.title(strTitle)
        oP.close()


    def visualize(self, oData=None, lstZColors=None, bShowGrid=True,
                  lstAnnotations=None, tplZLim=None, strTitle=None,
                  bLegend=False, strAnnotationColor="#000000",
                  bMarkInvalid=False, bShowTour=False,
                  bMarkNone=True,
                  strTourColor="#000000aa",
                  legend_xlab="",
                  **dctOptions):
        from rpy import r

        oP = self._oPlotter
        iDimX, iDimY = self._oPlate.getOption('tplDims')

        # FIXME: this scaling is arbitrary
        if 'width' not in dctOptions:
            dctOptions['width'] = iDimX*24
        if 'height' not in dctOptions:
            if bLegend:
                dctOptions['height'] = iDimY*28
            else:
                dctOptions['height'] = iDimY*24

        oP.figure(**dctOptions)
        aDimX = asarray(range(1, iDimX+1))
        aDimY = asarray(range(1, iDimY+1))

        lstCoordinates = self._oPlate.getCoordinates(oFilter=lambda x: not x['Position'] is None)

        if oData is None:
            aData = self._oPlate.getEmptyArray(oValue=1)
        elif type(oData) == types.StringType:
            aData = self._oPlate.getData(oData)
        else:
            aData = oData

        #print aData

        if self._oPlate.getOption('tplAxisOrientation')[0] == -1:
            aData = aData[::-1,]
        if self._oPlate.getOption('tplAxisOrientation')[1] == 1:
            aData = aData[:,::-1]

        if lstZColors is None:
            lstZColors = oP.heat_colors(20)

        dctOptions = {}
        if tplZLim is None:
            tplZLim = oP.range(aData.flatten(), na_rm=True)
        dctOptions['breaks'] = r.seq(tplZLim[0], tplZLim[1], length_out=len(lstZColors)+1)
        #lstZColors = ['black'] + lstZColors

        #print aData

        if bLegend:
            oP.layout([[1],[2]], heights=(10,2))

        for i in range(len(aDimX)):
            for j in range(len(aDimY)):
                if aData[i,j] < tplZLim[0]:
                    aData[i,j] = tplZLim[0]
                elif aData[i,j] > tplZLim[1]:
                    aData[i,j] = tplZLim[1]

        oP.par(mar=(2,2.5,3,1))
        oP.image(aDimX, aDimY, aData,
                 col=lstZColors,
                 xaxs='i', yaxs='i',
                 xaxt='n', yaxt='n',
                 xlab='', ylab='',
                 **dctOptions)
#        if bMarkInvalid:
#            aDataValid = self._oPlate.getData('isValid')
#            oP.image(aDimX, aDimY, aDataValid,
#                     col=('black', 'transparent'),
#                     add=True,
#                     xaxs='i', yaxs='i',
#                     xaxt='n', yaxt='n',
#                     xlab='', ylab='',
#                     **dctOptions)
        oP.box(lwd=.5)

        if strTitle is None:
            strTitle = ""
        oP.title(strTitle)

#        if self._oPlate.getOption('tplAxisOrientation')[0] == -1:
#            lstXLabels = self._oPlate.coordinateToLabel(aDimX[::-1]-1, 'x')
#        else:
#            lstXLabels = self._oPlate.coordinateToLabel(aDimX-1, 'x')
#
#        if self._oPlate.getOption('tplAxisOrientation')[1] == -1:
#            lstYLabels = self._oPlate.coordinateToLabel(aDimY[::-1]-1, 'y')
#        else:
#            lstYLabels = self._oPlate.coordinateToLabel(aDimY-1, 'y')

        lstXLabels = self._oPlate.coordinateToLabel(aDimX-1, 'x')
        lstYLabels = self._oPlate.coordinateToLabel(aDimY[::-1]-1, 'y')

        oP.axis(1, aDimX, lstXLabels, las=2, cex_axis=.9, line=-.5, tick=False)
        oP.axis(2, aDimY, lstYLabels, las=2, cex_axis=.9, line=-.5, tick=False)

        if bShowGrid:
            for iX in aDimX[1:]:
                oP.abline(v=iX-0.5, col="#00000077")
            for iY in aDimY[1:]:
                oP.abline(h=iY-0.5, col="#00000077")

        #
        if bMarkInvalid:
            aDataValid = self._oPlate.getData('isValid')
            #print aDataValid

        for iY in aDimY:
            for iX in aDimX:
                if self._oPlate.getOption('tplAxisOrientation')[0] == -1:
                    iX2 = (iX - iDimX - 1) * -1
                else:
                    iX2 = iX
                if self._oPlate.getOption('tplAxisOrientation')[1] == 1:
                    iY2 = (iY - iDimY - 1) * -1
                else:
                    iY2 = iY
                if bMarkInvalid and not aDataValid[iX-1, iY-1]:
                    oP.points(iX2, iY2, pch='X', cex=1.0, lwd=2)
                elif bMarkNone and (aData[iX-1, iY-1] is None or isnan(aData[iX-1, iY-1])):
                    #oP.points(iX2, iY2, pch='?', cex=1.0, lwd=2)
                    oP.segments(iX2-0.5, iY2-0.5, iX2+0.5, iY2+0.5, col="#00000077", lwd=1)
                    oP.segments(iX2-0.5, iY2+0.5, iX2+0.5, iY2-0.5, col="#00000077", lwd=1)

        if lstAnnotations is not None:
            for dctAnnotation in lstAnnotations:
                strKey = dctAnnotation['k']
                strValue = dctAnnotation['v']
                strColor = dctAnnotation.get('c', strAnnotationColor)
                lstPos = self._oPlate.selectCoordinates(strKey, strValue)
                if len(lstPos) > 0:
                    aX = asarray([tplXY[0]+1 for tplXY in lstPos])
                    if self._oPlate.getOption('tplAxisOrientation')[0] == -1:
                        aX = (aX - iDimX - 1) * -1
                    aY = asarray([tplXY[1]+1 for tplXY in lstPos])
                    if self._oPlate.getOption('tplAxisOrientation')[1] == 1:
                        aY = (aY - iDimY - 1) * -1
                    if 't' in dctAnnotation:
                        oP.text(aX, aY, labels=dctAnnotation['t'], col=strColor, cex=0.8)
                    if 'f' in dctAnnotation:
                        oP.rect(aX-0.5, aY-0.5, aX+0.5, aY+0.5, col=dctAnnotation['f'])

        # show tour of microscope scan
        if bShowTour:
            tplLastP = None
            if len(lstCoordinates) > 0:
                lstCoordinates.append(lstCoordinates[0])
                for iX, iY in lstCoordinates[:-1]:
                    iX += 1
                    iY += 1
                    if self._oPlate.getOption('tplAxisOrientation')[0] == -1:
                        iX = (iX - iDimX - 1) * -1
                    if self._oPlate.getOption('tplAxisOrientation')[1] == 1:
                        iY = (iY - iDimY - 1) * -1
                    if tplLastP is not None:
                        oP.arrows(tplLastP[0], tplLastP[1],
                                  iX, iY,
                                  length=.1, angle=15,
                                  col=strTourColor)
                    tplLastP = (iX, iY)
            #oP.title("tour length: %.1f mm" % (self._oPlate.getTourLength() / 1000.0))

        if bLegend:
            oP.par(mar=(4,2.5,0,1), mgp=(2,0.5,0))
            aDimZ = oP.as_matrix(oP.seq(tplZLim[0], tplZLim[1], length_out=50))
            oP.image(aDimZ, 1, aDimZ, col=lstZColors,
                     xaxs='i', yaxs='i',
                     yaxt='n',
                     xlab=legend_xlab, ylab='',
                     cex_axis=.9,
                     cex=.9)
            oP.box(lwd=.5)

        oP.close()

    def showPlate(self, bShowTour=False, bShowGrid=True, **dctOptions):
        self.visualize(lstZColors=('white', 'red'),
                       bShowTour=bShowTour,
                       bShowGrid=bShowGrid,
                       **dctOptions)

#class PlateVisualizer(object):
#
#    CLS_PLOTTER = RPlotter
#
#    def __init__(self, oPlate, **dctOptions):
#        self._oPlate = oPlate
#        self._oPlotter = self.CLS_PLOTTER(**dctOptions)
#
#    def visualize(self, aData=None, lstZColors=None,
#                  bShowTour=False, bShowGrid=True,
#                  lstAnnotations=None, tplZLim=None,
#                  **dctOptions):
#        oP = self._oPlotter
#        iDimX, iDimY = self._oPlate.getOption('tplDims')
#
#        # FIXME: this scaling is arbitrary
#        if 'width' not in dctOptions:
#            dctOptions['width'] = iDimX*20
#        if 'height' not in dctOptions:
#            dctOptions['height'] = iDimY*24
#
#        oP.figure(**dctOptions)
#        aDimX = asarray(range(1, iDimX+1))
#        aDimY = asarray(range(1, iDimY+1))
#
#        lstPositions = self._oPlate.getCoordinates()
#
#        if aData is None:
#            aData = self._oPlate.getEmptyData()
#            for iX, iY in lstPositions:
#                aData[iX, iY] = 1
#
#        if lstZColors is None:
#            lstZColors = oP.heat_colors(20)
#
#        dctOptions = {}
#        if tplZLim is not None:
#            dctOptions['zlim'] = tplZLim
#
#        oP.image(aDimX, aDimY, aData,
#                 col=lstZColors,
#                 xaxs='i', yaxs='i',
#                 xaxt='n', yaxt='n',
#                 xlab='', ylab='',
#                 **dctOptions)
#
#        oP.axis(1, aDimX, map(str, aDimX), las=2)
#        oP.axis(2, aDimY, map(str, aDimY), las=2)
#
#        if bShowGrid:
#            for iX in aDimX:
#                oP.abline(v=iX-0.5, col="#00000077")
#            for iY in aDimY:
#                oP.abline(h=iY-0.5, col="#00000077")
#
#        #
#        if lstAnnotations is not None:
#            for tplAnnotation in lstAnnotations:
#                strKey, strValue, strChr, strColor = tplAnnotation
#                lstPos = self._oPlate.selectCoordinates(strKey, strValue)
#                lstX = [tplXY[0]+1 for tplXY in lstPos]
#                lstY = [tplXY[1]+1 for tplXY in lstPos]
#                oP.points(lstX, lstY, pch=strChr, col=strColor, cex=0.9)
#
#
#        # show tour of microscope scan
#        if bShowTour:
#            tplLastP = None
#            if len(lstPositions) > 0:
#                lstPositions.append(lstPositions[0])
#                for iX, iY in lstPositions:
#                    iX += 1
#                    iY += 1
#                    if tplLastP is not None:
#                        oP.arrows(tplLastP[0], tplLastP[1],
#                                  iX, iY,
#                                  length=.1, angle=15,
#                                  col="#00000088")
#                    tplLastP = (iX, iY)
#            oP.title("tour length: %.1f mm" % (self._oPlate.getTourLength() / 1000.0))
#
#        oP.close()
#
#    def showPlate(self, bShowTour=False, bShowGrid=True, **dctOptions):
#        self.visualize(lstZColors=('white', 'red'),
#                       bShowTour=bShowTour,
#                       bShowGrid=bShowGrid,
#                       **dctOptions)


if __name__ ==  "__main__":
#    oPlate = Labtek()
#    print oPlate
#
##    oPlateLayouter = ExcelMacroPlateLayouter('/Users/miheld/data/md/ms_exp345/exp345/_meta/exp345_screening_excel_macro_MD_80Locations.tsv')
##    oPlateMapper = ExcelMacroPlateMapper('/Users/miheld/data/md/exp500/exp500_071003_IBB_Screen_10x_Test.tsv')
##    oPlateMapper = ExcelMacroPlateMapper('/Volumes/Data/data/Analysis/md/exp500/exp500.tsv')
#    oPlateMapper = ExcelMacroPlateMapper('/Volumes/Data/data/Analysis/IBB_Screen/Q01_exp409/Q01_exp409.tsv')
#    oPlate.importMapping(oPlateMapper)
#
#    print oPlate
#    print oPlate.getTourLength()
#
#    oPlateVis = PlateVisualizer(oPlate, bUseCairo=True)
#
#    lstAnnotations = [('strGeneGroup', 'Neg. Control', 'N', '#00FF00'),
#                      ('strGeneGroup', 'Pos. Control', 'P', '#FF0000')]
#    oPlateVis.visualize(strFilename='moo1.png', bShowTour=True,
#                        lstZColors=('#FFFFFF', '#FF000055'),
#                        lstAnnotations=lstAnnotations)
#
#
#    oPlate.optimizePositions()
##    print oPlate
##    print oPlate.getTourLength()
##
##    oPlate.exportPlate('experiment_optimized.tsv')
##
##    oScanPositionWriter = MetaMorphPositionWriter('experiment_optimized.stg')
##    oPlate.exportScanPositions(oScanPositionWriter)
##
#    oPlateVis = PlateVisualizer(oPlate, bUseCairo=True)
#    oPlateVis.showPlate(strFilename='moo2.png', bShowTour=True)
##



#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase1_1/_exp655.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase1_1/exp655_3x3.tsv')

    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/CellBrowser/GerlichGroup/PPase_Validation/exp778/exp778.tsv')
    #m.convertMapping()
    p = Plate96_3x3()
    p.importMapping(m)
    print p
    exportTable(p._oTable, 'patrick_meander_96_3x3_mapping.tsv', fieldDelimiter='\t')

    p = Plate96()
    p.importMapping(m)
    vis = PlateVisualizer(p, bUseCairo=True)
    vis.visualize(strFilename='test.png', bShowTour=True, lstZColors=['#FFFF99'])

    #m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase8_2/exp638_3x3.tsv')

#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase2_1/_exp658.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase2_1/exp658_3x3.tsv')

#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase3_1/_exp659.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase3_1/exp659_3x3.tsv')

#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase4_1/_exp666.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase4_1/exp666_3x3.tsv')

#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase5_1/_exp662.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase5_1/exp662_3x3.tsv')

#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase6_1/_exp663.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase6_1/exp663_3x3.tsv')

#    m = ExcelMacroPlateMapper('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase7_1/_exp664.tsv')
#    m.convertMapping()
#    m.exportMapping('/Volumes/Data1T/Analysis/PPase_Screen_Taxol_exp687/PPase7_1/exp664_3x3.tsv')