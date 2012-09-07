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

#-------------------------------------------------------------------------------
# standard library imports:
#

import numpy

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

class Normalizer(object):

    def __init__(self, strFilepath):
        oFile = file(strFilepath, "r")
        strLine = oFile.readline().rstrip()
        if strLine == "x":
            strLine = oFile.readline().rstrip()
        if strLine == "-1 1":
            self.iMode = 0
        else:
            self.iMode = 1
        self.lstScale = []
        for strLine in oFile:
            lstLine = strLine.rstrip().split(" ")
            self.lstScale.append((int(lstLine[0])-1, float(lstLine[1]),
                                  float(lstLine[2])))
        oFile.close()

    def scale(self, lstValues):
        #print self.iMode, len(lstValues), len(self.lstScale)
        if len(lstValues) != len(self.lstScale):
            raise ValueError('Length of value list (%d) differs from length '
                             'of scale factor list (%d)!' % \
                             (len(lstValues), len(self.lstScale)))
        if self.iMode == 0:
            # range [-1,1]
            lstResults = [2.0 * (lstValues[i] - lo) / (hi - lo + 0.0000001) - 1.0
                          for i,lo,hi in self.lstScale
                         ]
        else:
            # range [0,1]
            lstResults = [(lstValues[i] - lo) / (hi - lo + 0.0000001)
                          for i,lo,hi in self.lstScale
                         ]
        return lstResults

    __call__ = scale




class ArffReader(object):
    '''
    modified ARFF reader from Pradeep Kishore Gowda
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/440533
    '''

    DCT_DATA_TYPES = {'numeric': float,
                      'string' : str,
                     }

    def __init__(self, strFilename):
        self.oFile = file(strFilename, "r")
        self.strRelationName = ""
        self.dctClassNames = {}
        self.dctClassLabels = {}
        self.lstFeatureNames = []
        self.dctDataTypes = {}
        self.dctFeatureData = {}
        self.dctHexColors = {}
        self.hasZeroInsert = True
        self._read()
        self._close()

    def _convert_string(self, string):
        return string.replace('\'','').replace('"','')

    def _read(self):
        in_data = False

        lstClassNames = []
        lstClassLabels = []
        lstHexColors = []

        for line in self.oFile.readlines():
            line = line.rstrip()

            if len(line) > 0:

                if line[0] in ['@', '%']:
                    lstToken = line.split(' ')
                    first = lstToken[0].lower()

                    if first == '@relation':
                        self.strRelationName = lstToken[1]

                    elif first == '@attribute':
                        if lstToken[2][0] == '{':
                            i1 = line.find('{')
                            i2 = line.find('}')
                            assert i1 != i2 != -1
                            lstClassNames = [self._convert_string(x)
                                             for x in line[i1+1:i2].split(',')]
                            setClassNames = set(lstClassNames)
                        else:
                            strFeatureName = lstToken[1]
                            strDataType = lstToken[2].lower()
                            self.lstFeatureNames.append(strFeatureName)
                            self.dctDataTypes[strFeatureName] = \
                                self.DCT_DATA_TYPES[strDataType]

                    elif first == '%class-labels':
                        if lstToken[1][0] == '{':
                            i1 = line.find('{')
                            i2 = line.find('}')
                            assert i1 != i2 != -1
                            lstClassLabels = [int(self._convert_string(x))
                                              for x in
                                              line[i1+1:i2].split(',')]

                    elif first == '%class-colors':
                        if lstToken[1][0] == '{':
                            i1 = line.find('{')
                            i2 = line.find('}')
                            assert i1 != i2 != -1
                            lstHexColors = [self._convert_string(x).upper()
                                            for x in
                                            line[i1+1:i2].split(',')]

                    elif first == '%has-zero-inserted-in-feature-vector':
                        self.hasZeroInsert = int(lstToken[1]) != 0

                    elif first == '@data':
                        in_data = True

                elif in_data:
                    lstItems = line.split(',')
                    strClassName = self._convert_string(lstItems[-1])
                    lstItems = lstItems[:-1]
                    #print strClassName, lstClassNames
                    assert strClassName in setClassNames
                    assert len(lstItems) == len(self.lstFeatureNames)
                    lstFeatureData = []
                    for strFeatureName, item in zip(self.lstFeatureNames,
                                                    lstItems):
                        if self.dctDataTypes[strFeatureName] == str:
                            value = self._convert_string(item)
                        else:
                            value = self.dctDataTypes[strFeatureName](item)
                        lstFeatureData.append(value)
                    if strClassName not in self.dctFeatureData:
                        self.dctFeatureData[strClassName] = []
                    self.dctFeatureData[strClassName].append(lstFeatureData)

        for strClassName in self.dctFeatureData:
            self.dctFeatureData[strClassName] = numpy.array(self.dctFeatureData[strClassName], numpy.float)

        for iClassLabel, strClassName in zip(lstClassLabels, lstClassNames):
            self.dctClassLabels[strClassName] = iClassLabel
            self.dctClassNames[iClassLabel] = strClassName

        for hexColor, strClassName in zip(lstHexColors, lstClassNames):
            self.dctHexColors[strClassName] = hexColor


    def _close(self):
        self.oFile.close()


