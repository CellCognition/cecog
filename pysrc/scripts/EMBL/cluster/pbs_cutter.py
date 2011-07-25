import os, re, time, sys
from optparse import OptionParser


from scripts.EMBL.settings import Settings

class BatchProcessor(object):
    def __init__(self, oBatchSettings):
        self.oBatchSettings = oBatchSettings
        for folder in self.oBatchSettings.lstFolders:
            if not os.path.isdir(folder):
                print 'making folder: %s' % folder
                os.makedirs(folder)

        return

    def exportPBSJobArray(self):

        hours = self.oBatchSettings.hours
        minutes = self.oBatchSettings.minutes

        jobCount = 0

        plates = self.oBatchSettings.plates
        if plates is None:
            plates = os.listdir(self.oBatchSettings.raw_image_path)

        # the path command is the first command to be executed in each single job
        # script. This is practical for setting environment variables,
        # in particular if there are several version of the same software that are
        # installed on the cluster.
        if self.oBatchSettings.path_command is None:
            path_command = ''
        else:
            path_command = self.oBatchSettings.path_command

        # head of each single job script of the array
        head = """#!/bin/bash
%s
cd %s
""" % (path_command, self.oBatchSettings.batchScriptDirectory)

        additional_options = ''
        if 'additional_attributes' in dir(self.oBatchSettings):
            for attribute, value in self.oBatchSettings.additional_attributes.iteritems():
                additional_options += ' --%s %s' % (attribute, str(value))

                # loop: job array scripts
        for plate in plates:
            jobCount += 1

            track_data_filename = os.path.join(self.oBatchSettings.track_data_dir,
                                               'track_data_%s.pickle' % plate)

            # command to be executed on the cluster
            cmd = """%s %s --plate %s --track_data_filename %s %s"""
            cmd %= (
                    self.oBatchSettings.pythonBinary,
                    self.oBatchSettings.batchScript,
                    plate,
                    track_data_filename,
                    additional_options
                    )

            # this is now written to a script file (simple text file)
            # the script file is called ltarray<x>.sh, where x is 1, 2, 3, 4, ... and corresponds to the job index.
            script_name = os.path.join(self.oBatchSettings.baseScriptDir, '%s%i.sh' % (self.oBatchSettings.scriptPrefix, jobCount))
            script_file = file(script_name, "w")
            script_file.write(head + cmd)
            script_file.close()

            # make the script executable (without this, the cluster node cannot call it)
            os.system('chmod a+x %s' % script_name)


        # write the main script
        array_script_name = '%s.sh' % os.path.join(self.oBatchSettings.baseScriptDir, self.oBatchSettings.scriptPrefix)
        main_script_file = file(array_script_name, 'w')
        main_content = """#!/bin/bash
#PBS -l walltime=%i:%02i:00
#PBS -l select=ncpus=%i:mem=%iGb
#PBS -o %s
#PBS -e %s
#PBS -J 1-%i
#PBS -q %s
#PBS -M %s
#PBS -m ae
%s$PBS_ARRAY_INDEX.sh
""" % (self.oBatchSettings.hours, self.oBatchSettings.minutes,
       self.oBatchSettings.ncpus, self.oBatchSettings.mem,
       self.oBatchSettings.pbsOutDir, self.oBatchSettings.pbsErrDir,
       jobCount,
       self.oBatchSettings.clusterName,
       self.oBatchSettings.pbsMail,
       os.path.join(self.oBatchSettings.baseScriptDir, self.oBatchSettings.scriptPrefix))

        main_script_file.write(main_content)
        os.system('chmod a+x %s' % array_script_name)

        # the submission commando is:
        sub_cmd = '/usr/pbs/bin/qsub -q %s -J1-%i %s' % (self.oBatchSettings.clusterName, jobCount, array_script_name)
        print sub_cmd
        print 'array containing %i jobs' % jobCount

        return


if __name__ ==  "__main__":

    description =\
'''
%prog - Generation of scripts as a job array for a PBS cluster.
'''

    parser = OptionParser(usage="usage: %prog [options]",
                         description=description)

    parser.add_option("-b", "--batch_configuration_filename", dest="batch_configuration_filename",
                      help="Filename of the configuration file of the"
                           "job array to be sent to the PBS-cluster")
    (options, args) = parser.parse_args()

    if (options.batch_configuration_filename is None):
        parser.error("incorrect number of arguments!")

    oSettings = Settings(os.path.abspath(options.batch_configuration_filename), dctGlobals=globals())
    bp = BatchProcessor(oSettings)
    #lstExperiments = bp.getListOfExperiments()
    #bp.exportPBSJobArray(lstExperiments)


