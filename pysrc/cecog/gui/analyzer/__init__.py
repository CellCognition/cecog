"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['REGION_NAMES_PRIMARY',
           'REGION_NAMES_SECONDARY',
           'SECONDARY_COLORS',
           'ZSLICE_PROJECTION_METHODS',
           'COMPRESSION_FORMATS',
           'TRACKING_METHODS',
           'R_LIBRARIES',
           '_BaseFrame',
           '_ProcessorMixin',
           'callit']

#-------------------------------------------------------------------------------
# standard library imports:
#
import types, \
       traceback, \
       logging, \
       sys, \
       os, \
       time, \
       copy, \
       SocketServer, \
       cPickle as pickle, \
       struct, \
       threading, \
       socket
       

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.ordereddict import OrderedDict
from pdk.datetimeutils import TimeInterval, StopWatch
from pdk.fileutils import safe_mkdirs

from multiprocessing import Pool, Queue, cpu_count

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.display import TraitDisplayMixin
from cecog.learning.learning import (CommonObjectLearner,
                                     CommonClassPredictor,
                                     ConfusionMatrix,
                                     )
from cecog.util.util import (hexToRgb,
                             write_table,
                             convert_package_path,
                             PACKAGE_PATH,
                             )
from cecog.gui.util import (ImageRatioDisplay,
                            numpy_to_qimage,
                            question,
                            critical,
                            information,
                            status,
                            waitingProgressDialog,
                            )
from cecog.analyzer import (CONTROL_1,
                            CONTROL_2,
                            )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer.core import AnalyzerCore, SECONDARY_REGIONS
from cecog.io.imagecontainer import PIXEL_TYPES
from cecog.traits.config import R_SOURCE_PATH
from cecog import ccore
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.analyzer.gallery import compose_galleries
from cecog.traits.config import ConfigSettings
from cecog.traits.analyzer import SECTION_REGISTRY

#-------------------------------------------------------------------------------
# functions:
#


# see http://stackoverflow.com/questions/3288595/multiprocessing-using-pool-map-on-a-function-defined-in-a-class
def AnalyzerCoreHelper(plate_id, settings_str, imagecontainer, position):
    print ' analyzing plate', plate_id, 'and position', position, 'in process', os.getpid()
    settings = ConfigSettings(SECTION_REGISTRY)
    settings.from_string(settings_str)
    
    settings.set(SECTION_NAME_GENERAL, 'constrain_positions', True)
    settings.set(SECTION_NAME_GENERAL, 'positions', position)
    analyzer = AnalyzerCore(plate_id, settings,imagecontainer)         
    analyzer.processPositions()
    
    return plate_id, position

def process_initialyzer(port):
    oLogger = logging.getLogger(str(os.getpid()))
    oLogger.setLevel(logging.NOTSET)
    socketHandler = logging.handlers.SocketHandler('localhost', port)
    socketHandler.setLevel(logging.NOTSET)
    oLogger.addHandler(socketHandler)
    oLogger.info('logger init')

#-------------------------------------------------------------------------------
# classes:
#

class BaseFrame(QFrame, TraitDisplayMixin):

    ICON = ":cecog_analyzer_icon"
    TABS = None
    CONTROL = CONTROL_1

    toggle_tabs = pyqtSignal(str)

    def __init__(self, settings, parent):
        QFrame.__init__(self, parent)
        self._tab_lookup = {}
        self._tab_name = None
        self._is_active = False

        self._control = QFrame(self)
        layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        if not self.TABS is None:
            self._tab = QTabWidget(self)
            #self._tab.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
            #                                    QSizePolicy.Expanding))
            for name in self.TABS:
                frame = QFrame(self._tab)
                frame._input_cnt = 0
                QGridLayout(frame)
                idx = self._tab.addTab(frame, name)
                self._tab_lookup[name] = (idx, frame)
            scroll_area.setWidget(self._tab)
            #layout.addWidget(self._tab)
            self._tab.currentChanged.connect(self.on_tab_changed)
        else:
            self._frame = QFrame(self)
            self._frame._input_cnt = 0
            QGridLayout(self._frame)
            #self._frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
            #                                    QSizePolicy.Expanding))
            scroll_area.setWidget(self._frame)
            #layout.addWidget(self._frame)

        layout.addWidget(scroll_area)
        layout.addWidget(self._control)

        TraitDisplayMixin.__init__(self, settings)

    @pyqtSlot('int')
    def on_tab_changed(self, index):
        self.tab_changed(index)

    def set_tab_name(self, name):
        self._tab_name = name

    def set_active(self, state=True):
        self._is_active = state

    def _get_frame(self, name=None):
        if name is None:
            if len(self._tab_lookup) > 0:
                frame = self._tab_lookup[self._tab_name][1]
            else:
                frame = self._frame
        else:
            frame = self._tab_lookup[name][1]
        return frame

    def add_expanding_spacer(self):
        frame = self._get_frame(name=self._tab_name)
        dummy = QWidget(frame)
        dummy.setMinimumSize(0,0)
        dummy.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                        QSizePolicy.Expanding))
        frame.layout().addWidget(dummy, frame._input_cnt, 0)
        frame._input_cnt += 1
