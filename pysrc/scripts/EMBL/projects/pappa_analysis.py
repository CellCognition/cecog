import re, time, os, sys, pickle

import shutil
import string
import numpy
import operator
import types

from optparse import OptionParser

from scripts.EMBL.settings import Settings

from collections import *
from scripts.EMBL.plotter import stats

from cecog import ccore

import copy

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc
# import scripts.EMBL.projects.pappa_analysis
# pap = scripts.EMBL.projects.pappa_analysis.PappaAnalysis("scripts/EMBL/settings_files/pappa/pappa_analysis_settings.py")
# pap()

class FileGetter(object):
    def __init__(self, suffix='tif', relpath=True):
        if suffix[0] == '.':
            self.suffix = suffix
        else:
            self.suffix = '.' + suffix
        self.relpath = relpath
        self.infolder = None

    def get_tiffs(self, all_tiffs, dirname, names):

        for filename in names:
            if os.path.splitext(filename)[-1] == self.suffix:
                if self.relpath:
                    all_tiffs.append((os.path.relpath(dirname, self.infolder),
                                      filename))
                else:
                    all_tiffs.append((dirname, filename))
        return

    def __call__(self, infolder):
        self.infolder = infolder
        all_tiffs = []
        os.path.walk(infolder, self.get_tiffs, all_tiffs)
        self.infolder = None
        return all_tiffs

class ImageNormalizer(object):
    def __call__(self, infolder, outfolder):
        fg = FileGetter('tif')
        all_tiffs = fg(infolder)
        for reldirname, filename in all_tiffs:
            imin = ccore.readImageMito(os.path.join(infolder, reldirname, filename))
            if not os.path.exists(os.path.join(outfolder, reldirname)):
                os.makedirs(os.path.join(outfolder, reldirname))
            ccore.writeImage(imin,
                             os.path.join(outfolder, reldirname, filename))

class TableReader(object):

    # transforms a string to int, float or string (attempts in that order)
    def getValue(self, stringval):
        try:
            value = int(stringval)
        except:
            try:
                value = float(stringval)
            except:
                value = stringval
        return value

    def __call__(self, filename, header=True):
        table = {}
        fp = open(filename, 'r')
        in_read = fp.readlines()
        fp.close()

        if header == True:
            try:
                title_line = [x.strip() for x in in_read[0].split('\t')]
                start_index = 1
            except:
                raise ValueError('ERROR: could not read title line from'
                                 '%s' % filename)
        else:
            try:
                title_line = ['C%02i' % x for x in range(len(in_read[0].split('\t')))]
                start_index = 0
            except:
                raise ValueError('ERROR: could not first line from'
                                 '%s' % filename)

        table = {}
        for entry in title_line:
            table[entry] = []

        for line in in_read[start_index:]:
            line_values = [self.getValue(x.strip()) for x in line.split('\t')]
            #print len(line_values), '\t', line_values
            if len(line_values) != len(title_line):
                continue
            for entry, val in zip(title_line, line_values):
                table[entry].append(val)

        return table

class PappaAnalysis(object):

    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())

        print 'PAPPA analysis'
        self.dctFolder = self.getFolderDict()
        self.tr = TableReader()
        if not os.path.isdir(self.settings.plotDir):
            os.makedirs(self.settings.plotDir)
        for pheno_entry in self.settings.colors.keys():
            new_key = '%s_%s' % ('phpos', pheno_entry)
            self.settings.colors[new_key] = self.settings.colors[pheno_entry]

        self.manual_entries = ['Prophase (manual)',
                               'Prometaphase (manual)',
                               'Metaphase (manual)',
                               'Anaphase (manual)',
                               'Mitotic (manual)',
                               'EarlyMitosis (manual)',
                               ]

        self.auto_features_sec = [
                                  # secondary channel
                                  'nb_sec_EarlyMitosis',
                                  'nb_sec_Metaphase',
                                  'nb_sec_Anaphase',
                                  'nb_sec_MitosisSegError',
                                  'nb_sec_NoMitosis',
                                  'secondary_mito',
                                  ]

        self.auto_features_prim = [
                                   # primary channel
                                   'nb_EarlyMitosis',
                                   'nb_Metaphase',
                                   'nb_Anaphase',
                                   'nb_Interphase',
                                   'nb_Apoptosis',
                                   'nb_Polylobed',
                                   'nb_JoinArt',
                                   'nb_SegArt',
                                   ]


    def getFolderDict(self):
        # /Users/twalter/data/PAPPA/output/ASlide1_20msoffset_001/log/_finished/A01_01__finished.txt
        dctFolder = {}
        for plate in self.settings.lstPlates:
            finished_folder = os.path.join(self.settings.output_folder, plate, 'log', '_finished')
            positions = [y.split('__')[0] for y in
                         filter(lambda x: x.split('.')[-1] == 'txt',
                                os.listdir(finished_folder))]
            dctFolder[plate] = positions
        return dctFolder

    def importObjectDetails(self, plate, pos):
        #/Users/twalter/data/PAPPA/output/ASlide1_20msoffset_001/analyzed/statistics/PA01_01__object_details.txt
        filename = os.path.join(self.settings.output_folder,
                                plate, 'analyzed', 'statistics',
                                'P%s__object_details.txt' % pos)
        full_info = self.tr(filename)
        res = {}
        for i in range(len(full_info['objID'])):
            try:
                obj_id = full_info['objID'][i]
                res[obj_id] = {'coord': (full_info['PRIMARY_primary_centerX'][i],
                                         full_info['PRIMARY_primary_centerY'][i]),
                               'phenoClass': full_info['PRIMARY_primary_className'][i],
                               'meandiff': full_info['SECONDARY_expanded_mean'][i] - full_info['SECONDARY_outside_mean'][i],
                               'phistClass': full_info['SECONDARY_expanded_className'][i],
                               }
            except:
                print 'ERROR: ', plate, pos
                print 'i = ', i
                print 'objID: ', full_info['objID'][i]
                print 'class name: ', full_info['PRIMARY_primary_className'][i]

        return res

    def importAllData(self):
        res = {}
        for lt in self.dctFolder.keys():
            res[lt] = {}
            for pos in self.dctFolder[lt]:
                res[lt][pos] = self.importObjectDetails(lt, pos)
        return res


    def readManualAnnotation(self):
        filename = self.settings.annotation_filename
        fp = open(filename, 'r')
        content_unproc = fp.readlines()
        fp.close()

        title_line = [x.strip() for x in content_unproc[0].split('\t')]
        entry_keys = [
                      'Mitotic (manual)',
                      'Prophase (manual)',
                      'Prometaphase (manual)',
                      'Metaphase (manual)',
                      'Anaphase (manual)',
                      ]

        #print title_line
        manual_annotation = {}
        for line in content_unproc[1:]:
            entries = dict(zip(title_line, [x.strip() for x in line.split('\t')]))

            if entries['Mitotic (manual)'] == '':
                continue

            #print entries
            plate = entries['plate']
            well = entries['well']
            if not plate in manual_annotation:
                manual_annotation[plate] = {}
            manual_annotation[plate][well] = dict(zip(entry_keys,
                                                      [int(entries[x]) if not entries[x] == '' else 0
                                                       for x in entry_keys]))
            manual_annotation[plate][well]['EarlyMitosis (manual)'] = \
                manual_annotation[plate][well]['Prometaphase (manual)'] + manual_annotation[plate][well]['Prophase (manual)']

        return manual_annotation


    def calcMitoticIndex(self, imp_data):

        res = {}
        for lt in imp_data.keys():
            res[lt] = {}
            for pos in imp_data[lt].keys():

                res[lt][pos] = {}

                # old: total number of cells is just the number of detected objects
                #total_nb_cells = len(imp_data[lt][pos])
                # now, we exclude all cells that correspond to segmentation artefacts
                # and debris.
                #all_obj = sorted(imp_data[lt][pos].keys())
                all_obj = filter(lambda x:
                                 not imp_data[lt][pos][x]['phenoClass'] in
                                 ['SegArt'],
                                 sorted(imp_data[lt][pos].keys()))
                all_valid_obj = filter(lambda x:
                                       not imp_data[lt][pos][x]['phenoClass'] in
                                       ['SegArt', 'Debris', 'Apoptosis'],
                                       all_obj)

                # number of total cells is stored
                res[lt][pos]['total_valid'] = len(all_valid_obj)
                res[lt][pos]['total'] = len(all_obj)

                # we count all classes (for all indices)
                # 1.) in the primary channel
                all_pheno_classes = [imp_data[lt][pos][x]['phenoClass']
                                     for x in all_obj]
                #nb_valid_obj = float(len(all_valid_obj))
                #nb_obj = float(len(all_obj))
                for phenoClass in self.settings.pheno_classes:
                    res[lt][pos]['nb_%s' % phenoClass] = all_pheno_classes.count(phenoClass)
