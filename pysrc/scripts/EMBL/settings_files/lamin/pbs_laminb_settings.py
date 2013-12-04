
# to start this script:
# cd /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/cluster
# for example:
# python-2.7 pbs_script_generation.py -b <settings_filename>
# python-2.7 pbs_script_generation.py -b ../settings_files/chromosome_condensation/pbs_chromosome_condensation_settings.py
# python-2.7 pbs_script_generation.py -b ../settings_files/lamin/pbs_laminb_settings.py


path_command = """export LD_LIBRARY_PATH=/g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
export PYTHONPATH=/g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc"""

# data directories
baseInDir = '/g/mattaj/Moritz/Olympus data'
baseOutDir = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_output'

# settings for scripts
baseScriptDir = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/scripts'
scriptPrefix = 'ENHSECCLASS'

# settingsfile
settingsFilename = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/settings2011-12-22.conf'

# plates=None means that all plates found in baseInDir are going to be processed.
# plates = None
plates = [
          '110820_mutants_LB_Compressed',
          '111027_RNAi_LB_Compressed',
          '111020_chemicals_LB_Compressed',
          ]

batchScriptDirectory = '/g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/cecog/batch'
pythonBinary = 'python-2.7'
batchScript = 'batch.py'

# PBS settings (cluster, walltime, log folders)
clusterName = 'clng_new'
pbsOutDir = '/g/mitocheck/PBS/laminlda'
pbsErrDir = '/g/mitocheck/PBS/laminlda'
pbsMail = 'twalter@embl.de'

hours = 16
minutes = 0
ncpus = 1
mem = 7
jobSize = 1
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

primary_graph = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/graph_primary.txt'
secondary_graph = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/graph_secondary.txt'
filename_to_r = '/g/software/bin/R-2.13.0'

primary_classification_envpath = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_classifiers/23092011_H2B-LB1_TRFX_H2B'
secondary_classification_envpath = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_classifiers/111222_H2B_TRFX_LB1'

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


