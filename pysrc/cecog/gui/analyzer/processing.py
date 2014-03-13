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


import logging
from PyQt4 import QtGui
from PyQt4 import QtCore

from cecog import CHANNEL_PREFIX, VERSION
from cecog import CH_OTHER, CH_VIRTUAL, CH_PRIMARY
from cecog.gui.analyzer import BaseProcessorFrame, AnalyzerThread
from cecog.gui.analyzer import ErrorCorrectionThread, MultiAnalyzerThread
from cecog.util.ctuple import CTuple


class ExportSettings(object):
    """Mixing for custom 'get_settings' methods."""

    def get_export_settings(self, settings, has_timelapse=True):
        settings = BaseProcessorFrame.get_special_settings(settings, has_timelapse)
        settings.set('General', 'version', VERSION)

        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        # set propertys of merged channel to the same as for Primary
        for prefix in CH_PRIMARY+CH_OTHER:
            if prefix == CH_PRIMARY[0] \
                    or settings.get('General', 'process_%s' % prefix):

                d = {} # render settings for contours
                for x in self.plugin_mgr.region_info.names[prefix]:
                    d = {'%s_contours_%s' % (prefix, x):
                             {prefix.capitalize(): {'raw': ('#FFFFFF', 1.0),
                                                    'contours': [(x, self.plugin_mgr.region_info.colors[x], 1, show_ids)]
                                                    }
                              }
                         }
                settings.get('General', 'rendering').update(d)

            # render settings for classifications
            d = {}
            if settings.get('Processing', '%s_classification' % prefix):
                for x in self.plugin_mgr.region_info.names[prefix]:
                    if x == settings.get('Classification', '%s_classification_regionname' % prefix) or \
                            prefix == CH_VIRTUAL[0]:
                        d = {'%s_classification_%s' % (prefix, x):
                                 {prefix.capitalize(): {'raw': ('#FFFFFF', 1.0),
                                                        'contours': [(x, 'class_label', 1, False),
                                                                     (x, '#000000' , 1, show_ids_class)]
                                                        }
                                  }
                             }
                if settings('EventSelection', 'supervised_event_selection'):
                    settings.get('General', 'rendering_class').update(d)

        # setup rendering properties for merged channel
        # want the same rendering properties as for the primary channel!
        if settings.get('General', 'process_merged'):

            # color are defined for regions (not for channels)
            # therefore, we first retrieve the regions for the primary channel
            # and (in the case there are some) we assign the color of the first
            # ROI of the primary channel to the merged contour.
            regions_primary = self.plugin_mgr.region_info.names[CH_PRIMARY[0]]
            if len(regions_primary) == 0:
                default_color = '#FF00FF'
            else:
                default_color = self.plugin_mgr.region_info.colors[regions_primary[0]]

            regions = self._merged_regions(settings)
            d = {'merged_contours_%s' %str(regions):
                     {"Merged": {'raw': ('#FFFFFF', 1.0),
                                 'contours': [(regions, default_color, 1, show_ids)]}}}
            settings.get("General", "rendering").update(d)
            if settings.get('Processing', 'merged_classification'):
                d = {'merged_classification_%s' %str(regions):
                         {"Merged": {'raw': ('#FFFFFF', 1.0),
                                     'contours': [(regions, 'class_label', 1, False),
                                                  (regions, '#000000' , 1, show_ids_class)]}}}
                settings.get("General", "rendering_class").update(d)

        if has_timelapse:
            # generate raw images of selected channels (later used for gallery images)
            if settings.get('Output', 'events_export_gallery_images'):
                for prefix in CHANNEL_PREFIX:
                    if prefix == 'primary' or settings.get('General', 'process_%s' % prefix):
                        settings.get('General', 'rendering').update({prefix : {prefix.capitalize() :
                                                                                   {'raw': ('#FFFFFF', 1.0)}}})
        return settings

    def _merged_regions(self, settings):
        """Return the regions seletected for segmentation in the
        order (primary, secondary, tertiary)."""
        regions = []
        for ch in (CH_PRIMARY+CH_OTHER):
            if settings.get("Classification", "merge_%s" %ch):
                regions.append(settings.get("Classification",
                                            "merged_%s_region" %ch))
        # want regions hashable
        return CTuple(regions)


    def get_special_settings(self, settings, has_timelapse=True):
        settings = self.get_export_settings(settings, has_timelapse)

        settings.set_section('Processing')
        for prefix in CHANNEL_PREFIX[1:]:
            if not settings('General', 'process_%s' % prefix):
                settings.set2('%s_classification' % prefix, False)
                settings.set2('%s_errorcorrection' % prefix, False)

        if not has_timelapse:
            # disable some tracking related settings in case no time-lapse data is present
            settings.set('Processing', 'tracking', False)
            settings.set('Processing', 'eventselection', False)
            settings.set('Output', 'events_export_gallery_images', False)
            settings.set('Output', 'events_export_all_features', False)
            settings.set('Output', 'export_track_data', False)

        return settings