#                    if nb_obj > 0:
#                        res[lt][pos]['index_%s' % phenoClass] = res[lt][pos]['nb_sec_%s' % phenoClass] / nb_obj
#                    else:
#                        res[lt][pos]['index_%s' % phenoClass] = 0.0

                # 2.) Secondary Channel
                sec_pheno_classes = [imp_data[lt][pos][x]['phistClass']
                                     for x in all_obj]
                for phenoClass in self.settings.sec_pheno_classes:
                    res[lt][pos]['nb_sec_%s' % phenoClass] = sec_pheno_classes.count(phenoClass)
#                    if nb_obj > 0:
#                        res[lt][pos]['index_%s' % phenoClass] = res[lt][pos]['nb_sec_%s' % phenoClass] / nb_obj
#                    else:
#                        res[lt][pos]['index_%s' % phenoClass] = 0.0


                # 3.) for both channels, we sum the relevant classes (defined in the settings file)
                for ch, key_prefix in zip(self.settings.sumClasses, ['nb_', 'nb_sec_']):
                    for sum_class in self.settings.sumClasses[ch]:
                        new_key = '%s_%s' % (ch, sum_class)
                        res[lt][pos][new_key] = sum([res[lt][pos]['%s%s' % (key_prefix, x)]
                                                     for x in self.settings.sumClasses[ch][sum_class]])

        return res

    def _DEPRECATED_calcMitoticIndex(self, imp_data):
        sumClasses = {
                      'mito_classification' : ['pro', 'prometa', 'map', 'meta', 'earlyana', 'lateana'],
                      'early_mito_classification' : ['pro', 'prometa', 'map', 'meta']
                      }
        res = {}
        for lt in imp_data.keys():
            res[lt] = {}
            for pos in imp_data[lt].keys():
                lstTracks = sorted(imp_data[lt][pos].keys())
                res[lt][pos] = {}
                total_nb_cells = len(imp_data[lt][pos])
                res[lt][pos]['total'] = total_nb_cells

                phos_histone_positive_tracks = filter(lambda x:
                                                      imp_data[lt][pos][x]['meandiff'] > self.settings.mito_thresh,
                                                      lstTracks)
                res[lt][pos]['nb_mito_phospho_histo'] = len(phos_histone_positive_tracks)
                #res[lt][pos]['ratio_mito_phospho_histo'] = res[lt][pos]['nb_mito_phospho_histo'] / total_nb_cells

                all_pheno_classes = [imp_data[lt][pos][x]['phenoClass']
                                     for x in lstTracks]
                for phenoClass in self.settings.pheno_classes:
                    res[lt][pos]['nb_%s' % phenoClass] = all_pheno_classes.count(phenoClass)

                ph_positive_pheno_classes = [imp_data[lt][pos][x]['phenoClass']
                                             for x in phos_histone_positive_tracks]
                for phenoClass in self.settings.phpos_pheno_classes:
                    res[lt][pos]['nb_phpos_%s' % phenoClass] = ph_positive_pheno_classes.count(phenoClass)
                    #res[lt][pos]['ratio_%s' % phenoClass] = float(res[lt][pos]['nb_%s' % phenoClass]) / total_nb_cells

                res[lt][pos]['nb_mito_classification'] = sum([res[lt][pos]['nb_%s' % phenoClass]
                                                              for phenoClass in sumClasses['mito_classification']])
                res[lt][pos]['nb_early_mito_classification'] = sum([res[lt][pos]['nb_%s' % phenoClass]
                                                                    for phenoClass in sumClasses['early_mito_classification']])
                res[lt][pos]['nb_phpos_mito_classification'] = sum([res[lt][pos]['nb_phpos_%s' % phenoClass]
                                                                    for phenoClass in sumClasses['mito_classification']])
                res[lt][pos]['nb_phpos_early_mito_classification'] = sum([res[lt][pos]['nb_phpos_%s' % phenoClass]
                                                                          for phenoClass in sumClasses['early_mito_classification']])

        return res

    def OLD_groupData(self, res):
        grouped_data = {}

        for lt in res.keys():
            lstPositions = sorted(res[lt].keys())
            entries = res[lt][lstPositions[0]].keys()
            grouped_data[lt] = {}
            for entry in entries:
                grouped_data[lt][entry] = 0
            for pos in lstPositions:
                for entry in entries:
                    #print lt, pos, entry, res[lt][pos][entry]
                    grouped_data[lt][entry] += res[lt][pos][entry]

        return grouped_data

    def specificPostProcessing(self, res):
        # join several plates
        join_plates = {
                       'ASlide1_20msoffset_001': ['ASlide1_20msoffset_001', 'BSlide1_20msoffset_002'],
                       'ASlide2_20msoffset_001': ['ASlide2_20msoffset_001', 'BSlide2_20msoffset_002'],
                       'ASlide3_20msoffset_001': ['ASlide3_20msoffset_001', 'BSlide3_20msoffset_002'],
                       'CSlide1_20msoffset_003': ['CSlide1_20msoffset_003', 'DSlide1_20msoffset_004'],
                       'CSlide2_20msoffset_003': ['CSlide2_20msoffset_003', 'DSlide2_20msoffset_004'],
                       'CSlide3_20msoffset_003': ['CSlide3_20msoffset_003', 'DSlide3_20msoffset_004'],
                       }
        new_res = {}
        for plate in join_plates.keys():
            if not plate in res:
                continue
            new_res[plate] = {}
            for pl in join_plates[plate]:
                lstPositions = res[pl].keys()
                entries = res[pl][lstPositions[0]].keys()

                for pos in lstPositions:
                    if not pos in new_res[plate]:
                        new_res[plate][pos] = copy.deepcopy(res[pl][pos])
                    else:
                        for entry in entries:
                            new_res[plate][pos][entry] += res[pl][pos][entry]
                del(res[pl])
        res.update(new_res)

        return

    def groupData(self, res):
        grouped_data = {}

        for lt in res.keys():
            lstPositions = sorted(res[lt].keys())
            entries = res[lt][lstPositions[0]].keys()
            grouped_data[lt] = {}
            lstWells = list(set([x.split('_')[0] for x in lstPositions]))
            for well in lstWells:
                grouped_data[lt][well] = {}
                for entry in entries:
                    grouped_data[lt][well][entry] = 0
                wellPositions = filter(lambda x: x.split('_')[0] == well, lstPositions)
                for pos in wellPositions:
                    for entry in entries:
                        #print lt, pos, entry, res[lt][pos][entry]
                        grouped_data[lt][well][entry] += res[lt][pos][entry]

        return grouped_data

    def OLD_makeBarplots(self, grouped_data):
        bp = stats.Barplot()
        plot_entries = ['nb_mito_phospho_histo',
                        'nb_mito_classification',
                        'nb_early_mito_classification',
                        'nb_pro', 'nb_prometa',
                        'nb_map', 'nb_meta',
                        'nb_earlyana', 'nb_lateana', 'nb_telo',
                        ]
        bar_names = dict(zip(plot_entries, ['Mito Count (PH)',
                                            'Mito Count (Class)',
                                            'Early Mito Count (Class)',
                                            'Pro (class)',
                                            'Prometa (class)',
                                            'MAP (class)',
                                            'Meta (class)',
                                            'Early Ana (class)',
                                            'Late Ana (class)',
                                            'Telo (class)']))

        bar_titles = [bar_names[x] for x in plot_entries]

        for lt in grouped_data.keys():
            datavec = [grouped_data[lt][x] for x in plot_entries]
            colvec = [self.settings.colors[x[3:]] for x in plot_entries]

            filename = os.path.join(self.settings.plotDir, 'Counts--%s.png' % lt)
            bp.singleBarplot(datavec, filename, color=colvec,
                             title = 'Cell counts for %s (total: %i)' % (lt, grouped_data[lt]['total']),
                             xlab='', ylab = 'Cell counts',
                             bartitles=bar_titles, bottom=0.3)

            filename = os.path.join(self.settings.plotDir, 'Relative_counts--%s.png' % lt)
            relvec = [float(x) / float(grouped_data[lt]['total']) for x in datavec]
            bp.singleBarplot(relvec, filename, color=colvec,
                             title = 'Relative cell counts for %s (total: %i)' % (lt, grouped_data[lt]['total']),
                             xlab='', ylab = 'Cell counts',
                             bartitles=bar_titles, bottom=0.3)

        output_entries = plot_entries + ['nb_apo', 'total']
        print '\t'.join(['plate'] + output_entries)
        for lt in grouped_data.keys():
            print '\t'.join([lt] + [str(grouped_data[lt][x]) for x in output_entries])

        return

    def compareManualVsAutomatic(self, res=None, manual=None):

        if res is None:
            imp_data = self.importAllData()
            res = self.calcMitoticIndex(imp_data)

        if manual is None:
            manual = self.readManualAnnotation()

