from optparse import OptionParser
#import os, re, time, sys
#import shutil
#import string
#
#import numpy
#
#import scripts.EMBL.feature_projection.lda
#reload(scripts.EMBL.feature_projection.lda)
#from scripts.EMBL.feature_projection.lda import ScikitLDA, TrainingSet
#
#import scripts.EMBL.io.flatfileimporter
#reload(scripts.EMBL.io.flatfileimporter)
#
#import scripts.EMBL.plotter.feature_timeseries_plotter
#reload(scripts.EMBL.plotter.feature_timeseries_plotter)
#
#import pickle
#
#from scripts.EMBL.plotter.feature_timeseries_plotter import TimeseriesPlotter
#import scripts.EMBL.plotter.stats
#reload(scripts.EMBL.plotter.stats)
#
#from scripts.EMBL.settings import Settings
#
#from collections import *
#
#import scripts.EMBL.html_generation.event_page_generation
#from scripts.EMBL.html_generation.event_page_generation import *

from scripts.EMBL.projects.post_processing import *

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc
# if rpy2 is going to be used: export PATH=/Users/twalter/software/R/R.framework/Resources/bin:${PATH}

class ColorMap(object):
    def __init__(self):
        # divergent color maps
        self.div_basic_colors_intense = ["#E41A1C",
                                         "#377EB8",
                                         "#4DAF4A",
                                         "#984EA3",
                                         "#FF7F00" ]
        self.div_basic_colors_soft = ["#7FC97F",
                                      "#BEAED4",
                                      "#FDC086",
                                      "#FFFF99",
                                      "#386CB0" ]


    def getRGBValues(self, hexvec):
        single_channel = {}
        for c in range(3):
            single_channel[c] = [int(x[(1 + 2*c):(3+2*c)], base=16) / 256.0 for x in hexvec]
        rgbvals = zip(single_channel[0], single_channel[1], single_channel[2])
        return rgbvals

    def makeDivergentColorRamp(self, N, intense=True, hex_output=False):
        if intense:
            basic_colors = self.div_basic_colors_intense
        if not intense:
            basic_colors = self.div_basic_colors_soft

        cr = self.makeColorRamp(N, basic_colors, hex_output)
        return cr

    def makeColorRamp(self, N, basic_colors, hex_output=False):

        if N<1:
            return []
        if N==1:
            return [basic_colors[0]]

        xvals = numpy.linspace(0, len(basic_colors)-1, N)

        single_channel = {}
        for c in range(3):
            xp = range(len(basic_colors))
            yp = [int(x[(1 + 2*c):(3+2*c)], base=16) for x in basic_colors]

            single_channel[c] = [x / 256.0 for x in numpy.interp(xvals, xp, yp)]

        if hex_output:
#            colvec = ['#' + hex(numpy.int32(min(16**4 * single_channel[0][i], 16**6 - 1) +
#                                            min(16**2 * single_channel[1][i], 16**4 - 1) +
#                                            min(single_channel[2][i], 16**2 -1) )).upper()[2:]
#                      for i in range(N)]
            colvec = ['#' + hex(numpy.int32(
                                            (((256 * single_channel[0][i]  ) +
                                              single_channel[1][i]) * 256 +
                                              single_channel[2][i]) * 256
                                              ))[2:]
                      for i in range(N)]

        else:
            colvec = zip(single_channel[0], single_channel[1], single_channel[2])

        return colvec


