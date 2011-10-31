import os, re, time, sys
import shutil
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

from scripts.EMBL.settings import Settings

from collections import *

import scripts.EMBL.html_generation.event_page_generation
from scripts.EMBL.html_generation.event_page_generation import *

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc
# if rpy2 is going to be used: export PATH=/Users/twalter/software/R/R.framework/Resources/bin:${PATH}

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

#class PostProcessingWorkflow(object):

# works with the settings file scripts/EMBL/settings_files/lamin/lamin_postprocessing.py
class FeatureProjectionAnalysis(object):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())
        self._ts = None

    def importEventData(self, plates=None, positions=None):
        event_importer = scripts.EMBL.io.flatfileimporter.EventDescriptionImporter(settings=self.settings)
        impdata = event_importer(plates=plates, positions=positions)
        return impdata

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

    #def makeSingleCellPlotsForPlate(self, plates=None):
    #    return

    def batchHTMLPageGeneration(self, plates=None, make_single_cell_plots=False):
        if plates is None:
            plates = self.settings.plates
        for plate in plates:
            positions = self.getPositions(plate)
            for pos in positions:
                # import the movie data
                impdata = self.importEventData([plate], [pos])

                # get expression levels
                self.calcExpressionLevel(impdata)

                # reduce data set by QC
                self.applyQC(impdata, remove_qc_false=True, verbose=True)

                # calc the LDA projections
                self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])

                print 'making html page for %s %s' % (plate, pos)
                self.makeHTMLPages(impdata, [plate], [pos])
        return

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

    def calcTrackFeature(self, impdata, func,
                         plates=None, positions=None, tracks=None):
        #for plate in impdata.keys():
        #    for well in impdata[plate][]
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

    def _apply_qc(self, track_data):
        track_data['qc'] = True

        if track_data['expression_level'] is None:
            track_data['qc'] = False
            return

        # minimal expression level
        if 'min_exp_level' in self.settings.qc_rules and \
            not self.settings.qc_rules['min_exp_level'] is None and \
            track_data['expression_level'] < self.settings.qc_rules['min_exp_level']:
            # apply qc rule
            track_data['qc'] = False
            return

        # maximal expression level
        if 'max_exp_level' in self.settings.qc_rules and \
            not self.settings.qc_rules['max_exp_level'] is None and \
            track_data['expression_level'] > self.settings.qc_rules['max_exp_level']:
            # apply qc rule
            track_data['qc'] = False
            return

        # primary classification
        event_index = track_data['isEvent'].index(True)
        classification_results = track_data['primary']['primary']['class__name']

        # first rule: when interphase is reached without going through late mitotic phases
        if classification_results[event_index:].count('inter') > 3 and \
            classification_results[event_index:].count('earlyana') +  \
            classification_results[event_index:].count('lateana') +  \
            classification_results[event_index:].count('telo') < 3:
            track_data['qc'] = False
            return

        # second rule: when mitosis takes less than 20 minutes, the track is rejected.
        if classification_results.count('pro') + classification_results.count('prometa') + \
            classification_results.count('meta') + \
            classification_results.count('earlyana') +  classification_results.count('lateana') \
            < 10:
            track_data['qc'] = False
            return

        # third rule: when too many apoptosis are found, the track is rejected
        if classification_results[event_index:event_index+10].count('apo') >= 3 or \
            classification_results.count('apo') >= 6:
            track_data['qc'] = False
            return

        return

    def _calc_expression_level(self, track_data):
        channel = 'tertiary'
        new_region = 'diff_out_in'

        if not 'diff_out_in' in track_data[channel]:
            track_data[channel]['diff_out_in'] = {}

        track_data[channel]['diff_out_in']['feature__n2_avg'] = \
            [track_data[channel]['inside']['feature__n2_avg'][i] -
             track_data[channel]['outside']['feature__n2_avg'][i]
             for i in range(len(track_data[channel]['outside']['feature__n2_avg']))]

        event_index = track_data['isEvent'].index(True)
        classification_results = track_data['primary']['primary']['class__name']
        indices = filter(lambda i: classification_results[i] in ['inter','disformed'],
                         range(event_index))
        if len(indices) == 0:
            # in this case, no expression level was assigned.
            # therefore, the track has to be removed, and any other calc makes no sense.
            expression_level = None
            track_data['expression_level'] = expression_level
            return
        else:
            expression_level = numpy.mean([track_data[channel]['diff_out_in']['feature__n2_avg'][i]
                                           for i in indices])
        track_data['expression_level'] = expression_level

        track_data[channel]['diff_out_in']['feature__avg_norm'] = \
            [track_data[channel]['diff_out_in']['feature__n2_avg'][i] / expression_level
             for i in range(len(track_data[channel]['diff_out_in']['feature__n2_avg']))]

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

    def calcExpressionLevel(self, impdata):
        self.calcTrackFeature(impdata, self._calc_expression_level)
        return

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

    def makeLDAPlots(self, impdata):
        featureData = [('secondary', 'propagate', 'lda_projection')]
        classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
        self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])
        self.makeSingleCellPlots(impdata, featureData, classificationData)
        return


    def batchPlotGeneration(self, plates=None):

        if plates is None:
            plates = self.settings.plates

        for plate in plates:
            positions = self.getPositions(plate)
            for pos in positions:
                impdata = self.importEventData([plate], [pos])

                # get expression levels
                self.calcExpressionLevel(impdata)

                # reduce data set by QC
                self.applyQC(impdata, remove_qc_false=True, verbose=True)

                # calc the LDA projections
                self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])

                # dump a pickle file
                self.dumpPosEventData(impdata, plate, pos)

                # make the plots
                featureData = [('secondary', 'propagate', 'lda_projection')]
                classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
                self.makeSingleCellPlots(impdata, featureData, classificationData)

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

    #featureData = [('secondary', 'propagate', 'lda_projection')]
    #classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
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

