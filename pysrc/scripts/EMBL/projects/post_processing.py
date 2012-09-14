import os, re, time, sys
import shutil
import string

import numpy

#import scripts.EMBL.feature_projection.lda
#reload(scripts.EMBL.feature_projection.lda)
from scripts.EMBL.learning.training_set import TrainingSet

from sklearn import svm
from sklearn import lda
from sklearn.linear_model import LogisticRegression

#from sklearn import cross_validation
#from sklearn.feature_selection import RFE
#from sklearn.cross_validation import StratifiedKFold
#from sklearn.feature_selection import RFECV
#from sklearn.metrics import zero_one
#import sklearn.feature_selection.univariate_selection


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

import scripts.EMBL.cutter.data_for_cutouts
reload(scripts.EMBL.cutter.data_for_cutouts)

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

class TimeseriesConditioner(object):

    def get_indices(self, impdata, plate, pos, track, channel, region):
        raise NotImplementedError("TimeseriesConditioner is a virtual base class.")
        return

    def extractTimeVector(self, impdata, plate, pos, track, channel, region):
        start_index, end_index = self.get_indices(impdata, plate, well, track, channel, region)
        timevec = impdata[plate][well][track]['Frame'][start_index:end_index]
        return timevec

    def extractDataMatrix(self, impdata, plate, pos, track, channel, region, feature):
        start_index, end_index = self.get_indices(impdata, plate, well, track, channel, region)
        datamatrix = numpy.array([impdata[plate][well][track][channel][region][feature][start_index:stop_index]
                      for channel, region, feature in featureData],
                      dtype=numpy.float64)
        return datamatrix

