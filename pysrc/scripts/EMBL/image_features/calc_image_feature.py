# general imports
import os, re, time, sys, pickle

# project imports
from cecog import ccore
from scripts.EMBL.settings import Settings

from scripts.EMBL.io.coordinate_generation import CoordinatesGeneration, RegexFilenameInterpreter


class ImageFeatureCalculator(object):
    def __init__(self, settings_filename):
        self.oSettings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())
        self.cg = CoordinatesGeneration(self.oSettings.EXP_DEFINITION)
        self.filenameInterpreter = RegexFilenameInterpreter(self.oSettings.regexScheme)

        # generate folders
        for folder in [
                       self.oSettings.output_dir,
                       self.oSettings.pickle_result_dir
                       ]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        self.prefix = 'abstract'
        return

    def readFilenames(self, inDir=None):
        if inDir is None:
            inDir = self.inDir
        imageInfo = self.cg.readCoordinatesFromFileStructure(inDir, self.filenameInterpreter)
        return imageInfo

    def getExpDict(self, imageInfo=None, inDir=None):
        if imageInfo is None:
            imageInfo = self.readFilenames(inDir)
        imgContainer = self.cg.getExpDict(imageInfo, self.oSettings.dctKeys)
        return imgContainer

    def calcFeature(self, imgContainer, pos, t, channels, primary_channel):
        raise NotImplementedError('The method calcFeature is not yet implemented.'
                                  'Please do not use the abstract class ImageFeatureCalculator.')

    def processLabtek(self, imgContainer, primary_channel, channels=None):
        image_feature = {}
        for pos in sorted(imgContainer.keys())[0:1]:
            image_feature[pos] = {}
            for t in sorted(imgContainer[pos].keys()):
                if channels is None:
                    channels = imgContainer[pos][t].keys()
                image_feature[pos][t] = self.calcFeature(imgContainer, pos, t,
                                                         channels, primary_channel)

        return image_feature


    def dump(self, image_feature, platename):
        filename = os.path.join(self.oSettings.pickle_result_dir, '%s_%s.pickle' % (self.prefix, platename))
        oFile = open(filename, 'w')
        pickle.dump(image_feature, oFile)
        oFile.close()
        print('%s written to disk' % filename)
        return

    def __call__(self, channels=None):
        for inDir in self.oSettings.lstIndir:
            print inDir
            self.inDir = inDir
            plate = os.path.split(os.path.realpath(inDir))[-1]
            print plate
            imageInfo = self.readFilenames()
            imgContainer = self.getExpDict(imageInfo)
            primary_channel = self.oSettings.primaryChannelDict[plate]
            image_feature = self.processLabtek(imgContainer, primary_channel, channels)
            self.dump(image_feature, plate)


class BackgroundLevel(ImageFeatureCalculator):

    def __init__(self, settings_filename):
        super(BackgroundLevel, self).__init__(settings_filename)
        self.prefix = 'background'

    def getBackgroundForImage(self, imgIn, imgMask, outFilenameBase=None):

        mask_histo = [x * imgMask.width * imgMask.height for x in imgMask.getHistogram(256)]
        area_objects = mask_histo[0]
        area_background = sum(mask_histo[1:])

        # pos, t, channel, path + filename
        imgConv = ccore.conversionTo8Bit(imgIn, 2**15, 2**15 + 4096, 0, 255)

        imgInf = ccore.infimum(imgMask, imgConv)
        inf_histo = [x * (imgInf.width * imgInf.height) / area_background  for x in imgInf.getHistogram(256)]

        if self.oSettings.write_images and not outFilenameBase is None:
            outDir = os.path.dirname(outFilenameBase)
            filename = os.path.basename(outFilenameBase)
            if not os.path.isdir(outDir):
                os.makedirs(outDir)
            ccore.writeImage(imgConv, os.path.join(outDir, 'convert_%s' % filename.replace('tif', 'png')))
            ccore.writeImage(imgInf, os.path.join(outDir, 'inf_%s' % filename.replace('tif', 'png')))


        # we exclude the object pixels from the analysis
        inf_histo[0] = 0

        # get statistical values
        meanval_background = sum([inf_histo[i] * i for i in range(256)])
        sumval = 0.0
        medianval_background = -1
        quantile25 = -1
        for i in range(256):
            sumval += inf_histo[i]
            if sumval >= 0.25 and quantile25 < 0:
                quantile25 = i
            if sumval >= 0.5 and medianval_background < 0:
                medianval_background = i
                break

        res = {'mean': meanval_background,
              'median': medianval_background,
              '25quantile': quantile25
              }

        return res

    def calcFeature(self, imgContainer, pos, t, channels, primary_channel):

        primary_filename = os.path.join(self.inDir,
                                        imgContainer[pos][t][primary_channel]['path'],
                                        imgContainer[pos][t][primary_channel]['filename'])
        imgMask = self.getBackgroundROI(primary_filename)

        res = {}
        for channel in channels:
            filename = os.path.join(self.inDir,
                                    imgContainer[pos][t][channel]['path'],
                                    imgContainer[pos][t][channel]['filename'])
            imgIn = ccore.readImageUInt16(filename)

            if self.oSettings.write_images:
                plate = os.path.split(os.path.realpath(self.inDir))[-1]
                outFilenameBase = os.path.join(self.oSettings.output_images_dir, plate,
                                               pos, imgContainer[pos][t][channel]['filename'])
            else:
                outFilenameBase = None
            res[channel] = self.getBackgroundForImage(imgIn, imgMask, outFilenameBase)

        return


    # can be replaced by the object detection (inverted).
    # However, border objects should not be removed before measuring background
    # intensity.
    def getBackgroundROI(self, primary_name):

        imgIn = ccore.readImageUInt16(primary_name)
        imgConv = ccore.conversionTo8Bit(imgIn, 2**15, 2**15 + 4096, 0, 255)
        imgSeg = ccore.window_average_threshold(imgConv, 50, 3)
        imgDil = ccore.dilate(imgSeg, 20, 8)
        imgMask = ccore.threshold(imgDil, 1, 255, 255, 0)

        return imgMask

class FocusMeasurement(ImageFeatureCalculator):

    def __init__(self, settings_filename):
        super(FocusMeasurement, self).__init__(settings_filename)
        self.method = 3
        self.gauss_sizes = [1, 2, 3, 4]
        self.prefix = 'focus_measurement'

    # gets relative focus measures for different filter sizes
    def getFocusMeasurementFilterSeries(self, imin, method=None, gauss_sizes=None):
        if method is None:
            method = self.method
        if gauss_sizes is None:
            gauss_sizes = self.gauss_sizes

        init_meas = ccore.focusQuantification(imin, method)
        res = {0: 1.0}
        for filter_size in gauss_sizes:
            impref = ccore.gaussianFilter(imin, filter_size)
            focus_meas = ccore.focusQuantification(impref, method)
            res[filter_size] = focus_meas / init_meas
        return res

    def calcFeature(self, imgContainer, pos, t, channels, primary_channel):

        res = {}
        for channel in channels:
            filename = os.path.join(self.inDir,
                                    imgContainer[pos][t][channel]['path'],
                                    imgContainer[pos][t][channel]['filename'])
            imgIn = ccore.readImageUInt16(filename)
            imgConv = ccore.conversionTo8Bit(imgIn, 2**15, 2**15 + 4096, 0, 255)

            res[channel] = self.getFocusMeasurementFilterSeries(imgConv, self.method, self.gauss_sizes)

        return res

