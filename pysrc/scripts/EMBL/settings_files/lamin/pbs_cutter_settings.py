
# to start this script:
# setenv LD_LIBRARY_PATH /g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
# setenv PYTHONPATH /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc
# cd /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/projects
# python-2.7 pbs_cutter.py -b project_settings/pbs_cutter_settings.py
# then, execute the last line of the output to submit the jobs.
VERSION = '1.2.4'

path_command = """export LD_LIBRARY_PATH=/g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib
export PYTHONPATH=/g/software/linux/pack/cellcognition-%s/SRC/cecog_git/pysrc""" % VERSION

# settings for scripts
raw_image_path = '/g/mattaj/Moritz/Olympus data'
base_analysis_dir = '/g/mitocheck/Thomas/data/Moritz_analysis_cecog'

#base_analysis_dir = '/g/mitocheck/Thomas/data/JKH'
#raw_image_path = '/g/ellenberg/JKH/chr_cond_screen'
plate_regex = re.compile('^plate')
#baseInDir = '/g/ellenberg/JKH/chr_cond_screen'

baseScriptDir = os.path.join(base_analysis_dir, 'scripts')
track_data_dir = os.path.join(base_analysis_dir, 'track_data')
scriptPrefix = 'RIBBON'

additional_attributes = {
                         'raw_image_path': '"%s"' % raw_image_path,
                         'out_path': os.path.join(base_analysis_dir, 'galleries'),
                         'skip_done': True,
                         #'settings_filename': os.path.join(os.path.dirname(__file__),
                         #                                  '..', 'settings_files', 'chromosome_condensation_settings',
                         #                                  'settings_chrcond_postprocessing.py')
                         #'settings_filename': os.path.join('..', 'settings_files', 'chromosome_condensation',
                         #                                  'settings_chrcond_postprocessing.py')
                         'settings_filename': os.path.join('..', 'settings_files', 'lamin',
                                                           'settings_lamin_analysis.py'),
                         'image_container_regex':  '"cecog_imagecontainer___PL(?P<plate>.+)\.pkl"',
                         }

# plates=None means that all plates found in baseInDir are going to be processed.
#plates = None #['plate1_2_006']
plates = [
          '110820_mutants_LB_Compressed'
          ]

batchScriptDirectory = '/g/software/linux/pack/cellcognition-%s/SRC/cecog_git/pysrc/scripts/EMBL/cutter/' % VERSION
pythonBinary = 'python-2.7'
batchScript = 'cut_tracks_from_resultfile.py'

# PBS settings (cluster, walltime, log folders)
clusterName = 'clng_new'
pbsOutDir = '/g/mitocheck/PBS/LAMIN_CUT'
pbsErrDir = '/g/mitocheck/PBS/LAMIN_CUT'
pbsMail = 'twalter@embl.de'

hours = 16
minutes = 0
ncpus = 1
mem = 7
jobSize = 1

processWholePlates = False

# folders to be generated
lstFolders = [pbsOutDir, pbsErrDir, baseScriptDir,
              additional_attributes['out_path']]