#pheno_classes = class_code.values()
#mitotic_classes = ['EarlyMitosis', 'Metaphase', 'Anaphase']

#sec_pheno_classes = sec_class_code.values()
#sec_mitotic_classes = ['EarlyMitosis', 'Metaphase', 'Anaphase', 'MitosisSegError']

        for feature_auto, feature_manual, title, xlabel, ylabel in \
                [
                 ('nb_sec_EarlyMitosis', ['Prophase (manual)', 'Prometaphase (manual)'],
                  '--early_mitosis', 'Early Mitosis (Automatic)', 'Pro + Prometa (Manual)'),
                 ('nb_sec_Metaphase', 'Metaphase (manual)',
                  '--PH_metaphase', 'Metaphase (Automatic)', 'Metaphase (Manual)'),
                 (['nb_sec_EarlyMitosis', 'nb_sec_Metaphase', 'nb_sec_Anaphase', 'nb_sec_MitosisSegError'],
                  'Mitotic (manual)',
                  '--PH_full_mitosis', 'Early + Meta + Ana + MitoSegError (Auto)', 'Mitotic (Manual)'),
                 (['nb_sec_EarlyMitosis', 'nb_sec_Metaphase', 'nb_sec_MitosisSegError'],
                  ['Prophase (manual)', 'Prometaphase (manual)', 'Metaphase (manual)'],
                  '--PH_mitosis_minus_anaphase_with_error', 'Early + Meta + MitoSegError (Auto)', 'Pro + Prometa + Meta (Manual)'),
                 (['nb_sec_EarlyMitosis', 'nb_sec_Metaphase'],
                  ['Prophase (manual)', 'Prometaphase (manual)', 'Metaphase (manual)'],
                  '--PH_mitosis_minus_anaphase_without_error', 'Early + Meta (Auto)', 'Pro + Prometa + Meta (Manual)'),
                 ]:
            #print
            #print feature_auto
            #print feature_manual
            #print title
            self.plotScatterManualVsAutomatic(res, manual,
                                              feature_auto, feature_manual,
                                              filename_addon=title,
                                              xlabel=xlabel,
                                              ylabel=ylabel)

        return

    def plotScatterManualVsAutomatic(self, res, manual, feature_auto, feature_manual,
                                     filename_addon='', xlabel=None, ylabel=None):
        # plot class
        sp = stats.Scatterplot()

        # plot output
        scatterplot_dir = os.path.join(self.settings.plotDir , 'scatter')
        if not os.path.exists(scatterplot_dir):
            os.makedirs(scatterplot_dir)
        filename = os.path.join(scatterplot_dir,
                                'scatter%s.png' % filename_addon)

        # extract data
        xvec = []
        yvec = []

        for plate in manual.keys():
            if not plate in res:
                print 'PLATE WARNING: not entry in automatic results for %s ... SKIPPING' % plate
                continue

            for pos in manual[plate].keys():

                if not pos in res[plate]:
                    print 'POSITION WARNING: not entry in automatic results for %s %s ... SKIPPING' % (plate, pos)
                    continue

                try:
                    if type(feature_manual) == types.ListType:
                        xvec.append(sum([manual[plate][pos][x] for x in feature_manual]))
                    else:
                        xvec.append(manual[plate][pos][feature_manual])

                    if type(feature_auto) == types.ListType:
                        yvec.append(sum([res[plate][pos][x] for x in feature_auto]))
                    else:
                        yvec.append(res[plate][pos][feature_auto])

                except:
                    print plate
                    print pos
                    print manual[plate][pos]
                    print res[plate][pos]
                    raise ValueError("Generation of vectors during scatter plot"
                                     "for the experiment: %s %s"
                                     "manual: %s"
                                     "automatic: %s"
                                     % (plate, pos, str(manual[plate][pos]), str(res[plate][pos])))

        # plot call
        if xlabel is None:
            xlabel = "Manual: %s" % str(feature_manual)
        if ylabel is None:
            ylabel="Automatic: %s" % str(feature_auto)
        sp.single(xvec, yvec, filename=filename,
                  xlabel=xlabel,
                  ylabel=ylabel,
                  title=filename_addon[2:])

        return

    def plotScatter(self, res, feature1, feature2,
                    filename_addon='',
                    xlabel=None, ylabel=None,
                    exp_ids=None):
        # plot class
        sp = stats.Scatterplot()

        # plot output
        scatterplot_dir = os.path.join(self.settings.plotDir , 'scatter')
        if not os.path.exists(scatterplot_dir):
            os.makedirs(scatterplot_dir)
        filename = os.path.join(scatterplot_dir,
                                'scatter%s.png' % filename_addon)

        # extract data
        xvec = []
        yvec = []

        if exp_ids is None:
            exp_ids = []
            for plate in res.keys():
                for pos in res[plate].keys():
                    exp_ids.append((plate, pos))

        for plate, pos in exp_ids:

            if True:
                if type(feature1) == types.ListType:
                    xvec.append(sum([res[plate][pos][x] for x in feature1]))
                else:
                    xvec.append(res[plate][pos][feature1])

                if type(feature2) == types.ListType:
                    yvec.append(sum([res[plate][pos][x] for x in feature2]))
                else:
                    yvec.append(res[plate][pos][feature2])

            else:
                print plate
                print pos
                print res[plate][pos]
                raise ValueError("Generation of vectors during scatter plot"
                                 "for the experiment: %s %s"
                                 "automatic: %s"
                                 % (plate, pos, str(res[plate][pos])))

        # plot call
        if xlabel is None:
            xlabel = str(feature1)
        if ylabel is None:
            ylabel= str(feature2)
        sp.single(xvec, yvec, filename=filename,
                  xlabel=xlabel,
                  ylabel=ylabel,
                  title=filename_addon[2:])

        return

    def getReversePlateDescription(self):
        plateDescription = self.getPlateDescription()
        revPlateDescription = {}
        for plate, well in plateDescription.keys():
            condition = plateDescription[(plate, well)]
            if not condition in revPlateDescription:
                revPlateDescription[condition] = []
            revPlateDescription[condition].append((plate, well))

        return revPlateDescription

    def getExperimentSeries(self):
        plateDescription = self.getPlateDescription()
        all_exp = plateDescription.keys()

        exp_series = {
                      'EMBL': filter(lambda x: x[0].rfind('Slide') >= 0, all_exp),
                      'Exp6': filter(lambda x: x[0] == 'plate1', all_exp),
                      'Exp10': filter(lambda x: x[0] == 'Exp10', all_exp),
                      'Exp11': filter(lambda x: x[0] == 'Exp11', all_exp),
                      'Exp12': filter(lambda x: x[0] == 'Exp12', all_exp),
                      }

        for key in exp_series.keys():
            if len(exp_series[key]) == 0:
                del exp_series[key]
                print 'deleted exp_series[%s]' % key

        return exp_series

    def calcFeatures(self, raw_data):
        manual_entries = ['Prophase (manual)',
                          'Prometaphase (manual)',
                          'Metaphase (manual)',
                          'Anaphase (manual)',
                          'Mitotic (manual)',
                          'EarlyMitosis (manual)',
                          ]

        auto_features_sec = [
                            # secondary channel
                            'nb_sec_EarlyMitosis',
                            'nb_sec_Metaphase',
                            'nb_sec_Anaphase',
                            'nb_sec_MitosisSegError',
                            'nb_sec_NoMitosis',
                            'secondary_mito',
                            ]

        auto_features_prim = [
                              # primary channel
                              'nb_EarlyMitosis',
                              'nb_Metaphase',
                              'nb_Anaphase',
                              'nb_Interphase',
                              'nb_Apoptosis',
                              'nb_Polylobed',
                              'nb_JoinArt',
                              'nb_SegArt',
                              ]


        proc_data = copy.deepcopy(raw_data)
        for lt in raw_data.keys():
            lstPositions = sorted(raw_data[lt].keys())
            for pos in lstPositions:

                # number of cells in manual annotation class divided
                # by the number of all livin cells
                # (i.e. all cells except for segmentation error and apoptosis)
                for feature in manual_entries:
                    if not feature in raw_data[lt][pos]:
                        continue
                    proc_data[lt][pos]['valid_rel_%s' % feature] = float(raw_data[lt][pos][feature]) / raw_data[lt][pos]['total_valid']
                    proc_data[lt][pos]['total_rel_%s' % feature] = float(raw_data[lt][pos][feature]) / raw_data[lt][pos]['total']
                    proc_data[lt][pos]['normmito_%s' % feature] = float(raw_data[lt][pos][feature]) / max(raw_data[lt][pos]['Mitotic (manual)'], 1.0)

                # number of cells in secondary channel class divided by
                # the number of all living cells
                # (i.e. all cells except for segmentation error and apoptosis)
                for feature in auto_features_sec:
                    if not feature in raw_data[lt][pos]:
                        continue
                    proc_data[lt][pos]['valid_rel_%s' % feature] = float(raw_data[lt][pos][feature]) / raw_data[lt][pos]['total_valid']
                    proc_data[lt][pos]['total_rel_%s' % feature] = float(raw_data[lt][pos][feature]) / raw_data[lt][pos]['total']
                    proc_data[lt][pos]['normmito_%s' % feature] = float(raw_data[lt][pos][feature]) / max(raw_data[lt][pos]['secondary_mito'], 1.0)

                # number of cells in secondary channel class divided by
                # the number of all cells (except for segmentation error)
                for feature in auto_features_prim:
                    if not feature in raw_data[lt][pos]:
                        continue
                    proc_data[lt][pos]['total_rel_%s' % feature] = float(raw_data[lt][pos][feature]) / raw_data[lt][pos]['total']


        return proc_data

    def makeBarplots(self, specific_data,
                     conditions=None, features=None,
                     filename_prefix = 'Summary',
                     plotDir=None,
                     feature_group=None):

        if plotDir is None:
            plotDir = self.settings.plotDir

        if conditions is None:
            conditions = [
                          'untreated',
                          'control',
                          'siRNA 42 knock down',
                          'siRNA 42 rescue',
                          'siRNA 28 knock down',
                          'siRNA 28 rescue',
                          ]
        if features is None:
            features = [
                        'valid_rel_secondary_mito',
                        'valid_rel_nb_sec_EarlyMitosis',
                        'normmito_nb_sec_EarlyMitosis',
                        'valid_rel_Mitotic (manual)',
                        'normmito_Prometaphase (manual)'

                        # and including apoptosis in the reference set.
                        'total_rel_nb_Apoptosis',
                        'total_rel_secondary_mito',
                        'total_rel_nb_sec_EarlyMitosis',
                        'total_rel_Mitotic (manual)',
                        ]

        if feature_group is None:
            feature_group = [
                            'total_rel_secondary_mito',
                            'total_rel_nb_sec_EarlyMitosis',
                            'total_rel_nb_Apoptosis',
                             ]

        grouped_data = self.calcFeatures(specific_data)

        plateDescription = self.getPlateDescription()
        revPlateDescription = self.getReversePlateDescription()
        exp_series = self.getExperimentSeries()
        available_exp = []
        for pl in grouped_data.keys():
            for pos in grouped_data[pl].keys():
                available_exp.append((pl, pos))

        bp = stats.Barplot()

        feature_names = self.getColumnTitles()

        for series_key, exp_list in exp_series.iteritems():
            ordered_sets = [filter(lambda x: x in exp_list and x in available_exp,
                                   revPlateDescription[cond])
                            for cond in conditions]
            ordered_exp = [x[0] for x in ordered_sets]
            colorvec = [self.settings.condition_colors[x] for x in conditions]

            for feature in features:
                if True:
                    print feature
                    datavec = [grouped_data[plate][pos][feature] for plate, pos in ordered_exp]
                else:
                    print '%s not in grouped_data %s %s ... SKIPPING' % (feature, plate, pos)
                    continue
                filename = os.path.join(plotDir, '%s--%s--%s.png' % (filename_prefix, feature, series_key))

                bp.singleBarplot(datavec, filename,
                                 color=colorvec,
                                 title = 'Summary results for %s %s' % (series_key, feature_names[feature]),
                                 xlab='', ylab = feature_names[feature],
                                 bartitles=conditions, bottom=0.3)


            # make group plot
            datavec = []
            for plate, pos in ordered_exp:
                try:
                    datavec.append([grouped_data[plate][pos][feature]  for feature in feature_group])
                except:
                    print 'PROBLEM: ', plate, pos, feature
                    raise ValueError('PFFFFF')

            datamat = numpy.matrix(datavec)
            colorvec = [self.settings.colors[feature.split('_')[-1]] for feature in feature_group]

            filename = os.path.join(plotDir, 'PhenoProfile--%s.png' % series_key)
            bp.multiBarplot(datamat, filename, colorvec=colorvec,
                            bartitles=conditions,
                            title='Phenotypic profiling: %s' % series_key,
                            dataset_names=[feature_names[x] for x in feature_group],
                            ylim=(0, 0.18), loc=2,
                            bottom=0.3)

        return

    def _DEPRECATED_makeBarplots(self, grouped_data):

        bp = stats.Barplot()

        # TO COMPARE PHOSPHO HISTONE AND DAPI RESULTS
        plot_entries = [
                        'nb_mito_phospho_histo',
                        'nb_mito_classification',
                        'nb_phpos_mito_classification',
                        'nb_early_mito_classification',
                        'nb_phpos_early_mito_classification',
                        'nb_pro',
                        'nb_phpos_pro',
                        'nb_prometa',
                        'nb_phpos_prometa',
                        'nb_map',
                        'nb_phpos_map',
                        'nb_meta',
                        'nb_phpos_meta',
                        'nb_earlyana',
                        'nb_phpos_earlyana',
                        'nb_lateana',
                        'nb_phpos_lateana',
                        'nb_telo',
                        'nb_apo'
                        ]

        bar_names = dict(zip(plot_entries, [
                                            'Mito Count (PhosHist)',
                                            'Mito Count (DAPI)',
                                            'Mito Count (DAPI+PhosHist)',
                                            'Early Mito Count (DAPI)',
                                            'Early Mito Count (DAPI+PhosHist)',
                                            'Pro (DAPI)',
                                            'Pro (DAPI+PhosHist)',
                                            'Prometa (DAPI)',
                                            'Prometa (DAPI+PhosHist)',
                                            'MAP (DAPI)',
                                            'MAP (DAPI+PhosHist)',
                                            'Meta (DAPI)',
                                            'Meta (DAPI+PhosHist)',
                                            'Early Ana (DAPI)',
                                            'Early Ana (DAPI+PhosHist)',
                                            'Late Ana (DAPI)',
                                            'Late Ana (DAPI+PhosHist)',
                                            'Telophase (DAPI)',
                                            'Apoptosis (DAPI)',
                                            ]))

        comp_plot_entries = ['nb_mito_phospho_histo',
                             'nb_phpos_mito_classification',
                             'nb_apo']