class CutAfterPhase(TimeseriesConditioner):
    """Cuts after the phase phenoClass.
    For instance a sequence I-I-I-P-PM-PM-M-M-M-M-AN-AN-T-I-I
    will be cut after the metaphase by CutAfterPhase('Metaphase')
    """
    def __init__(self, phenoClass):
        self.phenoClass = phenoClass

    def get_axis(self, datamatrix, timevec, impdata):
        plate = impdata.keys()[0]
        pos = impdata[plate].keys()[0]
        track = impdata[plate][pos].keys()[0]

        ymin = impdata[plate][well][track]['Frame'][0]
        ymax = impdata[plate][well][track]['Frame'][-1]
        ymin -= 0.05 * (ymax - ymin)
        ymax += 0.05 * (ymax - ymin)

        xmin = min(datamatrix)
        xmax = max(datamatrix)
        xmin -= 0.05 * (xmax - xmin)
        xmax += 0.05 * (xmax - xmin)

        return (xmin, xmax, ymin, ymax)

    def get_indices(self, impdata, plate, well, track, channel, region):
        if not 'class__name' in impdata[plate][well][track][channel][region]:
            raise ValueError('no classification results for %s' % ', '.join([plate, well, track, channel, region]))

        # HERE I AM
        classVec = numpy.array(impdata[plate][well][track][channel][region]['class__name'])

        # start_index is fixed to 0 (we always plot from the start)
        start_index = 0

        # end index is found by finding the first transition
        # from (phenoClass) to (not phenoClass)
        truevec = classVec==self.phenoClass
        end_index = [truevec[i] and not truevec[i+1] for i in range(len(truevec) - 1)].index(True)

        return start_index, end_index



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

    def batchPanelGeneration(self, plates=None):

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
                if 'featureData' in self.settings.panel_settings:
                    featureData = self.settings.panel_settings['featureData']
                else:
                    featureData = None
                if 'classificationData' in self.settings.panel_settings:
                    classificationData = self.settings.panel_settings['classificationData']
                else:
                    classificationData = None
                self.makePanels(impdata, featureData, classificationData)

        return

    def _export_track_data(self, impdata):
        plates = impdata.keys()
        if not os.path.exists(self.settings.feature_export_dir):
            os.makedirs(self.settings.feature_export_dir)
        for plate in plates:
            print 'exporting ', plate
            positions = impdata[plate].keys()
            if len(positions) == 1:
                export_path = os.path.join(self.settings.feature_export_dir, plate)
                if not os.path.exists(export_path):
                    os.makedirs(export_path)
                pos = positions[0]
                filename = os.path.join(export_path, '%s--%s.pickle' % (plate, pos))
            else:
                filename = os.path.join(self.settings.feature_export_dir, '%s.pickle' % plate)
            fp = open(filename, 'w')
            pickle.dump(impdata, fp)
            fp.close()
            #positions = self.getPositions
        return

    def batchExport(self, plates=None):
        if plates is None:
            plates = self.settings.plates

        for plate in plates:
            positions = self.getPositions(plate)
            for pos in positions:
                impdata = self.importEventData([plate], [pos])

                self._process(impdata)
                self._export_track_data(impdata)

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
                for plot_name in self.settings.single_cell_plot_settings.keys():
                    #featureData = [('secondary', 'propagate', 'lda_projection')]
                    #classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
                    featureData = self.settings.single_cell_plot_settings[plot_name]['featureData']
                    classificationData = self.settings.single_cell_plot_settings[plot_name]['classificationData']
                    if 'condition' in self.settings.single_cell_plot_settings[plot_name]:
                        timeseries_condition = self.settings.single_cell_plot_settings[plot_name]['condition']
                    else:
                        timeseries_condition = None
                    self.makeSingleCellPlots(impdata, featureData, classificationData, filename_id=plot_name,
                                             timeseries_condition=timeseries_condition)

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

    def makePanels(self, impdata, featureData=None, classificationData=None,
                   plates=None, wells=None, tracks=None):
        if plates is None:
            plates = impdata.keys()

        cp = scripts.EMBL.cutter.data_for_cutouts.ClassificationPanel(single_image_width=self.settings.gallery_single_image_width,
                                                                      panel_height=5)
        for plate in plates:
            if wells is None:
                wells = sorted(impdata[plate].keys())
            for well in wells:
                if tracks is None:
                    tracks = sorted(impdata[plate][well].keys())

                out_path = os.path.join(self.settings.panelDir,
                                        plate, well)
                if not os.path.exists(out_path):
                    os.makedirs(out_path)

                for track in tracks:
                    # classification panels
                    for panel, channel, region in classificationData:
                        classificationVec = \
                            impdata[plate][well][track][channel][region]['class__name']
                        colorvals = \
                            [self.settings.class_color_code[(channel, region)]['color_code'][x]
                             for x in classificationVec]
                        filename = os.path.join(out_path,
                                                '%s--%s.png' % (panel, track))
                        cp(filename, colorvals)

                    #timevec = impdata[plate][well][track]['Frame']
                    #event_index = impdata[plate][well][track]['isEvent'].index(True)

        return


    # example: featureData = [('secondary', 'propagate', 'lda_projection')]
    # example: classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
    def makeSingleCellPlots(self, impdata, featureData, classificationData=None,
                            plates=None, wells=None, tracks=None, filename_id=None,
                            timeseries_condition=None):
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
                    if timeseries_condition is None:
                        timevec = impdata[plate][well][track]['Frame']
                    else:
                        timevec = timeseries_condition.extractTimeVector(impdata, plate, pos, track, channel, region)

                    event_index = impdata[plate][well][track]['isEvent'].index(True)
                    vertical_lines = {'event': {'x': timevec[event_index]}}

                    features = [x[-1].split('__')[-1] for x in featureData]
                    if filename_id is None:
                        filename = os.path.join(out_path,
                                                'singlecell_%s.png' % \
                                                '_'.join([plate, well, track]
                                                         + features))
                    else:
                        filename = os.path.join(out_path,
                                                'singlecell_%s.png' % \
                                                '_'.join([plate, well, track, filename_id]))

                    title = ' '.join([plate, well, track] + features)

                    if not timeseries_condition is None:
                        datamatrix = timeseries_condition.extractDataMatrix(impdata, plate, pos, track, channel, region, feature)
                    else:
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
                                               colnames=[x[-1].split('__')[-1] for x in featureData]
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

    def DEPRECATEDlearnDirection(self, trainingset_filename=None):
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

    def learnClassifier(self, trainingset_filename=None, method='lda', features=None):
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

        all_features = self._ts.getFeatureNames()

        if method == 'lda':
            clf = lda.LDA()
        if method == 'svm':
            clf = svm.SVC(kernel='linear', probability=True, shrinking=True)
        if method == 'logres':
            clf = LogisticRegression(C=1.0, penalty='l2')

        if features is None:
            print 'learning: ', method
            clf.fit(X, y)
        else:
            indices = numpy.array(filter(lambda x: all_features[x] in features,
                                         range(len(all_features))), dtype=numpy.integer)
            print 'learning: ', method, ' with feature selection'
            clf.fit(X[:,indices], y)


