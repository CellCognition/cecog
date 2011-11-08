import os, re, time, sys
import shutil
import string

import numpy

import scripts.EMBL.feature_projection.lda
reload(scripts.EMBL.feature_projection.lda)
from scripts.EMBL.feature_projection.lda import ScikitLDA, TrainingSet

import scripts.EMBL.io.flatfileimporter
reload(scripts.EMBL.io.flatfileimporter)

import scripts.EMBL.plotter.feature_timeseries_plotter
reload(scripts.EMBL.plotter.feature_timeseries_plotter)

import pickle

from scripts.EMBL.plotter.feature_timeseries_plotter import TimeseriesPlotter
import scripts.EMBL.plotter.stats
reload(scripts.EMBL.plotter.stats)

from scripts.EMBL.settings import Settings

from collections import *

import scripts.EMBL.html_generation.event_page_generation
from scripts.EMBL.html_generation.event_page_generation import *

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc
# if rpy2 is going to be used: export PATH=/Users/twalter/software/R/R.framework/Resources/bin:${PATH}

# example of usage:
# copy_stats_analysis('/Volumes/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_output',
# '/Users/twalter/data/Moritz_cecog/cecog_output')
def copy_stats_analysis(source_dir, target_dir, lst_plates=None):
    if lst_plates is None:
        lst_plates = filter(lambda x: os.path.isdir(os.path.join(source_dir, x)),
                            os.listdir(source_dir))

    for lt in lst_plates:
        print lt
        lt_dir = os.path.join(source_dir, lt, 'analyzed')
        shutil.copytree(lt_dir, os.path.join(target_dir, lt, "analyzed"),
                        ignore=shutil.ignore_patterns('*.tif', '*.jpg', '*.png', '*.tiff'))

    return


