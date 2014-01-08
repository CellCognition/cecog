
import inspect

settings_dir = os.path.abspath(os.path.dirname(inspect.getfile( inspect.currentframe() )))

if os.path.exists(os.path.join(settings_dir, 'CLUSTER')):
    print 'CLUSTER VERSION'
    outDir = '/g/ellenberg/JKH/cecog'    
else:
    outDir = '/Users/twalter/data/JKH'

baseDir = os.path.join(outDir, 'output')
importDir = os.path.join(outDir, 'imported_event_data')
plotDir = os.path.join(outDir, 'plots')
singleCellPlotDir = os.path.join(plotDir, 'single_cell_plots')
panelDir = os.path.join(plotDir, 'panels')

htmlDir = os.path.join(outDir, 'html')
galleryDir = os.path.join(outDir, 'galleries')
htmlResourceDir = os.path.join(outDir, 'html_resources')

feature_export_dir = os.path.join(outDir, 'pickle_feature_export')

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
                                    #'primary': ['tracking__center_x', 'feature__granu_close_volume_2'],
                                    'primary': 'all',
                                    },
                        }


# for the moment, plates has to be determined (None does not work for the moment!)
plates = [
          '2012-11-16-test_plate_009',
          'PTP4A3_rescue-2013-01-17',
          ]

positions = None

qc_rules = {
            }

#single_cell_plot_settings = {
#                             'featureData': [('primary', 'primary', 'lda_projection'),
#                                             ],
#                             'classificationData': [('primary', 'primary')]
#                             }

features_normalization = [
                          'feature__granu_open_volume_1',
                          'feature__h2_IDM',
                          'feature__ls0_CAREA_sample_mean'
                          ]

features_selection = [
                      'granu_open_volume_1',
                      'h2_IDM',
                      'ls0_CAREA_sample_mean',
                      #'ls1_NCA_sample_sd',
                      #'h1_2CON',
                      #'h1_IDM',
                      ]

# this contains the settings for the single plots. 
# The key indicates the feature name: 
single_cell_plot_settings = {
                             'classification_decision_value_reduced_norm':
                                {
                                 'featureData': [('primary', 'primary', 'lda_decvalue_reduced_norm'),
                                                 ('primary', 'primary', 'svm_decvalue_reduced_norm'),
                                                 ('primary', 'primary', 'logres_decvalue_reduced_norm'),],
                                 'classificationData': [('primary', 'primary')]
                                 },
                             'feature_selection':
                                {
                                 'featureData': [('primary', 'primary', 'normalized__granu_open_volume_1'),
                                                 ('primary', 'primary', 'normalized__h2_IDM'),
                                                 ('primary', 'primary', 'normalized__ls0_CAREA_sample_mean'),],
                                 'classificationData': [('primary', 'primary')]
                                 },
                             }

# panels for the gallery
# (corresponding to coloured rectangles, each representing a classification result).
# The panels can be oriented above and under the galleries.
panel_settings = {
                  #'featureData': [('primary', 'primary', 'lda_projection'),
                  #                ],
                  'classificationData': [('primary_classification_panel', 'primary', 'primary')]
                  }

upper_panels = ['primary_classification_panel']
lower_panels = []
gallery_single_image_width = 101

# colors for the plot of classification results
class_color_code = {
                    ('primary', 'primary'):
                    {
                     'color_code':
                        {
                         'interphase'       :   '#fe761b',
                         'early_prophase'   :   '#a9e8ef',
                         'mid_prophase'     :   '#4e9dff',
                         'prometaphase'     :   '#00458a',
                         'metaphase'        :   '#3af33a',
                         'early_anaphase'   :   '#40c914',
                         'late_anaphase'    :   '#2d8f0c',
                         'apoptosis'        :   '#fe1710',
                         'artefact'         :   '#fe51c3',
                         'out-of-focus'     :   '#9321fe',
                         },
                      'class_list':
                         [
                          'interphase', 'early_prophase', 'mid_prophase',
                          'prometaphase', 'metaphase', 'early_anaphase',
                          'late_anaphase', 'apoptosis', 'artefact',
                          'out-of-focus',
                          ],
                      'legend_title': 'mitosis',
                      },
                    }

legend_titles = {}

###############################################################
# REGULAR EXPRESSIONS

obj_regex = re.compile('__T(?P<Time>\d+)__O(?P<Object>\d+)')
#pos_regex = re.compile('W(?P<Well>\d+)--P(?P<Position>\d+)')
pos_regex = re.compile('(?P<Position>\d+)')
subpos_regex = re.compile('(?P<Well>[A-Za-z0-9]+)_(?P<Subwell>[0-9]+)')
track_id_regex = re.compile('T(?P<Time>\d+)__O(?P<Object>\d+)')
remove_empty_fields = False

###############################################################
# FEATURE PROJECTION
#tempDir = '/g/mitocheck/Thomas/data/JKH'
#trainingset_filename = os.path.join(tempDir, 'cecog_classifiers', 'classifier3','data','features.arff')
trainingset_filename = '/g/ellenberg/JKH/cecog/classifiers/chr_cond_classifier/data/features.arff'

# features to remove from the analysis (typically because of high correlation)
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

# classes for LDA projection
PHENOCLASSES_FOR_TRAINING = ['interphase', 'mid_prophase',]
PHENOCLASSES = ['interphase', 'early_prophase', 'mid_prophase',]

###############################################################
# HTML SETTINGS
# These are values to be displayed in the html page, starting with the title of the column
# and then the way how to extract the data. 
# The first entry for instance calls the ValueCounter (with __call__ function) which
# counts occurences of early_prophase in channel=primary, region=primary and column=class_name.
value_extraction = OrderedDict([
                                ('count(early)', (ValueCounter('early_prophase'), 'primary', 'primary', 'class__name')),
                                ('count(mid)', (ValueCounter('mid_prophase'), 'primary', 'primary', 'class__name')),
                                ])

# The columns of the html-page: List of tuples, each tuple takes 
# the variable name and the title of the column. 
html_plot_col_title = OrderedDict([
                                   ('classification_decision_value_reduced_norm', 'Projection (select, normalized)'),                                   
                                   #('classification_decision_value_norm', 'Projection (normalized)'),
                                   ('feature_selection', 'Feature Selection'),
                                   #('avg_norm', 'Transloc'),
                                   ])

# The order of galleries.
gallery_channels = ['primary']

# This is True if the galleries from Cellcognition are used. 
# otherwise it is False (use galleries from the cutter script instead. 
# Note that this is quite different: if the galleries were generated with the cutter script
# they contain already two channels, whereas if they are generated with cellcognition
# directly, we must specifiy ['primary', 'secondary'] above to have them both. 
use_cecog_galleries = False