# ORIGINAL:
#        plot_entries = ['nb_mito_phospho_histo',
#                        'nb_phpos_mito_classification',
#                        'nb_phpos_early_mito_classification',
#                        'nb_phpos_pro', 'nb_phpos_prometa',
#                        'nb_phpos_map', 'nb_phpos_meta',
#                        'nb_phpos_earlyana', 'nb_phpos_lateana',
#                        #'nb_apo'
#                        ]
#        comp_plot_entries = ['nb_mito_phospho_histo',
#                             'nb_phpos_mito_classification',
#                             'nb_apo']

#        bar_names = dict(zip(plot_entries, ['Mito Count (PosHist)',
#                                            'Mito Count (DAPI+PosHist)',
#                                            'Early Mito Count (DAPI+PosHist)',
#                                            'Pro (DAPI+PosHist)',
#                                            'Prometa (DAPI+PosHist)',
#                                            'MAP (DAPI+PosHist)',
#                                            'Meta (DAPI+PosHist)',
#                                            'Early Ana (DAPI+PosHist)',
#                                            'Late Ana (clDAPI+PosHistass)',
#                                            #'Apoptosis (class)',
#                                            ]))
        bar_titles = [bar_names[x] for x in plot_entries]

        for lt in grouped_data.keys():
            for pos in grouped_data[lt].keys():
                datavec = [grouped_data[lt][pos][x] for x in plot_entries]
                colvec = [self.settings.colors[x[3:]] for x in plot_entries]

                filename = os.path.join(self.settings.plotDir, 'Counts--%s--%s.png' % (lt, pos))
                bp.singleBarplot(datavec, filename, color=colvec,
                                 title = 'Cell counts for %s %s (total: %i)' % (lt, pos,
                                                                                grouped_data[lt][pos]['total']),
                                 xlab='', ylab = 'Cell counts',
                                 bartitles=bar_titles, bottom=0.45)

                filename = os.path.join(self.settings.plotDir, 'Relative_counts--%s--%s.png' % (lt, pos))
                relvec = [float(x) / float(grouped_data[lt][pos]['total']) for x in datavec]
                bp.singleBarplot(relvec, filename, color=colvec,
                                 title = 'Relative cell counts for %s %s (total: %i)' % (lt, pos,
                                                                                         grouped_data[lt][pos]['total']),
                                 xlab='', ylab = 'Cell counts',
                                 bartitles=bar_titles, bottom=0.45)

        all_pos = []
        for lt in sorted(grouped_data.keys()):
            for pos in sorted(grouped_data[lt].keys()):
                all_pos.append((lt, pos))

        print all_pos
        barnames = ['%s--%s' % (lt, pos) for lt, pos in all_pos]
        for entry in comp_plot_entries:
            datavec = [grouped_data[lt][pos][entry]/float(grouped_data[lt][pos]['total'])
                       for lt, pos in all_pos]
            color = self.settings.colors[entry[3:]]

            filename = os.path.join(self.settings.plotDir, 'AllPositions--%s.png' % entry)

            bp.singleBarplot(datavec, filename, color=color,
                             title = 'Relative cell counts for %s' % entry,
                             xlab='', ylab = 'Relative cell counts',
                             bartitles=barnames, bottom=0.4)


        #output_entries = plot_entries + ['nb_apo', 'total']
        #print '\t'.join(['plate'] + output_entries)
        #for lt in grouped_data.keys():
        #    print '\t'.join([lt] + [str(grouped_data[lt][pos][x]) for x in output_entries])

        return

    def getPlateDescription(self, all_exp=False):

        plateDescription = {
                            ('ASlide1_20msoffset_001', 'A01'): 'untreated',
                            ('ASlide2_20msoffset_001', 'A01'): 'siRNA 42 knock down',
                            ('ASlide3_20msoffset_001', 'A01'): 'siRNA 42 rescue',
                            ('BSlide1_20msoffset_002', 'A01'): 'untreated',
                            ('BSlide2_20msoffset_002', 'A01'): 'siRNA 42 knock down',
                            ('BSlide3_20msoffset_002', 'A01'): 'siRNA 42 rescue',
                            ('CSlide1_20msoffset_003', 'A01'): 'control',
                            ('CSlide2_20msoffset_003', 'A01'): 'siRNA 28 knock down',
                            ('CSlide3_20msoffset_003', 'A01'): 'siRNA 28 rescue',
                            ('DSlide1_20msoffset_004', 'A01'): 'control',
                            ('DSlide2_20msoffset_004', 'A01'): 'siRNA 28 knock down',
                            ('DSlide3_20msoffset_004', 'A01'): 'siRNA 28 rescue',

                            ('plate1', 'A01'): 'untreated',
                            ('plate1', 'B01'): 'control',
                            ('plate1', 'C01'): 'siRNA 42 knock down',
                            ('plate1', 'D01'): 'siRNA 28 knock down',
                            ('plate1', 'E01'): 'siRNA 42 rescue',
                            ('plate1', 'F01'): 'siRNA 28 rescue',

                            ('Exp10', 'A01'): 'untreated',
                            ('Exp10', 'B01'): 'control',
                            ('Exp10', 'C01'): 'siRNA 42 knock down',
                            ('Exp10', 'D01'): 'siRNA 28 knock down',
                            ('Exp10', 'E01'): 'siRNA 42 rescue',
                            ('Exp10', 'F01'): 'siRNA 28 rescue',

                            ('Exp11', 'A01'): 'untreated',
                            ('Exp11', 'B01'): 'control',
                            ('Exp11', 'C01'): 'siRNA 42 knock down',
                            ('Exp11', 'D01'): 'siRNA 28 knock down',
                            ('Exp11', 'E01'): 'siRNA 42 rescue',
                            ('Exp11', 'F01'): 'siRNA 28 rescue',

                            ('Exp12', 'A01'): 'untreated',
                            ('Exp12', 'B01'): 'control',
                            ('Exp12', 'C01'): 'siRNA 42 knock down',
                            ('Exp12', 'D01'): 'siRNA 28 knock down',
                            ('Exp12', 'E01'): 'siRNA 42 rescue',
                            ('Exp12', 'F01'): 'siRNA 28 rescue',
                            }

        if not all_exp:
            for pl, pos in plateDescription.keys():
                if not pl in self.settings.lstPlates:
                    del plateDescription[(pl, pos)]

        return plateDescription

    def getColumnTitles(self):

        bar_names = {
                     'total': 'Total',
                     'total_valid': 'Total Valid',

                     # secondary channel
                     'secondary_mito': 'Mito Count (PH)',
                     'nb_sec_EarlyMitosis': 'Early Mitosis (PH)',
                     'nb_sec_Metaphase': 'Metaphase (PH)',
                     'nb_sec_Anaphase': 'Anaphase (PH)',
                     'nb_sec_MitosisSegError': 'Mitosis Joint Segmentation (PH)',
                     'nb_sec_NoMitosis': 'Not Mitotic (PH)',

                     # secondary channel
                     'normmito_nb_sec_EarlyMitosis': 'Early Mitosis (among mitosis, PH)',
                     'normmito_nb_sec_Metaphase': 'Metaphase (among mitosis, PH)',
                     'normmito_nb_sec_Anaphase': 'Anaphase (among mitosis, PH)',
                     'normmito_nb_sec_MitosisSegError': 'Mitosis Joint Segmentation (among mitosis, PH)',

                     # secondary channel
                     'valid_rel_secondary_mito': 'Mito Count (percentage, PH)',
                     'valid_rel_nb_sec_EarlyMitosis': 'Early Mitosis (percentage, PH)',
                     'valid_rel_nb_sec_Metaphase': 'Metaphase (percentage, PH)',
                     'valid_rel_nb_sec_Anaphase': 'Anaphase (percentage, PH)',
                     'valid_rel_nb_sec_MitosisSegError': 'Mitosis Joint Segmentation (percentage, PH)',
                     'valid_rel_nb_sec_NoMitosis': 'Not Mitotic (percentage, PH)',

                     # secondary channel
                     'total_rel_secondary_mito': 'Mito Index, PH',
                     'total_rel_nb_sec_EarlyMitosis': 'Early Mitosis Index, PH',
                     'total_rel_nb_sec_Metaphase': 'Metaphase index, PH',
                     'total_rel_nb_sec_Anaphase': 'Anaphase index, PH',
                     'total_rel_nb_sec_MitosisSegError': 'Mitosis Joint Segmentation index, PH',
                     'total_rel_nb_sec_NoMitosis': 'Not Mitotic index, PH',

                     # primary channel
                     'primary_mito': 'Mito Count (DAPI)',
                     'nb_EarlyMitosis': 'Early Mitosis (DAPI)',
                     'nb_Metaphase': 'Metaphase (DAPI)',
                     'nb_Anaphase': 'Anaphase (DAPI)',
                     'nb_Interphase': 'Interphase (DAPI)',
                     'nb_Apoptosis': 'Apoptosis (DAPI)',
                     'nb_Polylobed': 'Polylobed (DAPI)',
                     'nb_JoinArt': 'Artifact (joint segmentation, DAPI)',
                     'nb_SegArt': 'Artifact (wrong segmentation, DAPI)',

                     # primary channel
                     'total_rel_primary_mito': 'Mito Count (perc. from all cells, DAPI)',
                     'total_rel_nb_EarlyMitosis': 'Early Mitosis (perc. from all cells, DAPI)',
                     'total_rel_nb_Metaphase': 'Metaphase (perc. from all cells, DAPI)',
                     'total_rel_nb_Anaphase': 'Anaphase (perc. from all cells, DAPI)',
                     'total_rel_nb_Interphase': 'Interphase (perc. from all cells, DAPI)',
                     'total_rel_nb_Apoptosis': 'Apoptosis (perc. from all cells, DAPI)',
                     'total_rel_nb_Polylobed': 'Polylobed (perc. from all cells, DAPI)',
                     'total_rel_nb_JoinArt': 'Artifact (perc. from all cells, joint segmentation, DAPI)',
                     'total_rel_nb_SegArt': 'Artifact (perc. from all cells, wrong segmentation, DAPI)',

                     # manual normed to mitotis
                     'normmito_Prophase (manual)': 'Prophase (perc. from mitotic cells, MANUAL)',
                     'normmito_Prometaphase (manual)': 'Prometaphase (perc. from mitotic cells, MANUAL)',
                     'normmito_Metaphase (manual)': 'Metaphase (perc. from mitotic cells, MANUAL)',
                     'normmito_Anaphase (manual)': 'Anaphase (perc. from mitotic cells, MANUAL)',
                     'normmito_Mitotic (manual)': 'Mitotic (perc. from mitotic cells, MANUAL)',
                     'normmito_EarlyMitosis (manual)': 'Early Mitosis (perc. from mitotic cells, MANUAL)',

                     # manual normed to all
                     'total_rel_Prophase (manual)': 'Prophase (perc. from all cells, MANUAL)',
                     'total_rel_Prometaphase (manual)': 'Prometaphase (perc. from all cells, MANUAL)',
                     'total_rel_Metaphase (manual)': 'Metaphase (perc. from all cells, MANUAL)',
                     'total_rel_Anaphase (manual)': 'Anaphase (perc. from all cells, MANUAL)',
                     'total_rel_Mitotic (manual)': 'Mitotic (perc. from all cells, MANUAL)',
                     'total_rel_EarlyMitosis (manual)': 'Early Mitosis (perc. from all cells, MANUAL)',

                     # manual normed to all valid
                     'valid_rel_Prophase (manual)': 'Prophase (perc. from all valid cells, MANUAL)',
                     'valid_rel_Prometaphase (manual)': 'Prometaphase (perc. from all valid cells, MANUAL)',
                     'valid_rel_Metaphase (manual)': 'Metaphase (perc. from all valid cells, MANUAL)',
                     'valid_rel_Anaphase (manual)': 'Anaphase (perc. from all valid cells, MANUAL)',
                     'valid_rel_Mitotic (manual)': 'Mitotic (perc. from all valid cells, MANUAL)',
                     'valid_rel_EarlyMitosis (manual)': 'Early Mitosis (perc. from all valid cells, MANUAL)',

                     }


        return bar_names

    def exportResults(self, res, manual_annotation=None, filename=None):

        plateDescription = self.getPlateDescription()

        manual_entries = ['Prophase (manual)',
                          'Prometaphase (manual)',
                          'Metaphase (manual)',
                          'Anaphase (manual)',
                          'Mitotic (manual)',
                          ]

        plot_entries = [
                        'total',
                        'total_valid',
                        # secondary channel
                        'secondary_mito',
                        'nb_sec_EarlyMitosis',
                        'nb_sec_Metaphase',
                        'nb_sec_Anaphase',
                        'nb_sec_MitosisSegError',
                        'nb_sec_NoMitosis',
                        # primary channel
                        'primary_mito',
                        'nb_EarlyMitosis',
                        'nb_Metaphase',
                        'nb_Anaphase',
                        'nb_Interphase',
                        'nb_Apoptosis',
                        'nb_Polylobed',
                        'nb_JoinArt',
                        'nb_SegArt',
                        ]

        bar_names = self.getColumnTitles()

        if not filename is None:
            full_filename = os.path.join(self.settings.output_folder, filename)
        else:
            full_filename = os.path.join(self.settings.output_folder, 'output_table.txt')

        fp = open(full_filename, 'w')
        if manual_annotation is None:
            title_line = ['plate', 'well', 'condition'] + [bar_names[x] for x in plot_entries]
        else:
            title_line = ['plate', 'well', 'condition'] + manual_entries + \
                ['Relative: %s' % x for x in manual_entries] + \
                ['Normalized to Mitosis: %s' % x for x in manual_entries] + \
                [bar_names[x] for x in plot_entries]
        fp.write('\t'.join(title_line) + '\n')

        if not manual_annotation is None:
            lstLabteks = sorted(res.keys())
        else:
            lstLabteks = sorted(res.keys())

        for lt in lstLabteks:
            if manual_annotation is None:
                lstPositions = sorted(res[lt].keys())
            else:
                lstPositions = sorted(manual_annotation[lt].keys())
            for pos in lstPositions:
                condition = plateDescription[(lt, pos.split('_')[0])]
                if manual_annotation is None:
                    tempStr = '\t'.join([lt, pos, condition] +
                                        [str(res[lt][pos][x]) for x in plot_entries])
                else:
                    tempStr = '\t'.join([lt, pos, condition] +
                                        [str(manual_annotation[lt][pos][x]) for x in manual_entries] +
                                        [str(float(manual_annotation[lt][pos][x]) / res[lt][pos]['total_valid'])
                                         for x in manual_entries] +
                                        [str(float(manual_annotation[lt][pos][x]) / max(manual_annotation[lt][pos]['Mitotic (manual)'], 1.0))
                                         for x in manual_entries] +
                                        [str(res[lt][pos][x]) for x in plot_entries])
                fp.write(tempStr + '\n')
        fp.close()

        return


    def renameFiles(self, in_folder, target_folder):
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        #A_01_c1
        #A1--W00001--P00001--Z00000--T00000--dapi
        lstFiles = os.listdir(in_folder)
        for filename in lstFiles:
            # old: temp =  filename.split('.')[0].split('_')
            temp = re.findall(r'[A-Za-z0-9]+', filename.split('.')[0])
            letter = temp[-3]
            pos = int(temp[-2])
            channel = temp[-1]
            correct_channel = None
            if channel in ['c0', 'C0']:
                correct_channel = 'dapi'
            if channel in ['c2', 'c2a']:
                correct_channel = 'mcherry'

            well_number = string.letters.index(letter.lower()) + 1
            try:
                new_filename = '%s1--W%05i--P%05i--Z00000--T00000--%s.tif' % (letter,
                                                                              well_number,
                                                                              pos,
                                                                              correct_channel)
            except:
                raise ValueError('Issue with image %s'
                                 'Information gathered from filename:'
                                 '\t well: %s position: %i channel: %s'
                                 % (filename, letter, pos, channel))

            print filename, ' ---> ', new_filename
            shutil.copy(os.path.join(in_folder, filename),
                        os.path.join(target_folder, new_filename))

        return

    def printSortedDataOnScreen(self, imp_data, lt, pos, sort_param='meandiff'):
        lstTracks = sorted(imp_data[lt][pos].keys())
        datavec = [imp_data[lt][pos][x][sort_param] for x in lstTracks]
        sort_data = zip(lstTracks, datavec)
        sort_data.sort(key=operator.itemgetter(-1))
        lstTracks_sorted = [x[0] for x in sort_data]
        for track in lstTracks_sorted:
            print '%i\tx:%i\ty:%i\t%s\t%f' % (track,
                                          imp_data[lt][pos][track]['coord'][0],
                                          imp_data[lt][pos][track]['coord'][1],
                                          imp_data[lt][pos][track]['phenoClass'],
                                          imp_data[lt][pos][track]['meandiff'])
        return


    def joinAutomaticToManualAnnotation(self, auto, manual):
        for lt in manual.keys():
            for pos in manual[lt].keys():
                manual[lt][pos].update(auto[lt][pos])
        return

    def getExperimentsForConditions(self, res, rescue_conditions=None):
        if rescue_conditions is None:
            rescue_conditions = ['siRNA 42 rescue', 'siRNA 28 rescue']
        revPlateDescription = self.getReversePlateDescription()
        extendedDescription = {}
        all_exp = []
        for rescue_condition in rescue_conditions:
            exp_list = revPlateDescription[rescue_condition]
            for plate, pos in exp_list:
                if not plate in res:
                    print '%s is not in data ... skipping' % plate
                plate_positions = filter(lambda x: x.rfind(pos) >= 0,
                                         res[plate].keys())
                all_exp.extend([(plate, x) for x in plate_positions])

        return all_exp

    def makeRescueApoptosisAnalysis(self, imp_data=None):

        if imp_data is None:
            imp_data = self.importAllData()

        raw_data = self.calcMitoticIndex(imp_data)
        res = self.calcFeatures(raw_data)

        rescue_conditions = ['siRNA 28 rescue', 'siRNA 42 rescue']#, 'siRNA 28 rescue']
        all_exp = self.getExperimentsForConditions(res, rescue_conditions)

        feature1 = 'total_rel_nb_Apoptosis'
        feature2 = 'valid_rel_secondary_mito'
        self.plotScatter(res, feature1, feature2, '%s--%s--%s' % (feature1, feature2, '_'.join(rescue_conditions)),
                         xlabel='Apoptosis', ylabel='Mitotic Index',
                         exp_ids=all_exp)

        feature1 = 'total_rel_nb_Apoptosis'
        feature2 = 'valid_rel_nb_sec_EarlyMitosis'
        self.plotScatter(res, feature1, feature2, '%s--%s--%s' % (feature1, feature2, '_'.join(rescue_conditions)),
                         xlabel='Apoptosis', ylabel='Early Mitosis Index',
                         exp_ids=all_exp)

        feature1 = 'nb_Apoptosis'
        feature2 = 'secondary_mito'
        self.plotScatter(res, feature1, feature2, '%s--%s--%s' % (feature1, feature2, '_'.join(rescue_conditions)),
                         xlabel='Apoptosis', ylabel='Mitotic Index',
                         exp_ids=all_exp)

        return

    def processPlates(self, imp_data=None):
        if imp_data is None:
            imp_data = self.importAllData()

        plotDir = os.path.join(self.settings.plotDir, 'summary_plots')
        if not os.path.exists(plotDir):
            os.makedirs(plotDir)

        res = self.calcMitoticIndex(imp_data)
        self.exportResults(res, filename='output_table_all_single_spots_only_automatic.txt')

        features = [
                    'total_rel_nb_Apoptosis',
                    'total_rel_secondary_mito',
                    'total_rel_nb_sec_EarlyMitosis',
                    'normmito_nb_sec_EarlyMitosis',

                    'valid_rel_secondary_mito',
                    'valid_rel_nb_sec_EarlyMitosis',
                    ]

        res_group = self.groupData(res)
        self.specificPostProcessing(res_group)
        self.makeBarplots(res_group, features=features,
                          plotDir=plotDir)

        return

    def __call__(self, imp_data=None):
        if imp_data is None:
            imp_data = self.importAllData()

        res = self.calcMitoticIndex(imp_data)
        self.exportResults(res, filename='output_table_all_single_spots_only_automatic.txt')

        manual_annotation = self.readManualAnnotation()
        self.compareManualVsAutomatic(res, manual_annotation)
        self.exportResults(res, manual_annotation, filename='output_table_single_spots.txt')

        self.joinAutomaticToManualAnnotation(res, manual_annotation)
        man_group = self.groupData(manual_annotation)
        self.specificPostProcessing(man_group)
        self.exportResults(man_group, man_group, filename='output_summary.txt')

        features = [
                    'total_rel_nb_Apoptosis',
                    'total_rel_secondary_mito',
                    'total_rel_nb_sec_EarlyMitosis',
                    'normmito_nb_sec_EarlyMitosis',

                    'total_rel_nb_Apoptosis',
                    'valid_rel_secondary_mito',
                    'valid_rel_nb_sec_EarlyMitosis',
                    ]

        res_group = self.groupData(res)
        self.specificPostProcessing(res_group)
        self.makeBarplots(res_group, features=features)

        features = [
                    'normmito_Prometaphase (manual)',
                    'normmito_EarlyMitosis (manual)',
                    'normmito_nb_sec_EarlyMitosis',
                    'valid_rel_Mitotic (manual)',
                    'valid_rel_secondary_mito',
                    'valid_rel_nb_sec_EarlyMitosis',

                    'total_rel_Mitotic (manual)',
                    'total_rel_nb_Apoptosis',
                    'total_rel_secondary_mito',
                    'total_rel_nb_sec_EarlyMitosis',

                    ]

        self.makeBarplots(man_group, features=features, filename_prefix='ManualAnnotation')


