"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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

__all__ = ['ProcessingFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

import threading, \
        logging

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog import CHANNEL_PREFIX
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
                                HmmThread,
                                MultiAnalzyerThread,
                                )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.plugin.segmentation import REGION_INFO

from PyQt4.QtGui import *
from PyQt4.QtCore import *

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SubProcessLogWindow(QFrame):
    lock = threading.Lock()
    on_msg_received = pyqtSignal(str, str, int)
    
    def __init__(self, parent):
        QFrame.__init__(self)
        self.setWindowTitle('Process log window')
        self.setGeometry(50,50,800,400)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(QLabel('Process logs for each child process'))
        self.tab_widget = QTabWidget()
        self.tab_widget.setUsesScrollButtons(True)
        self._layout.addWidget(self.tab_widget)
        self.on_msg_received.connect(self.on_show_msg)
        
    def init_process_list(self, sub_process_names):
        self.tab_widget.clear()
        self.items = {}
        for p in sub_process_names:
            lw = QPlainTextEdit(self.tab_widget)
            self.items[p] = lw
            self.tab_widget.addTab(lw, p)
        
    def on_show_msg(self, name, msg, level):
        print '+'*10, msg, level
        if level == logging.INFO:
            msg = "<font color='black'>" + msg + '</font>'
            self.items[name].appendHtml(msg)
        elif level == logging.DEBUG:
            msg = "<font color='green'>" + msg + '</font>'
            self.items[name].appendHtml(msg)
        elif level == logging.WARNING:
            msg = "<font color='blue'><b>" + msg + '</b></font>'
            self.items[name].appendHtml(msg)
        elif level > logging.WARNING:
            msg = "<font color='red'><b>" + msg + '</b></font>' 
        else:
            self.items[name].appendPlainText(msg)
            
    def on_msg_received_emit(self, record, formated_msg):
        self.on_msg_received.emit(record.name, formated_msg, record.levelno)

        
        
class ProcessingFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_PROCESSING

    def __init__(self, settings, parent):
        super(ProcessingFrame, self).__init__(settings, parent)

        self.register_control_button('process',
                                     [AnalzyerThread,
                                      HmmThread],
                                     ('Start processing', 'Stop processing'))
        
        self.register_control_button('multi_process',
                                     [MultiAnalzyerThread,
                                      HmmThread],
                                     ('Start multi processing', 'Stop multi processing'))
        

        self.add_group(None,
                       [('primary_featureextraction', (0,0,1,1)),
                        ('primary_classification', (1,0,1,1)),
                        ('tracking', (2,0,1,1)),
                        ('tracking_synchronize_trajectories', (3,0,1,1)),
                        ('primary_errorcorrection', (4,0,1,1))
                        ], link='primary_channel', label='Primary channel')

        for prefix in ['secondary', 'tertiary']:
            self.add_group('%s_processchannel' % prefix,
                           [('%s_featureextraction' % prefix, (0,0,1,1)),
                            ('%s_classification' % prefix, (1,0,1,1)),
                            ('%s_errorcorrection' % prefix, (2,0,1,1))
                            ])

        #self.add_line()

        self.add_expanding_spacer()

        self._init_control()
        self.process_log_window = SubProcessLogWindow(self)

    @classmethod
    def get_export_settings(cls, settings, has_timelapse=True):
        settings = BaseProcessorFrame.get_special_settings(settings, has_timelapse)

        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        colors = REGION_INFO.colors
        for prefix in CHANNEL_PREFIX:
            if prefix == 'primary' or settings.get('Processing', '%s_processchannel' % prefix):
                d = dict([('%s_contours_%s' % (prefix, x),
                                               {prefix.capitalize(): {'raw': ('#FFFFFF', 1.0),
                                                                      'contours': [(x, colors[x], 1, show_ids)]
                                               }})
                                               for x in REGION_INFO.names[prefix]])
                settings.get('General', 'rendering').update(d)

                if settings.get('Processing', '%s_classification' % prefix):
                    d = dict([('%s_classification_%s' % (prefix, x),
                               {prefix.capitalize(): {'raw': ('#FFFFFF', 1.0),
                                                      'contours': [(x, 'class_label', 1, False),
                                                                   (x, '#000000' , 1, show_ids_class)]
                               }})
                               for x in REGION_INFO.names[prefix]
                               if x == settings.get('Classification',
                                                    '%s_classification_regionname' % prefix)])
                    settings.get('General', 'rendering_class').update(d)

        if has_timelapse:
            # generate raw images of selected channels (later used for gallery images)
            if settings.get('Output', 'events_export_gallery_images'):
                for prefix in CHANNEL_PREFIX:
                    if prefix == 'primary' or settings.get('Processing', '%s_processchannel' % prefix):
                        settings.get('General', 'rendering').update({prefix : {prefix.capitalize() :
                                                                               {'raw': ('#FFFFFF', 1.0)}}})

        return settings


    @classmethod
    def get_special_settings(cls, settings, has_timelapse=True):
        settings = cls.get_export_settings(settings, has_timelapse)

        settings.set_section('Processing')
        for prefix in CHANNEL_PREFIX[1:]:
            if not settings.get2('%s_processchannel' % prefix):
                settings.set2('%s_classification' % prefix, False)
                settings.set2('%s_errorcorrection' % prefix, False)

        if not has_timelapse:
            # disable some tracking related settings in case no time-lapse data is present
            settings.set('Processing', 'tracking', False)
            settings.set('Processing', 'tracking_synchronize_trajectories', False)
            settings.set('Output', 'events_export_gallery_images', False)
            settings.set('Output', 'events_export_all_features', False)
            settings.set('Output', 'export_track_data', False)

        return settings
