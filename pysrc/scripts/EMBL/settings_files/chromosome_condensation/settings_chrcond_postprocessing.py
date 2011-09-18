# remote: baseDir = '/Volumes/mitocheck/Thomas/data/JKH/cecog_output'

settings_dir = os.path.join('..', 'settings_files', 'chromosome_condensation')

if os.path.exists(os.path.join(settings_dir, 'CLUSTER')):
    print 'CLUSTER VERSION'
    outDir = '/g/mitocheck/Thomas/data/JKH'
else:
    outDir = '/Users/twalter/data/JKH'

baseDir = os.path.join(outDir, 'cecog_output')
importDir = os.path.join(outDir, 'imported_event_data')
plotDir = os.path.join(outDir, 'plots')
singleCellPlotDir = os.path.join(plotDir, 'single_cell_plots')

# plates: if plates are not defined, the inDir is screened and all subdirectories
# are taken as plates.
plates = [
          'plate1_1_013'
          ]

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

class_color_code = {
                    'interphase'     :   '#fe761b',
                    'early_prophase' :   '#a9e8ef',
                    'mid_prophase'   :   '#4e9dff',
                    'prometaphase'   :   '#00458a',
                    'metaphase'      :   '#3af33a',
                    'early_anaphase' :   '#40c914',
                    'late_anaphase'  :   '#2d8f0c',
                    'apoptosis'      :   '#fe1710',
                    'artefact'       :   '#fe51c3',
                    'out-of-focus'   :   '#9321fe',
                    }


obj_regex = re.compile('__T(?P<Time>\d+)__O(?P<Object>\d+)')
#pos_regex = re.compile('W(?P<Well>\d+)--P(?P<Position>\d+)')
pos_regex = re.compile('(?P<Position>\d+)')
track_id_regex = re.compile('T(?P<Time>\d+)__O(?P<Object>\d+)')
remove_empty_fields = False

# track_dir is either 'full' or 'events' (if events are selected)
#track_dir = 'events'

