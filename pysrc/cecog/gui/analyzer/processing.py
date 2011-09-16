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
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
                                HmmThread,
                                )
from cecog.analyzer import (SECONDARY_REGIONS,
                            TERTIARY_REGIONS,
                            SECONDARY_COLORS,
                            )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )

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
        self._layout = QHBoxLayout(self)
        self.tab_widget = QTabWidget()
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
            msg = "<font color='blue'>" + msg + '</font>'
            self.items[name].appendHtml(msg)
        elif level == logging.DEBUG:
            msg = "<font color='red'>" + msg + '</font>'
            self.items[name].appendHtml(msg)
        elif level >= logging.WARNING:
            msg = "<font color='red'><b>" + msg + '</b></font>'
            self.items[name].appendHtml(msg)
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
    def get_special_settings(cls, settings, has_timelapse=True):
        settings = BaseProcessorFrame.get_special_settings(settings, has_timelapse)

        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        additional_prefixes = [SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]

        settings.set_section('Classification')
        sec_class_regions = dict([(prefix,
                                  settings.get2('%s_classification_regionname' % prefix))
                                  for prefix in additional_prefixes])

        settings.set_section('ObjectDetection')
        prim_id = PrimaryChannel.NAME
        sec_ids = dict([(x.PREFIX, x.NAME)
                        for x in [SecondaryChannel, TertiaryChannel]])
        sec_regions = dict([(prefix, [v for k,v in regions.iteritems()
                                      if settings.get2(k)])
                            for prefix, regions in
                            [(SecondaryChannel.PREFIX, SECONDARY_REGIONS),
                             (TertiaryChannel.PREFIX, TERTIARY_REGIONS),
                             ]])

#        lookup = dict([(v,k) for k,v in SECONDARY_REGIONS.iteritems()])
#        # FIXME: we should rather show a warning here!
#        if not sec_region in sec_regions:
#            sec_regions.append(sec_region)
#            settings.set2(lookup[sec_region], True)

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        settings.get('General', 'rendering').update({'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                    'contours': {'primary': ('#FF0000', 1, show_ids)}}}})

        settings.set_section('Processing')
        if settings.get2('primary_classification'):
            settings.get('General', 'rendering_class').update({'primary_classification': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                          'contours': [('primary', 'class_label', 1, False),
                                                                                                       ('primary', '#000000', 1, show_ids_class),
                                                                                                       ]}}})

        for prefix in additional_prefixes:
            if settings.get2('%s_processchannel' % prefix):
                sec_id = sec_ids[prefix]
                settings.get('General', 'rendering').update(dict([('%s_contours_%s' % (prefix, x), {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                             'contours': [(x, SECONDARY_COLORS[x] , 1, show_ids)]
                                                                                                 }})
                                                                  for x in sec_regions[prefix]]))

                if settings.get2('%s_classification' % prefix):
                    sec_id = sec_ids[prefix]
                    sec_region = sec_class_regions[prefix]
                    settings.get('General', 'rendering_class').update({'%s_classification_%s' % (prefix, sec_region): {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                                             'contours': [(sec_region, 'class_label', 1, False),
                                                                                                                                          (sec_region, '#000000', 1, show_ids_class),
                                                                                                                                          ]}}})
            else:
                settings.set2('%s_classification' % prefix, False)
                settings.set2('%s_errorcorrection' % prefix, False)

        if has_timelapse:
            # generate raw images of selected channels (later used for gallery images)
            if settings.get('Output', 'events_export_gallery_images'):
                settings.get('General', 'rendering').update({'primary' : {prim_id : {'raw': ('#FFFFFF', 1.0)}}})
                for prefix in additional_prefixes:
                    if settings.get2('%s_processchannel' % prefix):
                        sec_id = sec_ids[prefix]
                        settings.get('General', 'rendering').update({prefix : {sec_id : {'raw': ('#FFFFFF', 1.0)}}})
        else:
            # disable some tracking related settings in case no time-lapse data is present
            settings.set('Processing', 'tracking', False)
            settings.set('Processing', 'tracking_synchronize_trajectories', False)
            settings.set('Output', 'events_export_gallery_images', False)
            settings.set('Output', 'events_export_all_features', False)
            settings.set('Output', 'export_track_data', False)

        print settings.get('General', 'rendering')
        print settings.get('General', 'rendering_class')
        return settings
