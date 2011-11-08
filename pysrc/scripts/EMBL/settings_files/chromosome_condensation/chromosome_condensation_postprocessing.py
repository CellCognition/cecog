
import inspect

settings_dir = os.path.abspath(os.path.dirname(inspect.getfile( inspect.currentframe() )))

if os.path.exists(os.path.join(settings_dir, 'CLUSTER')):
    print 'CLUSTER VERSION'
    outDir = '/g/mitocheck/Thomas/data/JKH'
else:
    outDir = '/Users/twalter/data/JKH'

baseDir = os.path.join(outDir, 'cecog_output')
importDir = os.path.join(outDir, 'imported_event_data')
plotDir = os.path.join(outDir, 'plots')
singleCellPlotDir = os.path.join(plotDir, 'single_cell_plots')

htmlDir = os.path.join(outDir, 'html')
galleryDir = os.path.join(outDir, 'galleries')
htmlResourceDir = os.path.join(outDir, 'html_resources')

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

plates = [
          'plate1_1_013',
          ]

qc_rules = {
            }

single_cell_plot_settings = {
                             'featureData': [('primary', 'primary', 'lda_projection'),
                                             ],
                             'classificationData': [('primary', 'primary')]
                             }

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
trainingset_filename = os.path.join(outDir, 'cecog_classifiers', 'classifier3','data','features.arff')

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

PHENOCLASSES_FOR_TRAINING = ['interphase', 'mid_prophase',]
PHENOCLASSES = ['interphase', 'early_prophase', 'mid_prophase',]

###############################################################
# HTML SETTINGS
value_extraction = OrderedDict([
                                ('count(early)', (ValueCounter('early_prophase'), 'primary', 'primary', 'class__name')),
                                ('count(mid)', (ValueCounter('mid_prophase'), 'primary', 'primary', 'class__name')),
                                ])

html_plot_col_title = OrderedDict([
                                   ('lda_projection', 'LDA'),
                                   #('avg_norm', 'Transloc'),
                                   ])