class SubProcessLogWindow(QtGui.QWidget):

    on_msg_received = QtCore.pyqtSignal(str, str, int)

    def __init__(self, *args, **kw):
        super(SubProcessLogWindow, self).__init__(*args, **kw)
        self.setWindowTitle('Multiprocessing logger')
        self.setWindowModality(QtCore.Qt.NonModal)
        self.setWindowFlags(QtCore.Qt.Window)

        self.resize(800, 600)

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.addWidget(QtGui.QLabel('Process logs for each child process'))
        self.tab_widget = QtGui.QTabWidget()
        self.tab_widget.setUsesScrollButtons(True)
        self._layout.addWidget(self.tab_widget)
        self.on_msg_received.connect(self.on_show_msg)

    def init_process_list(self, sub_process_names):
        self.tab_widget.clear()
        self.items = {}
        for p in sub_process_names:
            lw = QtGui.QPlainTextEdit(self.tab_widget)
            lw.setReadOnly(True)
            self.items[p] = lw
            self.tab_widget.addTab(lw, p)

    def on_show_msg(self, name, msg, level):

        if level == logging.DEBUG:
            msg = "<font color='green'>" + msg + '</font>'
        elif level == logging.WARNING:
            msg = "<font color='orange'><b>" + msg + '</b></font>'
            self.tab_widget.setCurrentWidget(self.items[name])
        elif level == logging.ERROR:
            msg = "<font color='red'><b>" + msg + '</b></font>'
            self.tab_widget.setCurrentWidget(self.items[name])
        else:
            msg = "<font color='black'>" + msg + '</font>'
        self.items[name].appendHtml(msg.replace('\n', '<br>'))
        self.items[name].moveCursor(QtGui.QTextCursor.End)

    def on_msg_received_emit(self, record, formated_msg):
        self.on_msg_received.emit(record.name, formated_msg, record.levelno)


class ProcessingFrame(BaseProcessorFrame, ExportSettings):

    def __init__(self, settings, parent, name):
        super(ProcessingFrame, self).__init__(settings, parent, name)

        self.register_control_button('process',
                                     [AnalyzerThread, ErrorCorrectionThread],
                                     ('Start processing', 'Stop processing'))

        self.register_control_button('multi_process',
                                     [MultiAnalyzerThread, ErrorCorrectionThread],
                                     ('Start multi processing', 'Stop multi processing'))

        self.add_group(None,
                       [('primary_featureextraction', (0,0,1,1)),
                        ('primary_classification', (1,0,1,1)),
                        ('tracking', (2,0,1,1)),
                        ('eventselection', (3,0,1,1)),
                        ('primary_errorcorrection', (4,0,1,1))
                        ], sublinks=False, label='Primary channel')

        for prefix in CH_OTHER:
            self.add_group(None,
                           [('%s_featureextraction' % prefix, (0,0,1,1)),
                            ('%s_classification' % prefix, (1,0,1,1)),
                            ('%s_errorcorrection' % prefix, (2,0,1,1))
                            ], sublinks=False, label='%s channel' %prefix.title())

        self.add_group(None,
                       [('merged_classification', (1,0,1,1)),
                        ('merged_errorcorrection', (2,0,1,1))],
                        sublinks=False, label='Merged channel')

        self.add_expanding_spacer()
        self._init_control()
        self.log_window = SubProcessLogWindow()


    def _get_modified_settings(self, name, has_timelapse=True):
        settings = ExportSettings.get_special_settings(
            self, self._settings, has_timelapse)

        # some processing settings overrule error correction settings
        settings.set('ErrorCorrection', 'primary',
                     settings('Processing', 'primary_errorcorrection'))

        settings.set('ErrorCorrection', 'secondary',
                     (settings('Processing', 'secondary_errorcorrection') and \
                          settings('General', 'process_secondary')))

        settings.set('ErrorCorrection', 'tertiary',
                     (settings('Processing', 'tertiary_errorcorrection') and \
                          settings('General', 'process_tertiary')))

        settings.set('ErrorCorrection', 'merged',
                     (settings('Processing', 'merged_errorcorrection') and \
                          settings('General', 'process_merged')))


        # special clase for UES, clustering takes place afterwards
        if settings('EventSelection', 'unsupervised_event_selection'):
            settings.set('General', 'rendering_class', {})
            settings.set('Processing', 'primary_classification', True)
            settings.set('Processing', 'secondary_featureextraction', False)
            settings.set('Processing', 'secondary_classification', False)
            settings.set('General', 'process_secondary', False)
            settings.set('Processing', 'tertiary_featureextraction', False)
            settings.set('Processing', 'tertiary_classification', False)
            settings.set('General', 'process_tertiary', False)
            settings.set('Processing', 'merged_classification', False)
            settings.set('General', 'process_merged', False)

        return settings
