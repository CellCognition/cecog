
# to start this script:
# OLD: setenv LD_LIBRARY_PATH /g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
# OLD: setenv PYTHONPATH /g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc
# OLD: cd /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/projects
# OLD: python-2.7 pbs_script_generation.py -b project_settings/pbs_chromosome_condensation_settings.py

# setenv PYTHONPATH /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc
# python-2.7 /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/cluster/pbs_script_generation.py -b /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/settings_files/chromosome_condensation/pbs_chromosome_condensation_settings.py

path_command = """export LD_LIBRARY_PATH=/g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
export PYTHONPATH=/g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc"""

# data directories
baseInDir = '/g/ellenberg/JKH/PTP4A3'
baseOutDir = '/g/ellenberg/JKH/cecog/output'
#baseInDir = '/g/ellenberg/JKH/chr_cond_screen'
#baseOutDir = '/g/mitocheck/Thomas/data/JKH/cecog_output'


# settings for scripts
baseScriptDir = '/g/mitocheck/Thomas/data/JKH/scripts'
scriptPrefix = 'PostPaperProcessing'

# settingsfile
settingsFilename = '/g/mitocheck/Thomas/data/JKH/cecog_settings/screen_settings_2011-11-16.conf'
#settingsFilename = '/g/ellenberg/JKH/cecog/pbs_PTP4A3_settings.py'
#settingsFilename = '/g/ellenberg/JKH/cecog/settings/settings_PTP4A3_rescue-2013-01-17.conf'

# plates=None means that all plates found in baseInDir are going to be processed.
plates = None
#plates = ['plate1_1_013']

batchScriptDirectory = '/g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/cecog/batch'
pythonBinary = 'python-2.7'
batchScript = 'batch.py'

# PBS settings (cluster, walltime, log folders)
clusterName = 'clng_new'
pbsOutDir = '/g/mitocheck/PBS/JKH'
pbsErrDir = '/g/mitocheck/PBS/JKH'
pbsMail = 'twalter@embl.de'

hours = 16
minutes = 0
ncpus = 1
mem = 7
jobSize = 8
omit_processed_positions = False

additional_flags = []

additional_attributes = {
                         }

rendering = {}
#rendering_class = {}

rendering_class = {'primary_classification':
                   {
                    'Primary': {'raw': ('#FFFFFF', 1.0),
                                'contours': [('primary', 'class_label', 1, False),
                                             #('primary', '#000000', 1, False)
                                             ]},
                    },
                    }

primary_graph = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/graph_primary.txt'
secondary_graph = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog/cecog_settings/graph_secondary.txt'
filename_to_r = '/g/software/bin/R-2.13.0'

primary_classification_envpath = '/g/mitocheck/Thomas/data/JKH/cecog_classifiers/classifier3'

# folders to be generated
lstFolders = [pbsOutDir, pbsErrDir, baseScriptDir, baseOutDir]


