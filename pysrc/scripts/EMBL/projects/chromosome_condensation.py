import os, sys, time, re, shutil

import scripts.EMBL.io.flatfileimporter

import scripts.EMBL.plotter.feature_timeseries_plotter
reload(scripts.EMBL.plotter.feature_timeseries_plotter)

from scripts.EMBL.plotter.feature_timeseries_plotter import TimeseriesPlotter
from scripts.EMBL.settings import Settings

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc
# if rpy2 is going to be used: export PATH=/Users/twalter/software/R/R.framework/Resources/bin:${PATH}
# This is necessary, because without that he finds the wrong R executable.

# works with the settings file scripts.EMBL/settings_files/chromosome_condensation_postprocessing.py
class FullAnalysis(object):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())

    def copyResultData(self, inDir, outDir, plates=None):
        #targetDir = '/Users/twalter/data/JKH/cecog_output'
        #inDir = '/Volumes/mitocheck/Thomas/data/JKH/cecog_output'
        #/Volumes/mitocheck/Thomas/data/JKH/cecog_output/plate1_1_013/analyzed/00001/statistics
        for plate in plates:
            plateDir = os.path.join(inDir, plate, 'analyzed')
            positions = filter(lambda x: os.path.isdir(os.path.join(plateDir, x)),
                               os.listdir(plateDir))
            for pos in positions:
                print 'copying:', plate, pos
                tempInDir = os.path.join(plateDir, pos, 'statistics')
                tempOutDir = os.path.join(outDir, plate, 'analyzed', pos)
                if not os.path.exists(tempOutDir):
                    os.makedirs(tempOutDir)
                shutil.copytree(tempInDir, os.path.join(tempOutDir, 'statistics'))
        return

    def importEventData(self, plates=None):
        event_importer = scripts.EMBL.io.flatfileimporter.EventDescriptionImporter(settings=self.settings)
        impdata = event_importer(plates=plates)
        return impdata

    def dumpPlateEventData(self, impdata, plate):
        filename = os.path.join(self.settings.track_data_dir,
                                'track_data_%s.pickle' % plate)
        track_file = open(filename, 'w')
        pickle.dump(impdata, track_file)
        track_file.close()
        return

    def importAndDumpEventData(self, plates=None):
        if plates is None:
            plates = filter(lambda x: os.path.isdir(x),
                            os.listdir(os.path.join(self.settings.base_analysis_dir,
                                                    'analyzed')))

        for plate in plates:
            starttime = time.time()
            print
            print 'importing %s' % plate
            impdata = self.importEventData([plate])
            self.dumpPlateEventData(impdata, plate)
            diffTime = time.time() - startTime
            print 'elapsed time: %02i:%02i:%02i' % ((diffTime/3600),
                                                    ((diffTime%3600)/60),
                                                    (diffTime%60))
        return

    def makeSingleCellPlots(self, impdata, feature, classification=True,
                            plates=None, wells=None, tracks=None,
                            channels=None, regions=None):
        if plates is None:
            plates = impdata.keys()
        if channels is None:
            channels = ['primary']
        if regions is None:
            regions = ['primary']

        plotter = TimeseriesPlotter()

        #for plate in plates:
        for plate in plates:
            if wells is None:
                wells = sorted(impdata[plate].keys())
            for well in wells:
                if tracks is None:
                    tracks = sorted(impdata[plate][well].keys())

                out_path = os.path.join(self.settings.singleCellPlotDir,
                                        plate, well)
                if not os.path.exists(out_path):
                    os.makedirs(out_path)

                for track in tracks:
                    timevec = impdata[plate][well][track]['Frame']

                    for channel in channels:
                        if regions is None:
                            regions = impdata[plate][well][track][channel].keys()
                        for region in regions:
                            classvec = impdata[plate][well][track][channel][region]['class__name']
                            colorvec = [self.settings.class_color_code[x] for x in classvec]
                            datavec = impdata[plate][well][track][channel][region][feature]
                            filename = os.path.join(out_path,
                                                    'singlecell_%s.png' % \
                                                    '_'.join([plate, well, track,
                                                              channel, region,
                                                              feature] ))
                            title = ' '.join([plate, well, track,
                                              channel, region, feature.split('__')[-1]])
                            plotter.makeSingleTimeseriesPlot(timevec,
                                                             datavec,
                                                             filename,
                                                             title=title,
                                                             xlabel='Time (Frames)',
                                                             ylabel=feature,
                                                             color='#0000ff',
                                                             colorvec=colorvec)

        return