class PostProcessingWorkflow(object):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())

    def _apply_qc(self):
        raise NotImplemented('')
        return

    def _process(self):
        raise NotImplemented('')
        return

    def groupData(self, impdata, plates=None):
        if plates is None:
            plates = impdata.keys()

        #omitted_tracks = []
        for plate in plates:
            positions = sorted(impdata[plate].keys())
            for pos in positions:
                searchres = self.settings.subpos_regex.search(pos)
                if searchres is None:
                    raise ValueError("Naming of positions %s is not conform with the given regular expression." % pos)
                well = searchres.groupdict()['Well']
                subpos = searchres.groupdict()['Subwell']
                if not well in impdata[plate]:
                    impdata[plate][well] = {}
                for track in impdata[plate][pos].keys():
                    #if track in impdata[plate][well]:
                    #    omitted_tracks.append(track)
                    #    continue
                    impdata[plate][well]['%s__%s' % (track, subpos)] = impdata[plate][pos][track]
                del(impdata[plate][pos])
            #print 'for plate %s: %i omitted tracks (same name for different positions)' % (plate, len(omitted_tracks))
        return

    def importEventData(self, plates=None, positions=None):
        event_importer = scripts.EMBL.io.flatfileimporter.EventDescriptionImporter(settings=self.settings)
        impdata = event_importer(plates=plates, positions=positions)
        return impdata

    def importAndDumpEventData(self, plates=None):
        if plates is None:
            plates = filter(lambda x: os.path.isdir(x),
                            os.listdir(os.path.join(self.settings.base_analysis_dir,
                                                    'analyzed')))

        for plate in plates:
            starttime = time.time()
            print
            print 'importing %s' % plate
            impdata = self.importEventData([plate])
            self.dumpPlateEventData(impdata, plate)
            diffTime = time.time() - startTime
            print 'elapsed time: %02i:%02i:%02i' % ((diffTime/3600),
                                                    ((diffTime%3600)/60),
                                                    (diffTime%60))
        return

    def getPositions(self, plate):
        event_importer = scripts.EMBL.io.flatfileimporter.EventDescriptionImporter(settings=self.settings)
        positions = event_importer.getPositionsForPlate(plate)
        return positions

    def dumpPlateEventData(self, impdata, plate):
        filename = os.path.join(self.settings.track_data_dir,
                                'track_data--%s.pickle' % plate)
        track_file = open(filename, 'w')
        pickle.dump(impdata, track_file)
        track_file.close()
        return

    def dumpPosEventData(self, impdata, plate, position):
        filename = os.path.join(self.settings.importDir, plate,
                                'track_data--%s--%s.pickle' % (plate, position))
        if not os.path.exists(os.path.join(self.settings.importDir, plate)):
            os.makedirs(os.path.join(self.settings.importDir, plate))

        track_file = open(filename, 'w')
        pickle.dump(impdata, track_file)
        track_file.close()
        return

    def applyQC(self, impdata, remove_qc_false = True, verbose=True):
        self.calcTrackFeature(impdata, self._apply_qc)

        if remove_qc_false:
            for plate in impdata.keys():
                for pos in impdata[plate].keys():
                    good_tracks = filter(lambda x: impdata[plate][pos][x]['qc'],
                                         impdata[plate][pos].keys())
                    print 'plate: %s\tposition: %s\tnumber of passed tracks: %i / %i\t' \
                        % (plate, pos, len(good_tracks), len(impdata[plate][pos]))
                    for track in impdata[plate][pos].keys():
                        if not impdata[plate][pos][track]['qc']:
                            del(impdata[plate][pos][track])
        return

    def calcTrackFeature(self, impdata, func,
                         plates=None, positions=None, tracks=None):

        if plates is None:
            plates = impdata.keys()

        for lt in plates:
            if positions is None:
                positions = impdata[lt].keys()

            for pos in positions:
                if tracks is None:
                    tracks = impdata[lt][pos].keys()

                for track in tracks:
                    func(impdata[lt][pos][track])
        return


    def makeHTMLPages(self, impdata,
                      plates=None, wells=None):
        if plates is None:
            plates = impdata.keys()

        hg = scripts.EMBL.html_generation.event_page_generation.HTMLGenerator(settings=self.settings)

        for plate in plates:
            if wells is None:
                wells = impdata[plate].keys()
            for well in wells:
                print 'exporting HTML for %s %s' % (plate, well)
                hg.exportTracksHTML(plate, well, impdata)

        return

    def batchHTMLPageGeneration(self, plates=None):
        if plates is None:
            plates = self.settings.plates
        for plate in plates:
            positions = self.getPositions(plate)
            for pos in positions:
                # import the movie data
                impdata = self.importEventData([plate], [pos])

                self._process(impdata)

                print 'making html page for %s %s' % (plate, pos)
                self.makeHTMLPages(impdata, [plate], [pos])
        return

    def batchPlotGeneration(self, plates=None):

        if plates is None:
            plates = self.settings.plates

        for plate in plates:
            positions = self.getPositions(plate)
            for pos in positions:
                impdata = self.importEventData([plate], [pos])

                self._process(impdata)

                # make the plots
                #featureData = [('secondary', 'propagate', 'lda_projection')]
                #classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
                featureData = self.settings.single_cell_plot_settings['featureData']
                classificationData = self.settings.single_cell_plot_settings['classificationData']
                self.makeSingleCellPlots(impdata, featureData, classificationData)

        return

    def extractTrackFeature(self, impdata, plate, pos, value_extraction=None,
                            lstTracks=None):
        if lstTracks is None:
            lstTracks = sorted(impdata[plate][pos].keys())

        if value_extraction is None:
            value_extraction = self.settings.value_extraction

        res = {}
        for track in lstTracks:
            res[track] = {}
            for feature, proc_tuple in value_extraction.iteritems():
                if len(proc_tuple) == 1:
                    res[track][feature] = impdata[plate][pos][track][proc_tuple[0]]
                elif len(proc_tuple) == 4:
                    res[track][feature] = proc_tuple[0](impdata[plate][pos][track][proc_tuple[1]][proc_tuple[2]][proc_tuple[3]])
                elif len(proc_tuple) == 7:
                    res[track][feature] = proc_tuple[0](impdata[plate][pos][track][proc_tuple[1]][proc_tuple[2]][proc_tuple[3]],
                                                        impdata[plate][pos][track][proc_tuple[4]][proc_tuple[5]][proc_tuple[6]])

        return res

    def makeTrackFeatureBarplot(self, impdata,
                                value_extraction=None,
                                plates=None, positions=None):

        if plates is None:
            plates = sorted(impdata.keys())

        if value_extraction is None:
            value_extraction = self.settings.value_extraction

        plotter = scripts.EMBL.plotter.stats.Barplot()

        for plate in plates:
            if positions is None:
                positions = sorted(impdata[plate].keys())
            for feature in value_extraction.keys():
                plot_data = {}
                for pos in positions:
                    ext_data = self.extractTrackFeature(impdata, plate, pos, value_extraction)

                    plot_data[pos] = [ext_data[track][feature] for track in ext_data.keys()]

                prep = plotter.prepareDataForSingleBarplot(plot_data)

                plotDir = os.path.join(self.settings.plotDir,
                                       'plate_overview',
                                       plate)
                if not os.path.isdir(plotDir):
                    os.makedirs(plotDir)
                filename = os.path.join(plotDir, '%s--%s.png' % (plate, feature))

                print prep['datavec']
                print prep['errorvec']

                plotter.singleBarplot(prep['datavec'],
                                      filename,
                                      color=None,
                                      errorvec=None, #prep['errorvec'],
                                      width=0.7,
                                      bartitles=sorted(positions),
                                      title = 'Means: %s for %s' % (feature, plate),
                                      xlab='', ylab=feature,
                                      xlim=None, ylim=None)

        return

    # example: featureData = [('secondary', 'propagate', 'lda_projection')]
    # example: classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
    def makeSingleCellPlots(self, impdata, featureData, classificationData=None,
                            plates=None, wells=None, tracks=None):
        if plates is None:
            plates = impdata.keys()

        plotter = scripts.EMBL.plotter.feature_timeseries_plotter.TimeseriesPlotter()

        for plate in plates:
            if wells is None:
                wells = sorted(impdata[plate].keys())
            for well in wells:
                if tracks is None:
                    tracks = sorted(impdata[plate][well].keys())

                out_path = os.path.join(self.settings.singleCellPlotDir,
                                        plate, well)
                if not os.path.exists(out_path):
                    os.makedirs(out_path)

                for track in tracks:
                    timevec = impdata[plate][well][track]['Frame']
                    event_index = impdata[plate][well][track]['isEvent'].index(True)
                    vertical_lines = {'event': {'x': timevec[event_index]}}

                    features = [x[-1].split('__')[-1] for x in featureData]
                    filename = os.path.join(out_path,
                                            'singlecell_%s.png' % \
                                            '_'.join([plate, well, track]
                                                     + features))
                    title = ' '.join([plate, well, track] + features)

                    datamatrix = numpy.array([impdata[plate][well][track][channel][region][feature]
                                              for channel, region, feature in featureData],
                                              dtype=numpy.float64)

                    classification_results = OrderedDict()
                    colorvals = OrderedDict()
                    classification_legends = OrderedDict()
                    legend_titles = OrderedDict()
                    for channel, region in classificationData:
                        classification_results[(channel, region)] = \
                            impdata[plate][well][track][channel][region]['class__name']

                        colorvals[(channel, region)] = \
                            [self.settings.class_color_code[(channel, region)]['color_code'][x]
                             for x in classification_results[(channel, region)]]

                        phenoClasses = self.settings.class_color_code[(channel, region)]['class_list']

                        classification_legends[(channel, region)] = \
                            (phenoClasses,
                             [self.settings.class_color_code[(channel, region)]['color_code'][x]
                              for x in phenoClasses])
                        legend_titles[(channel, region)] = \
                            self.settings.class_color_code[(channel, region)]['legend_title']

                    plotter.makeTimeseriesPlot(timevec,
                                               datamatrix,
                                               filename,
                                               title=title,
                                               xlabel='Time (Frames)',
                                               ylabel=feature,
                                               #linecolors=['#0000ff'],
                                               colorvals=colorvals,
                                               classification_legends=classification_legends,
                                               vertical_lines=vertical_lines,
                                               legend_titles=legend_titles,
                                               )
        return