#if __name__ ==  "__main__":
#
#    parser = OptionParser()
#    parser.add_option("-r", "--raw_image_path", dest="raw_image_path",
#                      help="raw image directory (base directory)")
#    parser.add_option("-o", "--out_path", dest="out_path",
#                      help="base output path for galleries")
#    parser.add_option("-e", "--event_path", dest="event_path",
#                      help="folder containing the track data for the detected events")
#    parser.add_option("-l", "--lt_file", dest="labtek_file",
#                      help="text file containing all labteks to be analyzed")
#    parser.add_option("-a", "--array_script_name", dest="array_script_name",
#                      help="name of the array script")
#    parser.add_option("-s", "--script_path", dest="script_path",
#                      help="path that contains the scripts")
#
#    (options, args) = parser.parse_args()
#
#    if (options.raw_image_path is None or
#        options.out_path is None or
#        options.event_path is None or
#        options.script_path is None):
#        parser.error("incorrect number of arguments!")
#
#    if options.array_script_name is None:
#        array_script_name = 'CUTTER'
#    else:
#        array_script_name = options.array_script_name
#
#    if not options.labtek_file is None:
#        file = open(options.labtek_file, 'r')
#        plates = [x.strip() for x in file.readlines()]
#        file.close()
#    else:
#        plates = os.listdir(options.raw_image_path)
#
#    base_in = options.raw_image_path
#    if not os.path.isdir(base_in):
#        raise ValueError("input path '%s' not found!\n" % base_in)
#
#    base_out = options.out_path
#    if not os.path.isdir(base_out):
#        os.makedirs(base_out)
#
#    jobCount = 0
#
#    if not os.path.exists(options.script_path):
#        os.makedirs(options.script_path)
#
#    hours=16
#    minutes=0
#
#    for plate in plates:
#        head = """#!/bin/bash
##PBS -l walltime=%02i:%02i:00
##PBS -M twalter@embl.de
##PBS -m e
##PBS -o /g/mitocheck/PBS/%s
##PBS -e /g/mitocheck/PBS/%s
#    """ % (hours, minutes, array_script_name, array_script_name)
#
#        # export LD_LIBRARY_PATH
#        cmd  = """export LD_LIBRARY_PATH=/g/software/linux/pack/libboostpython-1.46.1/lib:/g/software/linux/pack/vigra-1.7.1/lib:/g/software/linux/pack/tiff-3.8.1/lib:/g/software/linux/pack/libjpeg-8/lib:/g/software/linux/pack/libpng-1.4.5/lib:/g/software/linux/pack/fftw-3.2.2/lib:/g/software/linux/pack/hdf5-1.8.4/lib:/g/software/linux/pack/szlib-2.1/lib"""
#        cmd += """export PYTHONPATH=/g/software/linux/pack/cellcognition-1.2.2/SRC/cecog_git/pysrc"""
#
#
#        cmd = """cd /g/mitocheck/software/dev/mito_svn/trunk/projects/EMBL\n"""
#        cmd += """export PYTHONPATH=/g/mitocheck/Thomas/src:/g/mitocheck/software/bin\n"""
#
#        cmd += """python2.6 /g/mitocheck/software/dev/mito_svn/trunk/projects/EMBL/laminB_analysis_cutter.py -r "%s" -o %s -a %s -l %s -p %s -s %s -t %i""" % (options.raw_image_path,
#                                                                                                    options.out_path,
#                                                                                                    options.analysis_path,
#                                                                                                    lt_id,
#                                                                                                    pos,
#                                                                                                    options.settings_filename,
#                                                                                                    sleep_time)
#
#            # create array job files
#            jobCount += 1
#            script_name = os.path.join(script_dir, '%s%i.sh' % (array_script_name, jobCount))
#            script_file = open(script_name, "w")
#            script_file.write(head + cmd)
#            script_file.close()
#            os.system('chmod a+rwx %s' % script_name)
#
#    # create main file to be submitted to the pbs server.
#    main_script_name = os.path.join(script_dir, '%s_main.sh' % array_script_name)
#    main_script_file = open(main_script_name, 'w')
#    main_content = """#!/bin/bash
##PBS -J 1-%i
##PBS -q clng_new
##PBS -M twalter@embl.de
##PBS -m e
##PBS -o /g/mitocheck/PBS/laminB
##PBS -e /g/mitocheck/PBS/laminB
#%s/%s$PBS_ARRAY_INDEX.sh
#"""
#    main_content %= (jobCount, script_dir, array_script_name)
#    main_script_file.write(main_content)
#    main_script_file.close()
#
#    os.system('chmod a+rwx %s' % main_script_name)
#
#    sub_cmd = '/usr/pbs/bin/qsub -q clng_new -J 1-%i %s' % (jobCount, main_script_name)
#    print sub_cmd
#    print 'array containing %i jobs' % jobCount
#    #os.system(sub_cmd)
#
#    print "* total positions: ", jobCount
