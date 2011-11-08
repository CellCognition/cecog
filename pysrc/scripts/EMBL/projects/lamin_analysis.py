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
        # get expression levels
        self.calcExpressionLevel(impdata)

        # reduce data set by QC
        self.applyQC(impdata, remove_qc_false=True, verbose=True)

        # calc the LDA projections
        self.calcProjections(impdata, channels=['secondary'], regions=['propagate'])

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

    (options, args) = parser.parse_args()

    if (options.settings_file is None):
        parser.error("incorrect number of arguments!")

    plot_generation = options.plot_generation
    if plot_generation is None:
        plot_generation = False

    la = LaminAnalysis(options.settings_file)

    # plot generation
    if plot_generation:
        la.batchPlotGeneration()

    # make HTML pages
    la.batchHTMLPageGeneration()



