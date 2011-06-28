
# to start this script:
# setenv LD_LIBRARY_PATH /g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
# setenv PYTHONPATH /g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc
# cd /g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc/scripts/projects
# python-2.7 pbs_script_generation.py -b project_settings/pbs_chromosome_condensation_settings.py

path_command = """export LD_LIBRARY_PATH=/g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
export PYTHONPATH=/g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc"""

# data directories
baseInDir = '/g/ellenberg/JKH/chr_cond_screen'
baseOutDir = '/g/mitocheck/Thomas/data/JKH/cecog_output'

# settings for scripts
baseScriptDir = '/g/mitocheck/Thomas/data/JKH/scripts'
scriptPrefix = 'CHROMIS'

# settingsfile
settingsFilename = '/g/mitocheck/Thomas/data/JKH/cecog_settings/screen_settings_2011-06-09.conf'

# plates=None means that all plates found in baseInDir are going to be processed.
plates = None #['plate1_2_006']

batchScriptDirectory = '/g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc/cecog/batch'
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
jobSize = 4
omit_processed_positions = True

additional_attributes = {
                         'create_images': False,
                         }

# folders to be generated
lstFolders = [pbsOutDir, pbsErrDir, baseScriptDir, baseOutDir]


