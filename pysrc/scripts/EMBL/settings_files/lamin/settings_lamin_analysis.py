# remote: baseDir = '/Volumes/mitocheck/Thomas/data/JKH/cecog_output'

#settings_dir = os.path.join('..', 'settings_files', 'lamin')
#settings_dir = os.path.abspath(__file__)

#print ' *** INSPECT RESULTS: ', inspect.getfile( inspect.currentframe() )

#print ' *** settings directory ', settings_dir

import inspect

settings_dir = os.path.abspath(os.path.dirname(inspect.getfile( inspect.currentframe() )))

if os.path.exists(os.path.join(settings_dir, 'CLUSTER')):
    print 'CLUSTER VERSION'
    outDir = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog'
else:
    outDir = '/Users/twalter/data/Moritz_cecog'

baseDir = os.path.join(outDir, 'cecog_output')
importDir = os.path.join(outDir, 'imported_event_data')
plotDir = os.path.join(outDir, 'plots')
singleCellPlotDir = os.path.join(plotDir, 'single_cell_plots')

htmlDir = os.path.join(outDir, 'html')
galleryDir = os.path.join(outDir, 'galleries')
htmlResourceDir = os.path.join(outDir, 'html_resources')

#foldersToCreate = [singleCellPlotDir,
#                   htmlDir]


# plates: if plates are not defined, the inDir is screened and all subdirectories
# are taken as plates.
plates = [
          '110820_mutants_LB_Compressed'
          ]

qc_rules = {
            'min_exp_level': 5.0,
            'max_exp_level': 80.0,
            }

# settings for the full track importer
# the key has the structure (channel, region, feature)
import_entries_full = {
                       'primary': {
                                   'primary': ['className', 'centerX', 'centerY',
                                               'mean', 'sd'],
                                   #'primary': 'all'
                                   }
                       }


# settings for the event track importer
# the key has the structure (channel, region, feature)
import_entries_event = {
                        'primary': {
                                    'primary': ['tracking__center_x', 'tracking__center_y',
                                                'class__name', 'class__label', 'class__probability'],
                                    },

                        'secondary': {
                                      'propagate': 'all',
                                      #'propagate': ['tracking__center_x', 'tracking__center_y',
                                      #              'class__name', 'class__label', 'class__probability'],
                                      },
                        'tertiary': {
                                     'inside': ['feature__n2_avg'],
                                     'rim': ['feature__n2_avg'],
                                     'outside': ['feature__n2_avg'],
                                     }
                        }

single_cell_plot_settings = {
                             'featureData': [#('secondary', 'propagate', 'lda_projection'),
                                             ('tertiary', 'diff_out_in', 'feature__avg_norm'),
                                             ],
                             'classificationData': [('primary', 'primary'),
                                                    ('secondary', 'propagate')]
                             }

class_color_code = {
                    ('primary', 'primary'):
                    {
                     'color_code':
                        {
                         'inter'    :    '#00ff00',
                         'pro'      :    '#ffff00',
                         'prometa'  :    '#ff8000',
                         'meta'     :    '#ff00ff',
                         'early ana':    '#800080',
                         'late ana' :    '#0000ff',
                         'telo'     :    '#00ffff',
                         'apoptosis':    '#ff0000',
                         'disformed':    '#5b783c',
                         },
                      'class_list':
                         [
                          'inter', 'pro', 'prometa', 'meta',
                          'early ana', 'late ana', 'telo',
                          'apoptosis', 'disformed'
                          ],
                      'legend_title': 'mitosis',
                      },
                    ('secondary', 'propagate'):
                    {
                     'color_code':
                        {
                         'assembled'   : '#00ff00',
                         'deforming'   : '#0000ff',
                         'disassembling' :   '#800080',
                         'disassembled'   : '#ff8000',
                         },
                     'class_list':
                         [
                          'assembled', 'deforming',
                          'disassembling', 'disassembled'
                          ],
                     'legend_title': 'lamin',
                    }
                    }

legend_titles = {

                 }

obj_regex = re.compile('__T(?P<Time>\d+)__O(?P<Object>\d+)')
#pos_regex = re.compile('W(?P<Well>\d+)--P(?P<Position>\d+)')
pos_regex = re.compile('(?P<Position>\d+)')
subpos_regex = re.compile('(?P<Well>[A-Za-z0-9]+)_(?P<Subwell>[0-9]+)')
track_id_regex = re.compile('T(?P<Time>\d+)__O(?P<Object>\d+)')
remove_empty_fields = False

###############################################################
# FEATURE PROJECTION

trainingset_filename = os.path.join(outDir, 'cecog_classifiers/01102011_H2B-LB1_TRFX_LB1/data/features.arff')