# works with the settings file scripts/EMBL/settings_files/lamin/lamin_postprocessing.py
class FeatureProjectionAnalysis(object):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())
        #PostProcessingWorkflow.__init__(self, settings=settings)
        self._ts = None

    def learnDirection(self, trainingset_filename=None):
        if trainingset_filename is None:
            trainingset_filename = self.settings.trainingset_filename

        self._ts = TrainingSet()
        self._ts.readArffFile(trainingset_filename)
        Xtemp, y = self._ts(trainingset_filename,
                            features_remove=self.settings.FEATURES_REMOVE,
                            correlation_threshold=0.99,
                            phenoClasses=self.settings.PHENOCLASSES_FOR_TRAINING,
                            normalization_method='z',
                            recode_dictionary=None)
        X = numpy.float64(Xtemp)
        lda = ScikitLDA()
        self._weights = lda.weights(X, y)

        return

    def makeSingleCellFeatureProjection(self, impdata, lt, pos, track,
                                         channel, region):
        featurenames = self._ts.getFeatureNames()
        frameVec = impdata[lt][pos][track]['Frame']
        Xpy = [[impdata[lt][pos][track][channel][region]['feature__' + x][i]
                for x in featurenames] for i in range(len(frameVec))]
        X = numpy.array(Xpy, dtype=numpy.float64)
        Xnorm = (X - self._ts._avg) / self._ts._stdev
        projections = numpy.dot(Xnorm, self._weights)
        return projections


    def calcProjections(self, impdata, plates=None, positions=None,
                        tracks=None, channels=None, regions=None):
        if self._ts is None:
            self.learnDirection()

        if plates is None:
            plates = impdata.keys()

        for lt in plates:
            if positions is None:
                positions = impdata[lt].keys()

            for pos in positions:
                if tracks is None:
                    tracks = impdata[lt][pos].keys()

                for track in tracks:
                    # The channels cannot be derived from the track
                    # keys because there are other track associated features.
                    if channels is None:
                        channels = self.settings.import_entries_event.keys()

                    for channel in channels:
                        if regions is None:
                            regions = impdata[lt][pos][track][channel].keys()

                        for region in regions:
                            impdata[lt][pos][track][channel][region]['lda_projection'] = \
                                self.makeSingleCellFeatureProjection(impdata, lt, pos,
                                                                     track, channel, region)

        return

#    def makeLDAPlots(self, impdata):
#        featureData = [('secondary', 'propagate', 'lda_projection')]
#        classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
#        self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])
#        self.makeSingleCellPlots(impdata, featureData, classificationData)
#        return