#        self._layout.addItem(QSpacerItem(0, 0,
#                                         QSizePolicy.Fixed,
#                                         QSizePolicy.Expanding),
#                             self._input_cnt, 0, 1, self.WIDTH+2)


    def add_line(self):
        frame = self._get_frame(name=self._tab_name)
        line = QFrame(frame)
        line.setFrameShape(QFrame.HLine)
        frame.layout().addWidget(line, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1

    def add_pixmap(self, pixmap, align=Qt.AlignLeft):
        frame = self._get_frame(name=self._tab_name)
        label = QLabel(frame)
        label.setPixmap(pixmap)
        frame.layout().addWidget(label, frame._input_cnt, 0, 1, 2, align)
        frame._input_cnt += 1

    def page_changed(self):
        '''
        Abstract method. Invoked by the AnalyzerMainWindow when this frame
        is activated for display.
        '''
        pass

    def tab_changed(self, index):
        pass



class _ProcessingThread(QThread):

    stage_info = pyqtSignal(dict)
    analyzer_error = pyqtSignal(str)

    def __init__(self, parent, settings):
        QThread.__init__(self, parent)
        self._settings = settings
        self._abort = False
        self._mutex = QMutex()
        self._stage_info = {'text': '',
                            'progress': 0,
                            'max': 0,
                            }
        self.parent = parent

    def __del__(self):
        #self._mutex.lock()
        self._abort = True
        self._mutex.unlock()
        self.stop()
        self.wait()

    def run(self):
        try:
            self._run()
        except MultiprocessingException, e:
            msg = e.msg
            logger = logging.getLogger()
            logger.error(msg)
            self.analyzer_error.emit(msg)
            raise
        except:
            msg = traceback.format_exc()
            logger = logging.getLogger()
            logger.error(msg)
            self.analyzer_error.emit(msg)
            raise

    def set_abort(self, wait=False):
        self._mutex.lock()
        self._abort = True
        self._mutex.unlock()
        if wait:
            self.wait()

    def get_abort(self):
        abort = self._abort
        return abort

    def set_stage_info(self, info):
        self._mutex.lock()
        self.stage_info.emit(info)
        self._mutex.unlock()



class HmmThread(_ProcessingThread):

    DEFAULT_CMD_MAC = 'R32'
    DEFAULT_CMD_WIN = r'C:\Program Files\R\R-2.10.0\bin\R.exe'

    def __init__(self, parent, settings, learner_dict, imagecontainer):
        _ProcessingThread.__init__(self, parent, settings)
        self._learner_dict = learner_dict
        self._imagecontainer = imagecontainer
        self._mapping_files = {}

        # R on windows works better with '/' then '\'
        self._convert = lambda x: x.replace('\\','/')
        self._join = lambda *x: self._convert('/'.join(x))

        self._logger = logging.getLogger(self.__class__.__name__)

        qApp._log_window.show()
        qApp._log_window.raise_()

    @classmethod
    def get_cmd(cls, filename):
        filename = filename.strip()
        if filename != '':
            cmd = filename
        elif sys.platform == 'darwin':
            cmd = cls.DEFAULT_CMD_MAC
        else:
            cmd = cls.DEFAULT_CMD_WIN
        return cmd

    @classmethod
    def test_executable(cls, filename):
        cmd = cls.get_cmd(filename)
        process = QProcess()
        process.start(cmd, ['--version'])
        success = process.waitForFinished()
        return success and process.exitCode() == QProcess.NormalExit, cmd

    def _run(self):
        plates = self._imagecontainer.plates
        self._settings.set_section(SECTION_NAME_ERRORCORRECTION)

        # mapping files (mapping between plate well/position and experimental condition) can be defined by a directory
        # which must contain all mapping files for all plates in the form <plate_id>.txt or .tsv
        # if the option 'position_labels' is not enabled a dummy mapping file is generated
        if self._settings.get2('position_labels'):
            path_mapping = self._convert(self._settings.get2('mappingfile_path'))
            for plate_id in plates:
                mapping_file = os.path.join(path_mapping, '%s.tsv' % plate_id)
                if not os.path.isfile(mapping_file):
                    mapping_file = os.path.join(path_mapping, '%s.txt' % plate_id)
                    if not os.path.isfile(mapping_file):
                        raise IOError("Mapping file '%s' for plate '%s' not found." %
                                      (mapping_file, plate_id))
                self._mapping_files[plate_id] = os.path.abspath(mapping_file)

        info = {'min' : 0,
                'max' : len(plates),
                'stage': 0,
                'meta': 'Error correction...',
                'progress': 0}
        for idx, plate_id in enumerate(plates):
            if not self._abort:
                info['text'] = "Plate: '%s' (%d / %d)" % (plate_id, idx+1, len(plates))
                self.set_stage_info(info)
                self._imagecontainer.set_plate(plate_id)
                self._run_plate(plate_id)
                info['progress'] = idx+1
                self.set_stage_info(info)
            else:
                break

    def _run_plate(self, plate_id):
        filename = self._settings.get2('filename_to_R')
        cmd = self.get_cmd(filename)

        path_out = self._imagecontainer.get_path_out()

        wd = os.path.abspath(os.path.join(R_SOURCE_PATH, 'hmm'))
        f = file(os.path.join(wd, 'run_hmm.R'), 'r')
        lines = f.readlines()
        f.close()

        path_analyzed = self._join(path_out, 'analyzed')
        path_out_hmm = self._join(path_out, 'hmm')

        # don't do anything if the 'hmm' folder already exists and the skip-option is on
        if os.path.isdir(path_out_hmm) and self._settings.get2('skip_processed_plates'):
            return

        safe_mkdirs(path_out_hmm)

        region_name_primary = self._settings.get('Classification', 'primary_classification_regionname')
        region_name_secondary = self._settings.get('Classification', 'secondary_classification_regionname')

        path_out_hmm_region = self._convert(self._get_path_out(path_out_hmm,
                                                               '%s_%s' % ('primary', region_name_primary)))

        # take mapping file for plate or generate dummy mapping file for the R script
        if plate_id in self._mapping_files:
            # convert path for R
            mapping_file = self._convert(self._mapping_files[plate_id])
        else:
            mapping_file = self._generate_mapping(wd, path_out_hmm, path_analyzed)

        if self._settings.get2('overwrite_time_lapse'):
            time_lapse = self._settings.get2('timelapse')
        else:
            meta_data = self._imagecontainer.get_meta_data()
            if meta_data.has_timestamp_info:
                time_lapse = meta_data.plate_timestamp_info[0] / 60.
            else:
                raise ValueError("Plate '%s' has not time-lapse info.\n"
                                 "Please define (overwrite) the value manually." % plate_id)

        if self._settings.get2('compose_galleries'):# and self._settings.get('Output', 'events_export_gallery_images'):
            gallery_names = ['primary'] +\
                            [x for x in ['secondary','tertiary']
                             if self._settings.get('Processing', '%s_processchannel' % x)]
        else:
            gallery_names = None


        for i in range(len(lines)):
            line2 = lines[i].strip()
            if line2 == '#WORKING_DIR':
                lines[i] = "WORKING_DIR = '%s'\n" % self._convert(wd)
            elif line2 == '#FILENAME_MAPPING':
                lines[i] = "FILENAME_MAPPING = '%s'\n" % mapping_file
            elif line2 == '#PATH_INPUT':
                lines[i] = "PATH_INPUT = '%s'\n" % path_analyzed
            elif line2 == '#GROUP_BY_GENE':
                lines[i] = "GROUP_BY_GENE = %s\n" % str(self._settings.get2('groupby_genesymbol')).upper()
            elif line2 == '#GROUP_BY_OLIGOID':
                lines[i] = "GROUP_BY_OLIGOID = %s\n" % str(self._settings.get2('groupby_oligoid')).upper()
            elif line2 == '#TIMELAPSE':
                lines[i] = "TIMELAPSE = %s\n" % time_lapse
            elif line2 == '#MAX_TIME':
                lines[i] = "MAX_TIME = %s\n" % self._settings.get2('max_time')
            elif line2 == '#SINGLE_BRANCH':
                lines[i] = "SINGLE_BRANCH = %s\n" % str(self._settings.get2('ignore_tracking_branches')).upper()
            elif line2 == '#GALLERIES':
                if gallery_names is None:
                    lines[i] = "GALLERIES = NULL\n"
                else:
                    lines[i] = "GALLERIES = c(%s)\n" % ','.join(["'%s'" % x for x in gallery_names])

            if 'primary' in self._learner_dict:# and self._settings.get('Processing', 'primary_errorcorrection'):

                if self._settings.get2('constrain_graph'):
                    primary_graph = self._convert(self._settings.get2('primary_graph'))
                else:
                    primary_graph = self._generate_graph('primary', wd, path_out_hmm, region_name_primary)

                if line2 == '#FILENAME_GRAPH_P':
                    lines[i] = "FILENAME_GRAPH_P = '%s'\n" % primary_graph
                elif line2 == '#CLASS_COLORS_P':
                    learner = self._learner_dict['primary']
                    colors = ",".join(["'%s'" % learner.dctHexColors[x] for x in learner.lstClassNames])
                    lines[i] = "CLASS_COLORS_P = c(%s)\n" % colors
                elif line2 == '#REGION_NAME_P':
                    lines[i] = "REGION_NAME_P = '%s'\n" % region_name_primary
                elif line2 == '#SORT_CLASSES_P':
                    if self._settings.get2('enable_sorting'):
                        lines[i] = "SORT_CLASSES_P = c(%s)\n" % self._settings.get2('sorting_sequence')
                    else:
                        lines[i] = "SORT_CLASSES_P = NULL\n"
                elif line2 == "#PATH_OUT_P":
                    lines[i] = "PATH_OUT_P = '%s'\n" % path_out_hmm_region



            if 'secondary' in self._learner_dict:# and self._settings.get('Processing', 'secondary_errorcorrection'):
                if self._settings.get2('constrain_graph'):
                    secondary_graph = self._convert(self._settings.get2('secondary_graph'))
                else:
                    secondary_graph = self._generate_graph('secondary', wd, path_out_hmm, region_name_secondary)

                if line2 == '#FILENAME_GRAPH_S':
                    lines[i] = "FILENAME_GRAPH_S = '%s'\n" % secondary_graph
                elif line2 == '#CLASS_COLORS_S':
                    learner = self._learner_dict['secondary']
                    colors = ",".join(["'%s'" % learner.dctHexColors[x] for x in learner.lstClassNames])
                    lines[i] = "CLASS_COLORS_S = c(%s)\n" % colors
                elif line2 == '#REGION_NAME_S':
                    lines[i] = "REGION_NAME_S = '%s'\n" % region_name_secondary
                elif line2 == '#SORT_CLASSES_S':
                    secondary_sort = self._settings.get2('secondary_sort')
                    if secondary_sort == '':
                        lines[i] = "SORT_CLASSES_S = NULL\n"
                    else:
                        lines[i] = "SORT_CLASSES_S = c(%s)\n" % secondary_sort
                elif line2 == "#PATH_OUT_S":
                    lines[i] = "PATH_OUT_S = '%s'\n" % \
                        self._convert(self._get_path_out(path_out_hmm, '%s_%s' % ('secondary', region_name_secondary)))

        input_filename = os.path.join(path_out_hmm, 'cecog_hmm_input.R')
        f = file(input_filename, 'w')
        f.writelines(lines)
        f.close()

        process = QProcess()
        self._process = process
        process.setWorkingDirectory(wd)
        process.start(cmd, ['BATCH', '--silent', '-f', input_filename])
        process.readyReadStandardOutput.connect(self._on_stdout)
        process.waitForFinished(-1)

        if process.exitCode() != 0:
            process.setReadChannel(QProcess.StandardError)
            msg = str(process.readLine()).rstrip()
            msg = ''.join(list(process.readAll()))
            self.analyzer_error.emit(msg)
            self.set_abort()

        elif self._settings.get2('compose_galleries') and not self._abort:
            sample = self._settings.get2('compose_galleries_sample')
            if sample == -1:
                sample = None
            for group_name in compose_galleries(path_out, path_out_hmm_region, one_daughter=False, sample=sample):
                self._logger.debug('gallery finished for group: %s' % group_name)
                if self._abort:
                    break

        if self._settings.get2('show_html'):
            QDesktopServices.openUrl(QUrl('file://'+os.path.join(path_out_hmm_region, 'index.html'), QUrl.TolerantMode))


    def _generate_graph(self, channel, wd, hmm_path, region_name):
        f_in = file(os.path.join(wd, 'graph_template.txt'), 'rU')
        filename_out = self._join(hmm_path, 'graph_%s.txt' % region_name)
        f_out = file(filename_out, 'w')
        learner = self._learner_dict[channel]
        for line in f_in:
            line2 = line.strip()
            if line2 in ['#numberOfClasses', '#numberOfHiddenStates']:
                f_out.write('%d\n' % len(learner.lstClassNames))
            elif line2 == '#startNodes':
                f_out.write('%s\n' % '  '.join(map(str, learner.lstClassLabels)))
            elif line2 == '#transitionGraph':
                f_out.write('%s -> %s\n' %
                            (','.join(map(str, learner.lstClassLabels)),
                             ','.join(map(str, learner.lstClassLabels))))
            elif line2 == '#hiddenNodeToClassificationNode':
                for label in learner.lstClassLabels:
                    f_out.write('%s\n' % '  '.join(map(str, [label]*2)))
            else:
                f_out.write(line)
        f_in.close()
        f_out.close()
        return filename_out

    def _generate_mapping(self, wd, hmm_path, path_analyzed):
        filename_out = self._join(hmm_path, 'layout.txt')
        rows = []
        positions = None
        if self._settings.get('General', 'constrain_positions'):
            positions = self._settings.get('General', 'positions')
        if positions is None or positions == '':
            positions = [x for x in os.listdir(path_analyzed)
                         if os.path.isdir(os.path.join(path_analyzed, x)) and
                         x[0] != '_']
        else:
            positions = positions.split(',')
        for pos in positions:
            rows.append({'Position': pos, 'OligoID':'', 'GeneSymbol':'', 'Group':''})
        header_names = ['Position', 'OligoID', 'GeneSymbol', 'Group']
        write_table(filename_out, rows, column_names=header_names, sep='\t')
        return filename_out

    def _on_stdout(self):
        self._process.setReadChannel(QProcess.StandardOutput)
        msg = str(self._process.readLine()).rstrip()
        self._logger.info(msg)

    def _get_path_out(self, path, prefix):
        if self._settings.get2('groupby_oligoid'):
            suffix = 'byoligo'
        elif self._settings.get2('groupby_genesymbol'):
            suffix = 'bysymbol'
        else:
            suffix = 'bypos'
        path_out = os.path.join(path, '%s_%s' % (prefix, suffix))
        safe_mkdirs(path_out)
        return path_out

    def set_abort(self, wait=False):
        self._process.kill()
        _ProcessingThread.set_abort(self, wait=wait)
        
        

        
class ParallelProcessThreadMixinBase(object):
    class ProcessCallback(object):
        def __init__(self):
            pass
        def __call__(self):
            pass
    def setup(self):
        pass
    
    def finish(self):
        pass
    
    def abort(self):
        pass
    
    @property
    def target(self):
        pass
    
    def submit_jobs(self, job_list):
        pass
    
class MultiProcessingAnalyzerMixin(ParallelProcessThreadMixinBase):
    class ProcessCallback(object):
        def __init__(self, parent):
            self.cnt = 0
            self.parent = parent
            self.job_count = None
            self._timer = StopWatch()
            
            
        def notify_execution(self, job_list):
            self.job_count = len(job_list)
            stage_info = {'stage': 0,
                      'progress': 0,
                      'text': '',
                      'meta': 'Parallel processing %d / %d positions (%d cores)' % (0, self.job_count, cpu_count()),
                      'min': 0,
                      'max': self.job_count,
                       }
            self.parent.set_stage_info(stage_info)
            
        def __call__(self, args):
            print 'args', args
            plate, pos = args
            self.cnt += 1
            stage_info = {'progress': self.cnt,
                          'meta': 'Parallel processing %d / %d positions (%d cores)' % (self.cnt, 
                                                                                        self.job_count, 
                                                                                        cpu_count()),
                          'text': 'finished %s - %s' % (str(plate), str(pos)),
                          'stage': 0,
                          'min': 0,
                          'item_name': 'position',
                          'interval': self._timer.current_interval(),
                          'max': self.job_count,
                          }
            self.parent.set_stage_info(stage_info)
            self._timer.reset()  
            
    def setup(self):
        self.log_receiver = LoggingReceiver(port=0)
        port = self.log_receiver.server_address[1]
        self.pool = Pool(cpu_count(), initializer=process_initialyzer, initargs=(port,))
        self.parent.process_log_window.init_process_list([str(p.pid) for p in self.pool._pool])
        self.parent.process_log_window.show()
        
        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        
        for p in self.pool._pool:
            logger = logging.getLogger(str(p.pid))
            handler = NicePidHandler(self.parent.process_log_window)
            handler.setFormatter(logging.Formatter('%(asctime)s %(name)-24s %(levelname)-6s %(message)s'))
            logger.addHandler(handler)
        
        self.log_receiver.handler.log_window = self.parent.process_log_window
               
        self.log_receiver_thread = threading.Thread(target=self.log_receiver.serve_forever)
        self.log_receiver_thread.start()
        
        self.process_callback = self.ProcessCallback(self)
        
    def finish(self):
        self.log_receiver.shutdown()
        self.log_receiver.server_close()        
        self.log_receiver_thread.join()
        
        
    def abort(self):
        self._abort = True
        self.pool.terminate()
        self.parent.process_log_window.close()
        
    def join(self):
        self.pool.close()
        self.pool.join()
        if not self._abort:
            exception_list = []
            for r in self.job_result:
                if not r.successful():
                    try:
                        r.get()
                    except Exception, e:
                        exception_list.append(e)
            if len(exception_list) > 0:
                multi_exception = MultiprocessingException(exception_list)
                raise multi_exception
                        
        self.finish()
        
    
    @property
    def target(self):
        return AnalyzerCoreHelper
    
    def submit_jobs(self, job_list):
        self.process_callback.notify_execution(job_list)
        self.job_result = [self.pool.apply_async(self.target, args, callback=self.process_callback) for args in job_list]
        
class MultiprocessingException(Exception):
    def __init__(self, exception_list):
        self.msg = '\n-----------\nError in job item:\n'.join([str(x) for x in exception_list])

class AnalzyerThread(_ProcessingThread, MultiProcessingAnalyzerMixin):
    image_ready = pyqtSignal(ccore.RGBImage, str, str)
    def __init__(self, parent, settings, imagecontainer):
        _ProcessingThread.__init__(self, parent, settings)
        self._renderer = None
        self._imagecontainer = imagecontainer
        self._buffer = {}
        self.setup()
        self._abort = False
        
    def set_abort(self, wait=False):
        self._abort = True
        self.abort()
        if wait:
            self.wait()

    def _run(self):
        self._abort = False
        settings_str = self._settings.to_string()
        job_list = []
        for plate_id in self._imagecontainer.plates:
            self._imagecontainer.set_plate(plate_id)
            meta_data = self._imagecontainer.get_meta_data()
            for pos_id in meta_data.positions:
                job_list.append((plate_id, settings_str, self._imagecontainer, pos_id))
        self.submit_jobs(job_list)
        self.join()

    def set_renderer(self, name):
        self._mutex.lock()
        self._renderer = name
        self._emit(name)
        self._mutex.unlock()

    def get_renderer(self):
        return self._renderer

    def set_image(self, name, image_rgb, info, filename=''):
        self._mutex.lock()
        self._buffer[name] = (image_rgb, info, filename)
        if name == self._renderer:
            self._emit(name)
        self._mutex.unlock()

    def _emit(self, name):
        if name in self._buffer:
            self.image_ready.emit(*self._buffer[name])




class TrainingThread(_ProcessingThread):

    conf_result = pyqtSignal(float, float, ConfusionMatrix)

    def __init__(self, parent, settings, learner):
        _ProcessingThread.__init__(self, parent, settings)
        self._learner = learner

    def _run(self):
        #print "training"

        # log2 settings (range and step size) for C and gamma
        c_begin, c_end, c_step = -5,  15, 2
        c_info = c_begin, c_end, c_step

        g_begin, g_end, g_step = -15, 3, 2
        g_info = g_begin, g_end, g_step

        stage_info = {'stage': 0,
                      'text': '',
                      'min': 0,
                      'max': 1,
                      'meta': 'Classifier training:',
                      'item_name': 'round',
                      'progress': 0,
                      }
        self.set_stage_info(stage_info)

        i = 0
        best_accuracy = -1
        best_log2c = None
        best_log2g = None
        best_conf = None
        is_abort = False
        stopwatch = StopWatch()
        self._learner.filterData(apply=True)
        for info in self._learner.iterGridSearchSVM(c_info=c_info,
                                                    g_info=g_info):
            n, log2c, log2g, conf = info
            stage_info.update({'min': 1,
                               'max': n,
                               'progress': i+1,
                               'text': 'log2(C)=%d, log2(g)=%d' % \
                               (log2c, log2g),
                               'interval': stopwatch.current_interval(),
                               })
            self.set_stage_info(stage_info)
            stopwatch.reset()
            i += 1
            accuracy = conf.ac_sample
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_log2c = log2c
                best_log2g = log2g
                best_conf = conf
                self.conf_result.emit(log2c, log2g, conf)
            time.sleep(.05)

            if self.get_abort():
                is_abort = True
                break

        # overwrite only if grid-search was not aborted by the user
        if not is_abort:
            self._learner.train(2**best_log2c, 2**best_log2g)
            self._learner.exportConfusion(best_log2c, best_log2g, best_conf)
            self._learner.exportRanges()
            # FIXME: in case the meta-data (colors, names, zero-insert) changed
            #        the ARFF file has to be written again
            #        -> better store meta-data outside ARFF
            self._learner.exportToArff()



class _ProcessorMixin(object):
    def __init__(self):
        self._is_running = False
        self._is_abort = False
        self._has_error = True
        self._current_process = None
        self._image_combo = None
        self._stage_infos = {}
        self._process_items = None

        self._control_buttons = OrderedDict()

        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.connect(shortcut, SIGNAL('activated()'), self._on_esc_pressed)

        #frame = self._get_frame()
#        frame = self._control
#        layout = frame.layout()
#
#        self._analyzer_progress2 = QProgressBar(frame)
#        self._analyzer_label2 = QLabel(frame)
#        layout.addWidget(self._analyzer_progress2, 1, 0, 1, 3)
#        layout.addWidget(self._analyzer_label2, 2, 0, 1, 3)
#
#        self._analyzer_progress1 = QProgressBar(frame)
#        self._analyzer_label1 = QLabel(frame)
#        layout.addWidget(self._analyzer_progress1, 3, 0, 1, 3)
#        layout.addWidget(self._analyzer_label1, 4, 0, 1, 3)
#
#        self._show_image = QCheckBox('Show images', frame)
#        self._show_image.setTristate(False)
#        self._show_image.setCheckState(Qt.Checked)
#        layout.addWidget(self._show_image, 5, 0)
#
#        self._run_button = QPushButton('Start processing', frame)
#        self.connect(self._run_button, SIGNAL('clicked()'), self._on_run_analyer)
#        layout.addWidget(self._run_button, 5, 2)
#
#        self._is_running = False
#        self._image_combo = None

    def register_process(self, name):
        pass

    def register_control_button(self, name, cls, labels):
        self._control_buttons[name] = {'labels' : labels,
                                       'widget' : None,
                                       'cls'    : cls,
                                       }

    def _init_control(self, has_images=True):
        layout = QHBoxLayout(self._control)
        layout.setContentsMargins(0,0,0,0)

        self._progress_label0 = QLabel(self._control)
        self._progress_label0.setText('')
        layout.addWidget(self._progress_label0)

        self._progress0 = QProgressBar(self._control)
        self._progress0.setTextVisible(False)
        layout.addWidget(self._progress0)

        if has_images:
            self._show_image = QCheckBox('Show images', self._control)
            self._show_image.setChecked(True)
            layout.addWidget(self._show_image)

        for name in self._control_buttons:
            w_button = QPushButton('', self._control)
            layout.addWidget(w_button)
            handler = lambda x: lambda : self._on_process_start(x)
            self.connect(w_button, SIGNAL('clicked()'), handler(name))
            self._control_buttons[name]['widget'] = w_button

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        self.connect(help_button, SIGNAL('clicked()'), handler('controlpanel'))
        layout.addWidget(help_button)

        if not self.TABS is None:
            self.connect(self._tab, SIGNAL('currentChanged(int)'), self._on_tab_changed)
            self._on_tab_changed(0)
        else:
            for name in self._control_buttons:
                self._set_control_button_text(name=name)

    @classmethod
    def get_special_settings(cls, settings, has_timelapse=True):
        settings = settings.copy()

        # try to resolve the paths relative to the package dir
        # (only in case of an relative path given)
        converts = [('General', 'pathin'),
                    ('General', 'pathout'),
                    ('Classification', 'primary_classification_envpath'),
                    ('Classification', 'secondary_classification_envpath'),
                    ('ErrorCorrection', 'primary_graph'),
                    ('ErrorCorrection', 'secondary_graph'),
                    ('ErrorCorrection', 'mappingfile_path'),
                    ]
        for section, option in converts:
            value = settings.get(section, option)
            settings.set(section, option, convert_package_path(value))
        return settings

    def _get_modified_settings(self, name, has_timelapse):
        return self.get_special_settings(self._settings, has_timelapse)

    def _on_tab_changed(self, idx):
        names = ['primary', 'secondary', 'tertiary']
        self._tab_name = names[idx]
        for name in self._control_buttons:
            self._set_control_button_text(name=name)

    def _set_control_button_text(self, name=None, idx=0):
        if name is None:
            name = self._current_process
        w_button = self._control_buttons[name]['widget']
        try:
            text = self._control_buttons[name]['labels'][idx] % self._tab_name
        except:
            text = self._control_buttons[name]['labels'][idx]
        w_button.setText(text)

    def enable_control_buttons(self, state=True):
        for name in self._control_buttons:
            w_button = self._control_buttons[name]['widget']
            w_button.setEnabled(state)

    def _toggle_control_buttons(self, name=None):
        if name is None:
            name = self._current_process
        for name2 in self._control_buttons:
            if name != name2:
                w_button = self._control_buttons[name2]['widget']
                w_button.setEnabled(not w_button.isEnabled())

    def _on_process_start(self, name, start_again=False):
        if not self._is_running or start_again:

            is_valid = True
            self._is_abort = False
            self._has_error = False

            if self._process_items is None:
                cls = self._control_buttons[name]['cls']
                if type(cls) == types.ListType:
                    self._process_items = cls
                    self._current_process_item = 0
                    cls = cls[0]

                    # remove HmmThread if process is not first in list and
                    # not valid error correction was activated
                    if (HmmThread in self._process_items and
                        self._process_items.index(HmmThread) > 0 and
                        not (self._settings.get('Processing', 'primary_errorcorrection') or
                             (self._settings.get('Processing', 'secondary_errorcorrection') and
                              self._settings.get('Processing', 'secondary_processchannel')))):
                        self._process_items.remove(HmmThread)

                else:
                    self._process_items = None
                    self._current_process_item = 0
            else:
                cls = self._process_items[self._current_process_item]


            if self.SECTION_NAME == 'Classification':
                result_frame = self._get_result_frame(self._tab_name)
                result_frame.load_classifier(check=False)
                learner = result_frame._learner

                if name == self.PROCESS_PICKING:
                    if not result_frame.is_pick_samples():
                        is_valid = False
                        result_frame.msg_pick_samples(self)
                    elif result_frame.is_train_classifier():
                        if not question(self, 'Samples already picked',
                                    'Do you want to pick samples again and '
                                    'overwrite previous '
                                    'results?'):
                            is_valid = False

                elif name == self.PROCESS_TRAINING:
                    if not result_frame.is_train_classifier():
                        is_valid = False
                        result_frame.msg_train_classifier(self)
                    elif result_frame.is_apply_classifier():
                        if not question(self, 'Classifier already trained',
                                    'Do you want to train the classifier '
                                    'again?'):
                            is_valid = False

                elif name == self.PROCESS_TESTING and not result_frame.is_apply_classifier():
                    is_valid = False
                    result_frame.msg_apply_classifier(self)


            elif cls is HmmThread:

                success, cmd = HmmThread.test_executable(self._settings.get('ErrorCorrection', 'filename_to_R'))
                if not success:
                    critical(self, 'Error running R',
                             "The R command line program '%s' could not be executed.\n\n"\
                             "Make sure that the R-project is installed.\n\n"\
                             "See README.txt for details." % cmd)
                    is_valid = False


            if is_valid:
                self._current_process = name
                #qApp._image_dialog = None

                if not start_again:
                    qApp._log_window.clear()

                    self._is_running = True
                    self._stage_infos = {}

                    self._toggle_tabs(False)
                    # disable all section button of the main widget
                    self.toggle_tabs.emit(self.get_name())

                    self._set_control_button_text(idx=1)
                    self._toggle_control_buttons()

                imagecontainer = self.parent().main_window._imagecontainer
                if cls is AnalzyerThread:

                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings, imagecontainer)

                    self._set_display_renderer_info()

                    # clear the image display and raise the window
                    if not qApp._image_dialog is None:
                        pix = qApp._graphics.pixmap()
                        pix2 = QPixmap(pix.size())
                        pix2.fill(Qt.black)
                        qApp._graphics.setPixmap(pix2)
                        qApp._image_dialog.raise_()

                elif cls is TrainingThread:
                    self._current_settings = self._settings.copy()

                    self._analyzer = cls(self, self._current_settings, result_frame._learner)
                    self._analyzer.setTerminationEnabled(True)

                    self._analyzer.conf_result.connect(result_frame.on_conf_result,
                                                       Qt.QueuedConnection)
                    result_frame.reset()

                elif cls is HmmThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)

                    # FIXME: classifier handling needs revision!!!
                    learner_dict = {}
                    for kind in ['primary', 'secondary']:
                        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (kind, y))
                        env_path = convert_package_path(_resolve('Classification', 'classification_envpath'))
                        if (_resolve('Processing', 'classification') and
                            (kind == 'primary' or self._settings.get('Processing', 'secondary_processchannel'))):
                            classifier_infos = {'strEnvPath' : env_path,
                                                'strChannelId' : _resolve('ObjectDetection', 'channelid'),
                                                'strRegionId' : _resolve('Classification', 'classification_regionname'),
                                                }
                            learner = CommonClassPredictor(dctCollectSamples=classifier_infos)
                            learner.importFromArff()
                            learner_dict[kind] = learner
                    self._analyzer = cls(self, self._current_settings,
                                         learner_dict,
                                         self.parent().main_window._imagecontainer)
                    self._analyzer.setTerminationEnabled(True)

                self._analyzer.finished.connect(self._on_process_finished)
                self._analyzer.stage_info.connect(self._on_update_stage_info, Qt.QueuedConnection)
                self._analyzer.analyzer_error.connect(self._on_error, Qt.QueuedConnection)

                self._analyzer.start(QThread.LowestPriority)
                if self._current_process_item == 0:
                    status('Process started...')

        else:
            self._abort_processing()

    def _toggle_tabs(self, state):
        if not self.TABS is None:
            for i in range(self._tab.count()):
                if i != self._tab.currentIndex():
                    self._tab.setTabEnabled(i, state)

    def _abort_processing(self):
        self.setCursor(Qt.BusyCursor)
        self._is_abort = True
        dlg = waitingProgressDialog('Please wait until the processing has been terminated...', self)
        dlg.setTarget(self._analyzer.set_abort, wait=True)
        dlg.exec_()
        self.setCursor(Qt.ArrowCursor)

    def _on_render_changed(self, name):
        #FIXME: proper sub-classing needed
        try:
            self._analyzer.set_renderer(name)
        except AttributeError:
            pass

    def _on_error(self, msg):
        self._has_error = True
        critical(self, 'An error occurred during processing.', detail=msg)

    def _on_process_finished(self):

        if (not self._process_items is None and
            self._current_process_item+1 < len(self._process_items) and
            not self._is_abort and
            not self._has_error):
            self._current_process_item += 1
            self._on_process_start(self._current_process, start_again=True)
        else:
            self._is_running = False
            #logger = logging.getLogger()
            #logger.removeHandler(self._handler)
            self._set_control_button_text(idx=0)
            self._toggle_control_buttons()
            self._toggle_tabs(True)
            # enable all section button of the main widget
            self.toggle_tabs.emit(self.get_name())
            if not self._is_abort and not self._has_error:
                if self.SECTION_NAME == 'ObjectDetection':
                    msg = 'Object detection successfully finished.'
                elif self.SECTION_NAME == 'Classification':
                    if self._current_process == self.PROCESS_PICKING:
                        msg = 'Samples successfully picked.\n\n'\
                              'Please train the classifier now based on the '\
                              'newly picked samples.'
                        result_frame = self._get_result_frame(self._tab_name)
                        result_frame.load_classifier(check=False)
                        nr_removed = len(result_frame._learner.filterData(apply=False))
                        if nr_removed > 0:
                            msg += '\n\n%d features contained NA values and will be removed from training.' % nr_removed
                    elif self._current_process == self.PROCESS_TRAINING:
                        msg = 'Classifier successfully trained.\n\n'\
                              'You can test the classifier performance here'\
                              'visually or apply the classifier in the '\
                              'processing workflow.'
                    elif self._current_process == self.PROCESS_TESTING:
                        msg = 'Classifier testing successfully finished.'
                elif self.SECTION_NAME == 'Tracking':
                    if self._current_process == self.PROCESS_TRACKING:
                        msg = 'Tracking successfully finished.'
                    elif self._current_process == self.PROCESS_SYNCING:
                        msg = 'Motif selection successfully finished.'
                elif self.SECTION_NAME == 'ErrorCorrection':
                    msg = 'HMM error correction successfully finished.'
                elif self.SECTION_NAME == 'Processing':
                    msg = 'Processing successfully finished.'

                information(self, 'Process finished', msg)
                status(msg)
            else:
                if self._is_abort:
                    status('Process aborted by user.')
                elif self._has_error:
                    status('Process aborted by error.')

            self._current_process = None
            self._process_items = None

    def _on_esc_pressed(self):
        if self._is_running:
            self._abort_processing()

    def _on_update_stage_info(self, info):
        sep = '   |   '
        info = dict([(str(k), v) for k,v in info.iteritems()])
        #print info
        if self.CONTROL == CONTROL_1:
            if info['stage'] == 0:
                self._progress0.setRange(info['min'], info['max'])
                if not info['progress'] is None:
                    self._progress0.setValue(info['progress'])
                    if info['max'] != 0:
                        self._progress_label0.setText('%3.1f%%' %\
                                                      (info['progress']*100.0/info['max']))
                    msg = ''
                    if 'meta' in info:
                        msg += '%s' % info['meta']
                    if 'text' in info:
                        msg += '   %s' % info['text']
                    if info['progress'] > info['min'] and 'interval' in info:
                        interval = info['interval']
                        self._intervals.append(interval.get_interval())
                        avg = numpy.average(self._intervals)
                        estimate = TimeInterval(avg * float(info['max']-info['progress']))
                        msg += '%s~ %.1fs / %s%s%s remaining' % (sep,
                                                               #interval.get_interval(),
                                                               avg,
                                                               info['item_name'],
                                                               sep,
                                                               estimate.format())
                    else:
                        self._intervals = []
                    status(msg)
                else:
                    self._progress_label0.setText('')
            else:
                self._stage_infos[info['stage']] = info
                if len(self._stage_infos) > 1:
                    total = self._stage_infos[1]['max']*self._stage_infos[2]['max']
                    current = (self._stage_infos[1]['progress']-1)*self._stage_infos[2]['max']+self._stage_infos[2]['progress']
                    #print current, total
                    self._progress0.setRange(0, total)
                    self._progress0.setValue(current)
                    #info = self._stage_infos[2]
                    self._progress_label0.setText('%.1f%%' % (current*100.0/total))
                    sep = '   |   '
                    msg = '%s   %s%s%s' % (self._stage_infos[2]['meta'],
                                           self._stage_infos[1]['text'],
                                           sep,
                                           self._stage_infos[2]['text'])
                    if current > 1:
                        interval = info['interval']
                        self._intervals.append(interval.get_interval())
                        estimate = TimeInterval(numpy.average(self._intervals) *
                                                float(total-current))
                        msg += '%s%.1fs / %s%s%s remaining' % (sep,
                                                               interval.get_interval(),
                                                               self._stage_infos[2]['item_name'],
                                                               sep,
                                                               estimate.format())
                    else:
                        self._intervals = []
                    status(msg)
        elif self.CONTROL == CONTROL_2:
            if info['stage'] == 1:
                if 'progress' in info:
                    self._analyzer_progress1.setRange(info['min'], info['max'])
                    self._analyzer_progress1.setValue(info['progress'])
                    self._analyzer_label1.setText('%s (%d / %d)' % (info['text'],
                                                                    info['progress'],
                                                                    info['max']))
                else:
                    self._analyzer_label1.setText(info['text'])
            else:
                if 'progress' in info:
                    self._analyzer_progress2.setRange(info['min'], info['max'])
                    self._analyzer_progress2.setValue(info['progress'])
                    self._analyzer_label2.setText('%s: %s (%d / %d)' % (info['text'],
                                                                        info['meta'],
                                                                        info['progress'],
                                                                        info['max']))
                else:
                    self._analyzer_label2.setText(info['text'])

    def _on_update_image(self, image_rgb, info, filename):
        if self._show_image.isChecked():
            # FIXME:
            if image_rgb.width % 4 != 0:
                image_rgb = ccore.subImage(image_rgb, ccore.Diff2D(0,0), ccore.Diff2D(image_rgb.width - (image_rgb.width % 4), image_rgb.height))
            qimage = numpy_to_qimage(image_rgb.toArray(copy=False))

            if qApp._image_dialog is None:
                qApp._image_dialog = QFrame()
                ratio = qimage.height()/float(qimage.width())
                qApp._image_dialog.setGeometry(50, 50, 800, 800*ratio)

                shortcut = QShortcut(QKeySequence(Qt.Key_Escape), qApp._image_dialog)
                shortcut.activated.connect(self._on_esc_pressed)

                layout = QVBoxLayout(qApp._image_dialog)
                layout.setContentsMargins(0,0,0,0)

                qApp._graphics = ImageRatioDisplay(qApp._image_dialog, ratio)
                qApp._graphics.setScaledContents(True)
                qApp._graphics.resize(800, 800*ratio)
                qApp._graphics.setMinimumSize(QSize(100,100))
                policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                policy.setHeightForWidth(True)
                qApp._graphics.setSizePolicy(policy)
                layout.addWidget(qApp._graphics)

                dummy = QFrame(qApp._image_dialog)
                dymmy_layout = QHBoxLayout(dummy)
                dymmy_layout.setContentsMargins(5,5,5,5)

                qApp._image_combo = QComboBox(dummy)
                qApp._image_combo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                            QSizePolicy.Fixed))
                self._set_display_renderer_info()

                dymmy_layout.addStretch()
                dymmy_layout.addWidget(qApp._image_combo)
                dymmy_layout.addStretch()
                layout.addWidget(dummy)
                layout.addStretch()

                qApp._image_dialog.show()
                qApp._image_dialog.raise_()
            #else:
            #    qApp._graphics_pixmap.setPixmap(QPixmap.fromImage(qimage))
            qApp._graphics.setPixmap(QPixmap.fromImage(qimage))
            qApp._image_dialog.setWindowTitle(info)
            qApp._image_dialog.setToolTip(filename)
            if not qApp._image_dialog.isVisible():
                qApp._image_dialog.show()
                qApp._image_dialog.raise_()


    def _set_display_renderer_info(self):
        rendering = [x for x in self._current_settings.get('General', 'rendering')
                     if not x in [PrimaryChannel.PREFIX, SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]]
        rendering += self._current_settings.get('General', 'rendering_class').keys()
        rendering.sort()

        if len(rendering) > 0:
            self._analyzer.set_renderer(rendering[0])
        else:
            self._analyzer.set_renderer(None)

        if not qApp._image_dialog is None:
            widget = qApp._image_combo
            current = widget.currentText()
            widget.clear()
            if len(rendering) > 1:
                for name in rendering:
                    widget.addItem(name)
                widget.show()
                widget.currentIndexChanged[str].connect(self._on_render_changed)
                if current in rendering:
                    widget.setCurrentIndex(widget.findText(current, Qt.MatchExactly))
            else:
                widget.hide()

        self._analyzer.image_ready.connect(self._on_update_image)
        
        
