
# to start this script:
# cd /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/cluster
# for example:
# python-2.7 pbs_script_generation.py -b <settings_filename>
# python-2.7 pbs_script_generation.py -b ../settings_files/chromosome_condensation/pbs_chromosome_condensation_settings.py
# python-2.7 pbs_script_generation.py -b ../settings_files/lamin/pbs_laminb_settings.py


path_command = """setenv PATH /cbio/donnees/nvaroquaux/.local/bin:${PATH}
setenv LD_LIBRARY_PATH ${LD_LIBRARY_PATH}:/cbio/donnees/nvaroquaux/.local/lib
setenv LIBRARY_PATH /cbio/donnees/nvaroquaux/.local/lib
setenv PYTHONPATH /cbio/donnees/twalter/workspace/cecog/pysrc
setenv DRMAA_LIBRARY_PATH /opt/gridengine/lib/lx26-amd64/libdrmaa.so
"""

# data directories
baseInDir = '/share/data/mitocheck/compressed_data'
baseOutDir = '/cbio/donnees/twalter/data/mitocheck/results'

# settings for scripts
baseScriptDir = '/cbio/donnees/twalter/data/mitocheck/scripts'
scriptPrefix = 'MITOSEGMENTATION'

# settingsfile
settingsFilename = '/cbio/donnees/twalter/data/mitocheck/settings/settings_2012-10-15.conf'

# plates=None means that all plates found in baseInDir are going to be processed.
# plates = None
plates = [
          'LT0159_49--ex2006_01_18--sp2006_01_10--tt17--c5',
          ]

batchScriptDirectory = '/cbio/donnees/twalter/workspace/cecog/pysrc/cecog/batch'
pythonBinary = 'python'
batchScript = 'batch.py'

# PBS settings (cluster, walltime, log folders)
#pbsArrayEnvVar = 'PBS_ARRAY_INDEX'
pbsArrayEnvVar = 'GE_TASK_ID'
jobArrayOption = 't'
clusterName = None
pbsOutDir = ':/cbio/donnees/twalter/PBS'
pbsErrDir = ':/cbio/donnees/twalter/PBS'
pbsMail = 'thomas.walter@mines-paristech.fr'

hours = 16
minutes = 0
ncpus = 1
mem = 2
jobSize = 30
omit_processed_positions = False

additional_flags = []

additional_attributes = {
                         }

rendering = {}

#rendering = {
#             'primary_contours':
#             {'Primary': {'raw': ('#FFFFFF', 1.0),
#                          'contours': {'primary': ('#FF0000', 1, True)}
#                          }
#             },
#             'secondary_contours':
#             {'Secondary': {'raw': ('#FFFFFF', 1.0),
#                            'contours': {'propagate': ('#FF0000', 1, True)}
#                            }
#             }
#             }

rendering_class = {}
#rendering_class = {'primary_classification':
#                   {
#                    'Primary': {'raw': ('#FFFFFF', 1.0),
#                                'contours': [('primary', 'class_label', 1, False),
#                                             ('primary', '#000000', 1, False)]},
##                    'Secondary': {'raw': ('#00FF00', 1.0),
##                                  'contours': [('propagate', 'class_label', 1, False),
##                                               ('propagate', '#000000', 1, False)]}
#                    },
#                    'secondary_classification':
#                    {
#                     'Secondary': {'raw': ('#FFFFFF', 1.0),
#                                   'contours': [('propagate', 'class_label', 1, False),
#                                                ('propagate', '#000000', 1, False)]}
#                     }
#                    }

#primary_graph = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/graph_primary.txt'
#secondary_graph = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/graph_secondary.txt'
#filename_to_r = '/g/software/bin/R-2.13.0'

primary_graph = None
secondary_graph = None
filename_to_r = None

#primary_classification_envpath = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_classifiers/23092011_H2B-LB1_TRFX_H2B'
#secondary_classification_envpath = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_classifiers/111222_H2B_TRFX_LB1'
primary_classification_envpath = None
secondary_classification_envpath = None

#filename_to_r = '/Users/twalter/software/R/R.framework/Versions/2.13/Resources/bin/R'
#primary_graph = '/Users/twalter/data/Moritz_cecog/cecog_settings/graph_primary.txt'
#secondary_graph = '/Users/twalter/data/Moritz_cecog/cecog_settings/graph_secondary.txt'

# example: overlay the primary results to the two-channel image.
# primary channel in red, secondary channel in green.
# The secondary segmentation is propagate
#rendering_class = {'primary_classification':
#                   {'Primary': {'raw': ('#FF0000', 1.0),
#                                'contours': [('primary', 'class_label', 1, False)]},
#                    'Secondary': {'raw': ('#00FF00', 1.0),
#                                  'propagate': [('propagate', 'class_label', 1, False)]}
#                    }
#                   }

# folders to be generated
lstFolders = [pbsOutDir, pbsErrDir, baseScriptDir, baseOutDir]