FEATURES_REMOVE = [
                   'h4_2ASM', 'h4_2CON', 'h4_2COR', 'h4_2COV',
                   'h4_2DAV', 'h4_2ENT', 'h4_2IDM', 'h4_2PRO',
                   'h4_2SAV', 'h4_2SET', 'h4_2SHA', 'h4_2SVA',
                   'h4_2VAR', 'h4_2average', 'h4_2variance',
                   'h4_ASM', 'h4_CON', 'h4_COR', 'h4_COV',
                   'h4_DAV', 'h4_ENT', 'h4_IDM', 'h4_PRO',
                   'h4_SAV', 'h4_SET', 'h4_SHA', 'h4_SVA',
                   'h4_VAR', 'h4_average', 'h4_variance',
                   'h8_2ASM', 'h8_2CON', 'h8_2COR', 'h8_2COV',
                   'h8_2DAV', 'h8_2ENT', 'h8_2IDM', 'h8_2PRO',
                   'h8_2SAV', 'h8_2SET', 'h8_2SHA', 'h8_2SVA',
                   'h8_2VAR', 'h8_2average', 'h8_2variance',
                   'h8_ASM', 'h8_CON', 'h8_COR', 'h8_COV',
                   'h8_DAV', 'h8_ENT', 'h8_IDM', 'h8_PRO',
                   'h8_SAV', 'h8_SET', 'h8_SHA', 'h8_SVA',
                   'h8_VAR', 'h8_average', 'h8_variance'
                   ]

PHENOCLASSES_FOR_TRAINING = ['assembled', 'disassembled']
PHENOCLASSES = ['assembled', 'disassembling', 'disassembled']

colordict = {
             'disassembling': (0.4, 0.1, 0.5),
             'disassembled': (0.1, 0.1, 0.9),
             'deforming': (0.2, 0.7, 0.2),
             'assembled': (0.9, 0.1, 0.1),
             'defective': (0.2, 0.2, 0.2),
             }

# HTML SETTINGS
value_extraction = OrderedDict([
                                ('count(disass)', (ValueCounter('disassembling'), 'secondary', 'propagate', 'class__name')),
                                ('dis count > meta', (ConditionalValueCounter('disassembling', 'meta'),
                                                      'secondary', 'propagate', 'class__name',
                                                      'primary', 'primary', 'class__name')),
                                ('dis count > dis', (ConditionalValueCounter('disassembling', 'disassembled'),
                                                     'secondary', 'propagate', 'class__name',
                                                     'secondary', 'propagate', 'class__name')),

                                ('expr', ['expression_level'])
                                ])

html_plot_col_title = OrderedDict([
                                   #('lda_projection', 'LDA'),
                                   ('avg_norm', 'Transloc'),
                                   ])

#value_extraction = {
#                   'mean_SECONDARY_rim_bgsub_normalized_max': ('mean_SECONDARY_rim_bgsub_normalized', max, 'Max'),
#                   'mean_SECONDARY_inside_bgsub_normalized_max': ('mean_SECONDARY_inside_bgsub_normalized', max, 'Max'),
#                   'mean_SECONDARY_expanded_bgsub_normalized_max': ('mean_SECONDARY_expanded_bgsub_normalized', max, 'Max'),
#                   'mean_SECONDARY_rim_bgsub_init': ('mean_SECONDARY_rim_bgsub', operator.itemgetter(0), 'Init'),
#                   'mean_SECONDARY_inside_bgsub_init': ('mean_SECONDARY_inside_bgsub', operator.itemgetter(0), 'Init'),
#                   'mean_SECONDARY_expanded_bgsub_init': ('mean_SECONDARY_expanded_bgsub', operator.itemgetter(0), 'Init'),
#                   }
#
#value_keys = [
#              'mean_SECONDARY_rim_bgsub_normalized_max',
#              'mean_SECONDARY_inside_bgsub_normalized_max',
#              'mean_SECONDARY_expanded_bgsub_normalized_max',
#              'mean_SECONDARY_rim_bgsub_init',
#              'mean_SECONDARY_inside_bgsub_init',
#              'mean_SECONDARY_expanded_bgsub_init'
#              ]
#
#html_plot_keys = [
#                  'mean_SECONDARY_rim_bgsub_normalized',
#                  'mean_SECONDARY_inside_bgsub_normalized',
#                  'mean_SECONDARY_expanded_bgsub_normalized',
#                  ]
#
#html_col_title = {
#                  'mean_SECONDARY_rim_bgsub_normalized': 'Rim,norm',
#                  'mean_SECONDARY_inside_bgsub_normalized': 'Inside,norm',
#                  'mean_SECONDARY_expanded_bgsub_normalized': 'Expanded,norm',
#                  'mean_SECONDARY_rim_bgsub': 'Rim,bg',
#                  'mean_SECONDARY_inside_bgsub': 'Inside,bg',
#                  'mean_SECONDARY_expanded_bgsub': 'Expanded,bg',
#                  }


# track_dir is either 'full' or 'events' (if events are selected)
#track_dir = 'events'

