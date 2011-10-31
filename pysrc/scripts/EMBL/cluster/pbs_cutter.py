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
            plates = filter(lambda x:
                            not self.oBatchSettings.plate_regex.match(x) is None,
                            os.listdir(self.oBatchSettings.raw_image_path))

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

    # EXPERIMENTAL: SUPPORT FOR SINGLE POSITION CUTTING
    def exportPBSJobArrayNew(self):

        hours = self.oBatchSettings.hours
        minutes = self.oBatchSettings.minutes

        jobCount = 0

        plates = self.oBatchSettings.plates
        if plates is None:
            plates = filter(lambda x:
                            not self.oBatchSettings.plate_regex.match(x) is None,
                            os.listdir(self.oBatchSettings.raw_image_path))

        dctExperiments = {}
        for plate in plates:
            platedir = os.path.join(self.oBatchSettings.base_analysis_dir, 'analyzed')
            dctExperiments[plate] = filter(lambda x: os.path.isdir(os.path.join(platedir, x)),
                                           os.listdir(platedir) )

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
    bp.exportPBSJobArray()

