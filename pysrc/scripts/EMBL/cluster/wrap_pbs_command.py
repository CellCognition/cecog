import os, re, time, sys, pickle
from optparse import OptionParser

from collections import OrderedDict

from scripts.EMBL.settings import Settings
from scripts.EMBL.projects.chromosome_condensation import *

path_command = 'cd /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/projects'
#command = 'python-2.7 chromosome_condensation.py -s ../settings_files/chromosome_condensation/chromosome_condensation_postprocessing.py --export --plate %s' #--plot_generation --panel_generation'
command = 'python-2.7 '

array_script_name = 'CONVMISSING'
#script_dir = '/g/mitocheck/Thomas/data/JKH/scripts'
script_dir = '/g/mitocheck/Thomas/conversion/scripts'

job_size = 1

hours = 12
minutes = 0

if __name__ == "__main__":

    description =\
'''
%prog - Generation of scripts as a job array for a PBS cluster.
'''

    parser = OptionParser(usage="usage: %prog [options]",
                         description=description)

    parser.add_option("-s", "--settings_file", dest="settings_file",
                      help="settings filename (parameters for the postprocessing pipeline)")

    (options, args) = parser.parse_args()

    if (options.settings_file is None):
        parser.error("incorrect number of arguments!")

    oSettings = Settings(os.path.abspath(options.settings_file), dctGlobals=globals())
    plates = oSettings.plates

    if plates is None:
        plates = filter(lambda x: os.path.isdir(os.path.join(oSettings.baseDir, x)),
                        os.listdir(oSettings.baseDir))


    if not os.path.isdir(script_dir):
        os.makedirs(script_dir)
    pbs_out_dir = '/g/mitocheck/PBS/%s' % array_script_name
    if not os.path.isdir(pbs_out_dir):
        os.makedirs(pbs_out_dir)

    head = """#!/bin/bash
#PBS -l walltime=%02i:%02i:00
#PBS -M twalter@embl.de
#PBS -m e
#PBS -o /g/mitocheck/PBS/%s
#PBS -e /g/mitocheck/PBS/%s
""" % (hours, minutes, array_script_name, array_script_name)

    jobCount = 1
    for plate in plates:
        cmd = path_command + '\n'
        cmd += (command % plate) + '\n'

        script_name = '%s%i.sh' % (os.path.join(script_dir, array_script_name), jobCount)
        script_file = open(script_name, "w")
        script_file.write(head + cmd)
        script_file.close()
        os.system('chmod a+rwx %s' % script_name)

        jobCount += 1

    # create main file to be submitted to the pbs server.
    main_script_name = '%s_main.sh' % os.path.join(script_dir, array_script_name)
    main_script_file = file(main_script_name, 'w')
    main_content = """#!/bin/bash
#PBS -J 1-%i
#PBS -q clng_new
#PBS -M twalter@embl.de
#PBS -m e
#PBS -o /g/mitocheck/PBS/%s
#PBS -e /g/mitocheck/PBS/%s
%s$PBS_ARRAY_INDEX.sh
"""
    main_content %= (jobCount, array_script_name, array_script_name, os.path.join(script_dir, array_script_name))
    main_script_file.write(main_content)
    os.system('chmod a+rwx %s' % main_script_name)

    sub_cmd = '/usr/pbs/bin/qsub -q clng_new -J 1-%i %s' % (jobCount, main_script_name)
    print sub_cmd
    print 'array containing %i jobs' % jobCount
    #os.system(sub_cmd)

    print "* total positions: ", jobCount
