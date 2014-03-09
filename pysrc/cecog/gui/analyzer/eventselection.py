"""
eventselection.py
"""

__author__ = 'Qing Zhong'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['EventSelectionFrame']

from cecog.gui.analyzer import BaseProcessorFrame
from cecog.gui.analyzer.classification import ClassificationFrame
from cecog.threads.analyzer import AnalyzerThread
from cecog.analyzer.channel import PrimaryChannel

class EventSelectionFrame(BaseProcessorFrame):

    DISPLAY_NAME = 'Event Selection'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent, name):
        super(EventSelectionFrame, self).__init__(settings, parent, name)
        self.register_control_button(self.PROCESS_SYNCING, AnalyzerThread, \
                              ('Test event selection', 'Stop event selection'))


        self.add_group(None,
                       [('backwardrange', (0,0,1,1)),
                        ('forwardrange', (0,1,1,1)),
                        ('duration_unit', (0,2,1,1)),
                        ], link='eventselection',
                       label='Event selection')
        self.add_line()
        self.add_group('supervised_event_selection',
                       [('labeltransitions', (0,0,1,1)),
                        ('eventchannel', (0,1,1,1)),
                        ('backwardlabels', (1,0,1,1)),
                        ('forwardlabels', (1,1,1,1)),
                        ('backwardcheck', (2,0,1,1)),
                        ('forwardcheck', (2,1,1,1)),
                       ], layout='grid')

        self.add_group('unsupervised_event_selection',
                       [('min_event_duration', (2, 2, 1, 1)),
                        (self.add_label('TC3 Analysis', 'tc3_analysis'),
                         (3, 0, 1,1)),
                        ('num_clusters', (3,2,1,1)),
                        ('min_cluster_size', (3,3,1,1)),
                        ], layout='grid',)

        self.add_expanding_spacer()
        self._init_control()

    def page_changed(self):
        self.settings_loaded()

    def settings_loaded(self):
        trait = self._settings.get_trait('EventSelection',
                                         'eventchannel')
        clfframe = self.parent().widgetByType(ClassificationFrame)

        # list only classifiers that has been trained
        clfnames = [k for k, c in clfframe.classifiers.items() if c.is_valid]
        trait.set_list_data(clfnames)

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings( \
            self, name, has_timelapse)

        # turn on tracking and event seletion
        settings.set('Processing', 'tracking', True)
        settings.set('Processing', 'eventselection', True)
        settings.set('General', 'rendering_class', {})
        settings.set('General', 'rendering', {})

        settings.set('Classification', 'collectsamples', False)
        settings.set('Output', 'hdf5_create_file', False)
        settings.set('Output', 'events_export_gallery_images', False)

        # only primary channel for event selection
        settings.set('Processing', 'secondary_featureextraction', False)
        settings.set('Processing', 'secondary_classification', False)
        settings.set('General', 'process_secondary', False)
        settings.set('Processing', 'tertiary_featureextraction', False)
        settings.set('Processing', 'tertiary_classification', False)
        settings.set('General', 'process_tertiary', False)
        settings.set('Processing', 'merged_classification', False)
        settings.set('General', 'process_merged', False)

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        render_contours = {PrimaryChannel.NAME:
                           {'raw': ('#FFFFFF', 1.0),
                            'contours': {'primary': ('#FF0000', 1, show_ids)}}}

        render_class = {PrimaryChannel.NAME:
                            {'raw': ('#FFFFFF', 1.0),
                             'contours': [('primary', 'class_label', 1, False),
                                          ('primary', '#000000', 1,
                                           show_ids_class)]}}

        # setting up primary channel and live rendering
        if settings.get('EventSelection', 'unsupervised_event_selection'):
            settings.set('Processing', 'primary_featureextraction', True)
            settings.set('Processing', 'primary_classification', True)
            settings.set('Processing', 'secondary_classification', False)
            settings.set('Processing', 'tertiary_classification', False)
            settings.set('Processing', 'merged_classification', False)
            settings.set('General', 'rendering',
                         {'primary_contours': render_contours})

        elif settings.get('EventSelection', 'supervised_event_selection'):
            settings.set('Processing', 'primary_featureextraction', True)
            settings.set('Processing', 'primary_classification', True)
            settings.set('General', 'rendering_class',
                         {'primary_classification': render_class})
        return settings