class WriterBase(object):

    FLOAT_DIGITS = 8

    def __init__(self, strFilename, lstFeatureNames, dctClassLabels):
        self.oFile = file(strFilename, "w")
        self.lstFeatureNames = lstFeatureNames
        self.dctClassLabels = dctClassLabels

    def close(self):
        self.oFile.close()

    @classmethod
    def buildLineStatic(cls, strClassName, lstObjectFeatures, dctClassLabels):
        raise NotImplementedError("This is an abstract method!")

    def buildLine(self, strClassName, lstObjectFeatures):
        return self.buildLineStatic(strClassName, lstObjectFeatures,
                                    self.dctClassLabels)

    def writeLine(self, strLine=""):
        self.oFile.write(strLine+"\n")

    def writeLineList(self, lstLine):
        for strLine in lstLine:
            self.writeLine(strLine)

    def writeObjectFeatureData(self, strClassName, lstObjectFeatureData):
        self.writeLine(self.buildLine(strClassName, lstObjectFeatureData))

    def writeAllFeatureData(self, dctFeatureData):
        for strClassName in dctFeatureData:
            for lstObjectFeatureData in dctFeatureData[strClassName]:
                self.writeObjectFeatureData(strClassName, lstObjectFeatureData)

    @classmethod
    def _convert(cls, f):
        return "%%.%de" % cls.FLOAT_DIGITS % f


class SparseWriter(WriterBase):

    def __init__(self, strFilename, lstFeatureNames, dctClassLabels):
        super(SparseWriter, self).__init__(strFilename, lstFeatureNames,
                                           dctClassLabels)

    @classmethod
    def buildLineStatic(cls, strClassName, lstObjectFeatures, dctClassLabels):
        strLine = " ".join(["%d" % dctClassLabels[strClassName]] +
                           ["%d:%s" % (iIdx+1, cls._convert(fObjectFeature))
                            for iIdx, fObjectFeature in
                            enumerate(lstObjectFeatures)]
                           )
        return strLine



class TsvWriter(WriterBase):

    def __init__(self, strFilename, lstFeatureNames, dctClassLabels):
        super(TsvWriter, self).__init__(strFilename, lstFeatureNames,
                                        dctClassLabels)
        self.writeLine("\t".join(["Class Name", "Class Label"] +
                                 self.lstFeatureNames))

    @classmethod
    def buildLineStatic(cls, strClassName, lstObjectFeatures, dctClassLabels):
        line = "\t".join([strClassName] +
                         ["%d" % dctClassLabels[strClassName]] +
                         [cls._convert(fObjectFeature)
                          for fObjectFeature in lstObjectFeatures]
                         )
        return line



class ArffWriter(WriterBase):

    def __init__(self, strFilename, lstFeatureNames, dctClassLabels,
                 dctHexColors=None, hasZeroInsert=False):
        super(ArffWriter, self).__init__(strFilename, lstFeatureNames,
                                         dctClassLabels)
        self.writeLine("@RELATION CecogClassifier")
        self.writeLine()
        for strFeatureName in self.lstFeatureNames:
            self.writeLine("@ATTRIBUTE %s NUMERIC" % strFeatureName)

        lstClassNames = self.dctClassLabels.keys()
        # sort names by labels
        lstClassNames.sort(key = lambda n: self.dctClassLabels[n])
        self.writeLine("@ATTRIBUTE class {%s}" %
                       ",".join(["'%s'" % x
                                 for x in lstClassNames])
                       )
        self.writeLine()
        self.writeLine("%%CLASS-LABELS {%s}" %
                       ",".join(["%s" % self.dctClassLabels[x]
                                 for x in lstClassNames])
                       )
        if dctHexColors is not None:
            self.writeLine("%%CLASS-COLORS {%s}" %
                           ",".join(["%s" % dctHexColors[x]
                                     for x in lstClassNames])
                           )
        self.writeLine()

        self.writeLine('%%HAS-ZERO-INSERTED-IN-FEATURE-VECTOR %d' %
                       (1 if hasZeroInsert else 0))
        self.writeLine()

        self.writeLine("@DATA")

    @classmethod
    def buildLineStatic(cls, strClassName, lstObjectFeatures, dctClassLabels):
        strLine = ",".join(map(cls._convert, lstObjectFeatures) +
                           ["'%s'" % strClassName]
                           )
        return strLine

    def close(self):
        self.writeLine()
        super(ArffWriter, self).close()