class LaminAnalysis(PostProcessingWorkflow, FeatureProjectionAnalysis):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())
        PostProcessingWorkflow.__init__(self, settings=self.settings)
        FeatureProjectionAnalysis.__init__(self, settings=self.settings)
        #self.fpa = FeatureProjectionAnalysis(settings=settings)

        self._classifiers = {'lda': None}
        self._classifiers_fs = {}

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

    def calcExpressionLevel(self, impdata):
        self.calcTrackFeature(impdata, self._calc_expression_level)
        return

    def _process(self, impdata):

        for method in self._classifiers.keys():
            if self._classifiers[method] is None:
                self._classifiers[method] = self.learnClassifier(method=method)

        if not self.settings.features_selection is None:
            for method in self._classifiers_fs.keys():
                if self._classifiers_fs[method] is None:
                    self._classifiers_fs[method] = self.learnClassifier(method=method,
                                                                        features = self.settings.features_selection)

        # get expression levels
        self.calcExpressionLevel(impdata)

        # reduce data set by QC
        self.applyQC(impdata, remove_qc_false=True, verbose=True)

        # calc the LDA projections
        #self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])


        self.projection_list = []
        for i in range(3):
            self.projection_list.append(('lda_discriminant_value_%i' % i,
                                         self.getDiscriminantValues,
                                         {'clf': self._classifiers['lda'],
                                          'features': None,
                                          'normalize_dynamic_range': False,
                                          'discr_index': i
                                          }))
        self.calcProjections2(impdata,
                              projection_list=self.projection_list,
                              channels=['secondary'],
                              regions=['propagate'])

        return


    def makeDisassemblyTimepointBarplot(self, impdata, plates=None, wells=None):

        value_extraction = {'until_disassembled':
                            (ConditionalValueCounter('disassembling', 'disassembled'),
                             'secondary', 'propagate', 'class__name',
                             'secondary', 'propagate', 'class__name')}
        self.makeTrackFeatureBarplot(impdata, value_extraction, plates, wells)


        value_extraction = {'until_disassembled_or_assembled':
                            (ConditionalValueCounterList('disassembling', ['disassembled', 'assembled']),
                             'secondary', 'propagate', 'class__name',
                             'secondary', 'propagate', 'class__name')}
        self.makeTrackFeatureBarplot(impdata, value_extraction, plates, wells)

        return


if __name__ ==  "__main__":

    description =\
'''
%prog - generation of single cell html pages.
Prerequesites are gallery images (generated by scripts.cutter.cut_tracks_from_resultfile.py ) ,
a settings file for the whole workflow (like scripts/EMBL/settings_files/lamin/settings_lamin_analysis.py)
and the generated single cell plots. The scripts just links existing information together.
'''

    parser = OptionParser(usage="usage: %prog [options]",
                          description=description)

    parser.add_option("-s", "--settings_file", dest="settings_file",
                      help="Filename of the settings file for the postprocessing")
    parser.add_option("--plot_generation", action="store_true", dest="plot_generation",
                      help="Filename of the settings file for the postprocessing")
    parser.add_option("--panel_generation", action="store_true", dest="panel_generation",
                      help="Flag for panel generation (representation of "
                      "classification results to be used with gallery images.")
    parser.add_option("--plate", dest="plate",
                      help="Plate Identifier (default None; plates are then taken"
                      "from the settings files.")

    (options, args) = parser.parse_args()

    if (options.settings_file is None):
        parser.error("incorrect number of arguments!")

    plot_generation = options.plot_generation
    if plot_generation is None:
        plot_generation = False

    panel_generation = options.panel_generation
    if panel_generation is None:
        panel_generation = False

#    parser.add_option("--plot_generation", action="store_true", dest="plot_generation",
#                      help="Filename of the settings file for the postprocessing")
#
#    (options, args) = parser.parse_args()
#
#    if (options.settings_file is None):
#        parser.error("incorrect number of arguments!")
#
#    plot_generation = options.plot_generation
#    if plot_generation is None:
#        plot_generation = False

    la = LaminAnalysis(options.settings_file)

#    # plot generation
#    if plot_generation:
#        la.batchPlotGeneration()
#
#    # make HTML pages
#    la.batchHTMLPageGeneration()

    if not options.plate is None:
        la.settings.plates = [options.plate]

    # plot generation
    if plot_generation:
        la.batchPlotGeneration()

    # make HTML pages
    if panel_generation:
        la.batchPanelGeneration()

    # generation of html-pages
    la.batchHTMLPageGeneration()