class LogRecordStreamHandler(SocketServer.BaseRequestHandler):
    'Handler for a streaming logging request'
    
    def handle(self):
        '''
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format.
        '''
        while 1:
            try:
                chunk = self.request.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                chunk = self.request.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.request.recv(slen - len(chunk))
                obj = self.unPickle(chunk)
                record = logging.makeLogRecord(obj)
                self.handleLogRecord(record)
            
            except socket.error:
                print 'socket handler abort'
                break
                  
        
    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)


class NicePidHandler(logging.Handler):
    
    def __init__(self, log_window, level=logging.NOTSET):
        logging.Handler.__init__(self, level)
        self.log_window = log_window
        
    def emit(self, record):
        self.log_window.on_msg_received_emit(record, self.format(record))


class LoggingReceiver(SocketServer.ThreadingTCPServer):
    'Simple TCP socket-based logging receiver'

    logname = None

    def __init__(self, host='localhost',
                 port=None,
                 handler=LogRecordStreamHandler):
        self.handler = handler
        if port is None:
            port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
        SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler)


class BaseProcessorFrame(BaseFrame, _ProcessorMixin):

    def __init__(self, settings, parent):
        BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

    def set_active(self, state):
        # set internal state and enable/disable control buttons
        super(BaseProcessorFrame, self).set_active(state)
        self.enable_control_buttons(state)