#        prob = clf.predict_proba(X)
#        log_prob = clf.predict_log_proba(X)
#        dec = clf.decision_function(X)
#        proj = clf.transform(X)
#        res = numpy.append(prob, dec, axis=1)
#        res = numpy.append(res, proj, axis=1)
#        res = numpy.append(res, log_prob[:,0].reshape((nb_samples, 1)), axis=1)
#        columns = ['lda_p0', 'lda_p1', 'lda_dec0', 'lda_dec1', 'lda_proj', 'lda_logprob']

        #lda = ScikitLDA()
        #self._weights = lda.weights(X, y)

        return clf

    def DEPRECATEDmakeSingleCellFeatureProjection(self, impdata, lt, pos, track,
                                         channel, region):
        featurenames = self._ts.getFeatureNames()
        frameVec = impdata[lt][pos][track]['Frame']
        Xpy = [[impdata[lt][pos][track][channel][region]['feature__' + x][i]
                for x in featurenames] for i in range(len(frameVec))]
        X = numpy.array(Xpy, dtype=numpy.float64)
        Xnorm = (X - self._ts._avg) / self._ts._stdev
        projections = numpy.dot(Xnorm, self._weights)
        return projections

    def normalizeSingleCellFeature(self, impdata, lt, pos, track,
                                   channel, region, feature):
        featurenames = ['feature__' + x for x in self._ts.getFeatureNames()]

        if len(feature.split('__')) == 0:
            feature = '__'.join(['feature', feature])

        feature_index = featurenames.index(feature)

        frameVec = impdata[lt][pos][track]['Frame']
        temp = [impdata[lt][pos][track][channel][region][feature][i]
                for i in range(len(frameVec))]
        featureVec = numpy.array(temp, dtype=numpy.float64)

        featureVec = (featureVec - self._ts._avg[feature_index]) / self._ts._stdev[feature_index]

        return featureVec


    def makeSingleCellFeatureProjection(self, impdata, lt, pos, track,
                                         channel, region, clf, features=None,
                                         normalize_dynamic_range=False):

        all_features = self._ts.getFeatureNames()
        if features is None:
            features = all_features

        indices = filter(lambda i: all_features[i] in features, range(len(all_features)))
        frameVec = impdata[lt][pos][track]['Frame']
        Xpy = [[impdata[lt][pos][track][channel][region]['feature__' + x][i]
                for x in features] for i in range(len(frameVec))]
        X = numpy.array(Xpy, dtype=numpy.float64)

        # normalization (z=score)
        Xnorm = (X - self._ts._avg[indices]) / self._ts._stdev[indices]

        # calculate projections
        decvals = clf.decision_function(Xnorm)

        if len(decvals.shape) == 1:
            projections = decvals
        elif decvals.shape[1] == 1:
            projections = decvals[:,0]
        elif decvals.shape[1] == 2:
            projections = decvals[:,1] - decvals[:,0]
        else:
            raise ValueError('not implemented for multiple classes')

        if normalize_dynamic_range:
            if projections.max() > projections.min():
                projections = projections * 1.0 / (projections.max() - projections.min())

        return projections

    def getDiscriminantValues(self, impdata, lt, pos, track,
                              channel, region, clf, features=None,
                              normalize_dynamic_range=False,
                              discr_index=0):

        all_features = self._ts.getFeatureNames()
        if features is None:
            features = all_features

        indices = filter(lambda i: all_features[i] in features, range(len(all_features)))
        frameVec = impdata[lt][pos][track]['Frame']
        Xpy = [[impdata[lt][pos][track][channel][region]['feature__' + x][i]
                for x in features] for i in range(len(frameVec))]
        X = numpy.array(Xpy, dtype=numpy.float64)

        # normalization (z=score)
        Xnorm = (X - self._ts._avg[indices]) / self._ts._stdev[indices]

        # calculate projections
        decvals = clf.decision_function(Xnorm)

        if len(decvals.shape) == 1:
            projections = decvals
        elif decvals.shape[1] == 1:
            projections = decvals[:,0]
        else:
            projections = decvals[:,discr_index]

        if normalize_dynamic_range:
            if projections.max() > projections.min():
                projections = projections * 1.0 / (projections.max() - projections.min())

        return projections

    def classificationProbability(self, impdata, lt, pos, track,
                                  channel, region, clf, features=None):

        all_features = self._ts.getFeatureNames()
        if features is None:
            features = all_features

        indices = filter(lambda i: all_features[i] in features, range(len(all_features)))
        frameVec = impdata[lt][pos][track]['Frame']
        Xpy = [[impdata[lt][pos][track][channel][region]['feature__' + x][i]
                for x in features] for i in range(len(frameVec))]
        X = numpy.array(Xpy, dtype=numpy.float64)

        # normalization (z=score)
        Xnorm = (X - self._ts._avg[indices]) / self._ts._stdev[indices]

        # calculate projections
        prob = clf.predict_proba(Xnorm)

        # return value is the first column (depending on the method there can be
        # several values).
        return prob[:,0]


    def DEPRECATEDcalcProjections(self, impdata, plates=None, positions=None,
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

    def calcProjections(self, impdata,
                        plates=None, positions=None,
                        tracks=None, channels=None, regions=None):

        for method in self._classifiers.keys():
            if self._classifiers[method] is None:
                self._classifiers[method] = self.learnClassifier(method=method)

        if not self.settings.features_selection is None:
            for method in self._classifiers_fs.keys():
                if self._classifiers_fs[method] is None:
                    self._classifiers_fs[method] = self.learnClassifier(method=method,
                                                                        features = self.settings.features_selection)

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

                            for method, clf in self._classifiers.iteritems():
                                impdata[lt][pos][track][channel][region]['%s_decvalue' % method] = \
                                    self.makeSingleCellFeatureProjection(impdata, lt, pos,
                                                                         track, channel, region, clf)
                                impdata[lt][pos][track][channel][region]['%s_decvalue_norm' % method] = \
                                    self.makeSingleCellFeatureProjection(impdata, lt, pos,
                                                                         track, channel, region, clf,
                                                                         normalize_dynamic_range=True)
                                impdata[lt][pos][track][channel][region]['%s_prob' % method] = \
                                    self.classificationProbability(impdata, lt, pos,
                                                                   track, channel, region, clf)

                            for method, clf in self._classifiers_fs.iteritems():
                                # reduced classifiers
                                impdata[lt][pos][track][channel][region]['%s_decvalue_reduced' % method] = \
                                    self.makeSingleCellFeatureProjection(impdata, lt, pos,
                                                                         track, channel, region, clf,
                                                                         features = self.settings.features_selection)
                                impdata[lt][pos][track][channel][region]['%s_decvalue_reduced_norm' % method] = \
                                    self.makeSingleCellFeatureProjection(impdata, lt, pos,
                                                                         track, channel, region, clf,
                                                                         features = self.settings.features_selection,
                                                                         normalize_dynamic_range=True)

                                impdata[lt][pos][track][channel][region]['%s_prob_reduced' % method] = \
                                    self.classificationProbability(impdata, lt, pos,
                                                                   track, channel, region, clf,
                                                                   features = self.settings.features_selection)


        return

    def calcProjections2(self, impdata, projection_list,
                        plates=None, positions=None,
                        tracks=None, channels=None, regions=None):

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

                            for key, func, param in self.projection_list:
                                impdata[lt][pos][track][channel][region][key] = \
                                    func(impdata, lt, pos, track, channel, region,
                                         **param)

        return

    def normalizeFeatures(self, impdata, features,
                          plates=None, positions=None,
                          tracks=None, channels=None, regions=None):

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
                            for method, clf in self._classifiers.iteritems():
                                for feature in features:
                                    if feature.split('__')[0] == 'feature':
                                        new_feature = feature.replace('feature__', 'normalized__')
                                    else:
                                        new_feature = 'normalized__' + feature
                                    impdata[lt][pos][track][channel][region][new_feature] = \
                                        self.normalizeSingleCellFeature(impdata, lt, pos, track,
                                                                        channel, region, feature)

        return

#    def makeLDAPlots(self, impdata):
#        featureData = [('secondary', 'propagate', 'lda_projection')]
#        classificationData = [('primary', 'primary'), ('secondary', 'propagate')]
#        self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])
#        self.makeSingleCellPlots(impdata, featureData, classificationData)
#        return

