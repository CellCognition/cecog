import os, re, time, sys
import math

from optparse import OptionParser

from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.traits.analyzer.classification import SECTION_NAME_CLASSIFICATION

from cecog.traits.config import ConfigSettings
from cecog.io.imagecontainer import ImageContainer

from scripts.EMBL.settings import Settings

class BatchProcessor(object):
    def __init__(self, oBatchSettings):
        self.oBatchSettings = oBatchSettings
        for folder in self.oBatchSettings.lstFolders:
            if not os.path.isdir(folder):
                print 'making folder: %s' % folder
                os.makedirs(folder)

        return

    # from a list of plate identifiers, get a dictionary of plate directories
    def getPlateDirectories(self, lstPlateId):
        lstFolders = os.listdir(self.oBatchSettings.baseInDir)
        dctPlateFolder = {}
        for plateId in lstPlateId:
            lstMatchingFolders = filter(lambda x: x.rfind(plateId) >=0, lstFolders)
            if len(lstMatchingFolders) > 1:
                raise ValueError('%s is an ambiguous identifier' % plateId)
            if len(lstMatchingFolders) < 1:
                raise ValueError('%s has no matching folder (image data not found)' % plateId)

            matchingFolder = lstMatchingFolders[0]
            dctPlateFolder[plateId] = {'inDir': os.path.join(self.oBatchSettings.baseInDir, matchingFolder),
                                       'outDir': os.path.join(self.oBatchSettings.baseOutDir, matchingFolder)
                                        }
        return dctPlateFolder

    # makes the output directories (analyzed, log, dump) for each plate.
    # This should be done before job submission to avoid simultaneous
    # attempts of directory creation by different parallel jobs.
    def makeOutputDirectories(self, lstPlateId, dctPlateFolder):
        for plateId in lstPlateId:

            print "* plate_id: '%s', dir: '%s', output: '%s'" % (plateId, dctPlateFolder[plateId]['inDir'], dctPlateFolder[plateId]['outDir'])
            if not os.path.exists(dctPlateFolder[plateId]['outDir']):
                outDir = dctPlateFolder[plateId]['outDir']
                os.makedirs(outDir)
                for subdir in ['analyzed', 'qc', 'log', 'dump']:
                    path = os.path.join(outDir, subdir)
                    if not os.path.exists(path):
                        print 'making output path: %s' % path
                        os.makedirs(path)

        return

    def writeRenderingSettingsToConfigFile(self, filename_settings=None,
                                           mod_filename=None):

        if filename_settings is None:
            filename_settings = self.oBatchSettings.settingsFilename

        if mod_filename is None:
            mod_filename = os.path.join(os.path.dirname(filename_settings),
                                        'mod_%s' % os.path.basename(filename_settings))

        settings = ConfigSettings(SECTION_REGISTRY)
        settings.read(filename_settings)

        settings.set_section(SECTION_NAME_GENERAL)
        settings.set2('rendering_class', self.oBatchSettings.rendering_class)
        settings.set2('rendering', self.oBatchSettings.rendering)

        oFile = open(mod_filename, 'w')
        settings.write(oFile)
        oFile.close()

        return


    def writePathSettingsToConfigFile(self, filename_settings=None,
                                      mod_filename=None):
        if filename_settings is None:
            filename_settings = self.oBatchSettings.settingsFilename

        if mod_filename is None:
            mod_filename = os.path.join(os.path.dirname(filename_settings),
                                        'mod_%s' % os.path.basename(filename_settings))

        settings = ConfigSettings(SECTION_REGISTRY)
        settings.read(filename_settings)

        settings.set_section(SECTION_NAME_ERRORCORRECTION)
        if 'filename_to_r' in dir(self.oBatchSettings) and not self.oBatchSettings.filename_to_r is None:
            settings.set2('filename_to_r', self.oBatchSettings.filename_to_r)
        if 'primary_graph' in dir(self.oBatchSettings) and not self.oBatchSettings.primary_graph is None:
            settings.set2('primary_graph', self.oBatchSettings.primary_graph)
        if 'secondary_graph' in dir(self.oBatchSettings) and not self.oBatchSettings.secondary_graph is None:
            settings.set2('secondary_graph', self.oBatchSettings.secondary_graph)

        settings.set_section(SECTION_NAME_CLASSIFICATION)
        if 'primary_classification_envpath' in dir(self.oBatchSettings) and not self.oBatchSettings.primary_classification_envpath is None:
            settings.set2('primary_classification_envpath',
                          self.oBatchSettings.primary_classification_envpath)
        if 'secondary_classification_envpath' in dir(self.oBatchSettings) and not self.oBatchSettings.secondary_classification_envpath is None:
            settings.set2('secondary_classification_envpath',
                          self.oBatchSettings.secondary_classification_envpath)

        #SECTION_NAME_CLASSIFICATION
        oFile = open(mod_filename, 'w')
        settings.write(oFile)
        oFile.close()

        return

    def exportPBSJobArray(self, lstExperiments):

        filename_settings = self.oBatchSettings.settingsFilename

        mod_filename = os.path.join(os.path.dirname(filename_settings),
                                    'mod_%s' % os.path.basename(filename_settings))

        self.writeRenderingSettingsToConfigFile(filename_settings, mod_filename)
        self.writePathSettingsToConfigFile(mod_filename, mod_filename)

        hours = self.oBatchSettings.hours
        minutes = self.oBatchSettings.minutes

        jobCount = 0
        jobSize = self.oBatchSettings.jobSize
        nb_jobs = int(math.ceil(len(lstExperiments)/float(jobSize)))

        # get the list of plates from the tuple list [(plate, pos), (plate, pos), ...]
        lstPlates = list(set([x[0] for x in lstExperiments]))
        dctPlateFolder = self.getPlateDirectories(lstPlates)

        # the folders are made at this level in oder to avoid conflicts between parallel jobs.
        self.makeOutputDirectories(lstPlates, dctPlateFolder)

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
        for attribute in self.oBatchSettings.additional_flags:
            additional_options += ' --%s' % attribute
        for attribute, value in self.oBatchSettings.additional_attributes.iteritems():
            additional_options += ' --%s %s' % (attribute, str(value))

        # loop: job array scripts
        for i in range(nb_jobs):
            jobCount += 1
            cmd = ''
            lstJobPositions = [lstExperiments[k] for k in range(i*jobSize, min(len(lstExperiments), (i+1)*jobSize))]

            for plate, pos in lstJobPositions:

                # command to be executed on the cluster
                temp_cmd = """
%s %s -s %s -i "%s" -o "%s" --position_list %s %s"""

                temp_cmd %= (
                        self.oBatchSettings.pythonBinary,
                        self.oBatchSettings.batchScript,
                        #self.oBatchSettings.settingsFilename,
                        mod_filename,
                        self.oBatchSettings.baseInDir,
                        self.oBatchSettings.baseOutDir,
                        '___'.join([plate, pos]),
                        additional_options)

                cmd += temp_cmd

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
        
        # modification for the CBIO cluster : 
        # FIX ME: removed: #PBS -q %s (for clustername) 

        main_content = """#!/bin/bash
#PBS -l walltime=%i:%02i:00
#PBS -l select=ncpus=%i:mem=%iGb
#PBS -o %s
#PBS -e %s
#PBS -%s 1-%i
#PBS -M %s
#PBS -m ae
%s$PBS_ARRAY_INDEX.sh
""" % (self.oBatchSettings.hours, self.oBatchSettings.minutes,
       self.oBatchSettings.ncpus, self.oBatchSettings.mem,
       self.oBatchSettings.pbsOutDir, self.oBatchSettings.pbsErrDir,
       self.oBatchSettings.jobArrayOption, jobCount,
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

    def exportPBSJobArray_position_based(self, lstExperiments):

        hours = self.oBatchSettings.hours
        minutes = self.oBatchSettings.minutes

        jobCount = 0
        jobSize = self.oBatchSettings.jobSize
        nb_jobs = int(math.ceil(len(lstExperiments)/float(jobSize)))

        # get the list of plates from the tuple list [(plate, pos), (plate, pos), ...]
        lstPlates = list(set([x[0] for x in lstExperiments]))
        dctPlateFolder = self.getPlateDirectories(lstPlates)

        # the folders are made at this level in oder to avoid conflicts between parallel jobs.
        self.makeOutputDirectories(lstPlates, dctPlateFolder)

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
        for attribute, value in self.oBatchSettings.additional_attributes.iteritems():
            additional_options += ' --%s %s' % (attribute, str(value))

        # loop: job array scripts
        for i in range(nb_jobs):
            jobCount += 1
            cmd = ''
            lstJobPositions = [lstExperiments[k] for k in range(i*jobSize, min(len(lstExperiments), (i+1)*jobSize))]

            for plate, pos in lstJobPositions:

                # command to be executed on the cluster
                temp_cmd = """
%s %s -s %s -i %s -o %s --position_list %s %s"""

                temp_cmd %= (
                        self.oBatchSettings.pythonBinary,
                        self.oBatchSettings.batchScript,
                        self.oBatchSettings.settingsFilename,
                        self.oBatchSettings.baseInDir,
                        self.oBatchSettings.baseOutDir,
                        '___'.join([plate, pos]),
                        additional_options)

                cmd += temp_cmd

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

    #def getFinishedJobs(self, i):
    #    finished_pos = os.listdir(os.path.join(self.oBatchSettings.baseOutDir, plate, 'log', '_finished'))
    #    return

    def getListOfExperiments(self):
        settings = ConfigSettings(SECTION_REGISTRY)
        settings.read(self.oBatchSettings.settingsFilename)

        settings.set_section(SECTION_NAME_GENERAL)
        settings.set2('pathin', self.oBatchSettings.baseInDir)
        settings.set2('pathout', self.oBatchSettings.baseOutDir)

        imagecontainer = ImageContainer()
        imagecontainer.import_from_settings(settings)

        if self.oBatchSettings.plates is None:
            plates = imagecontainer.plates
        else:
            plates = self.oBatchSettings.plates

        lstExperiments = []
        for plate in plates:
            imagecontainer.set_plate(plate)
            meta_data = imagecontainer.get_meta_data()
            positions = meta_data.positions

            if self.oBatchSettings.omit_processed_positions:
                if os.path.exists(os.path.join(self.oBatchSettings.baseOutDir,
                                               plate, 'log', '_finished')):
                    finished_pos = [os.path.splitext(x)[0].split('__')[0] for x in
                                    os.listdir(os.path.join(self.oBatchSettings.baseOutDir,
                                                            plate, 'log', '_finished'))]
                    positions = filter(lambda x: x not in finished_pos, positions)

            lstExperiments.extend([(x,y) for x,y in zip([plate for i in positions],
                                                        positions) ])

        return lstExperiments




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
    lstExperiments = bp.getListOfExperiments()
    bp.exportPBSJobArray(lstExperiments)

