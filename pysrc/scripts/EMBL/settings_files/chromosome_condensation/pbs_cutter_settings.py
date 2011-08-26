
# to start this script:
# setenv LD_LIBRARY_PATH /g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
# setenv PYTHONPATH /g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc
# cd /g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc/scripts/projects
# python-2.7 pbs_script_generation.py -b project_settings/pbs_chromosome_condensation_settings.py

path_command = """export LD_LIBRARY_PATH=/g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
export PYTHONPATH=/g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc"""

#    parser.add_option("--raw_image_path", dest="raw_image_path",
#                      help="raw image directory (base directory)")
#    parser.add_option("--out_path", dest="out_path",
#                      help="base output path for galleries")
#    parser.add_option("--plate", dest="plate",
#                      help="plate for cutting")
#    parser.add_option("--track_data_filename", dest="track_data_filename",
#                      help="filename containing track data")
#    parser.add_option("--positions", dest="positions",
#                      help="positions to be cut")
#    #parser.add_option("--create_no_images", action="store_false", dest="create_images",
#    #                  help="Turn image creation off.")
#
#    parser.add_option("--skip_done", action="store_true", dest='skip_done',
#                      help="if this option is set, tracks with existing galleries are skipped.")
#    parser.add_option("--not_skip_done", action="store_false", dest='skip_done',
#                      help="if this option is set, tracks with existing galleries are not skipped.")

# settings for scripts
base_analysis_dir = '/g/mitocheck/Thomas/data/JKH'
raw_image_path = '/g/ellenberg/JKH/chr_cond_screen'
#baseInDir = '/g/ellenberg/JKH/chr_cond_screen'

baseScriptDir = os.path.join(base_analysis_dir, 'scripts')
track_data_dir = os.path.join(base_analysis_dir, 'track_data')
scriptPrefix = 'CecogCut'

additional_attributes = {
                         'raw_image_path': raw_image_path,
                         'out_path': os.path.join(base_analysis_dir, 'galleries'),
                         'skip_done': True
                         }

# data directories
#baseOutDir = '/g/mitocheck/Thomas/data/JKH/cecog_output'


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


