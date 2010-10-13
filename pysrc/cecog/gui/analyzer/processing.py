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

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.gui.analyzer import (_BaseFrame,
                                _ProcessorMixin,
                                AnalzyerThread,
                                HmmThread,
                                )
from cecog.analyzer import (SECONDARY_REGIONS,
                            SECONDARY_COLORS,
                            )

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class ProcessingFrame(_BaseFrame, _ProcessorMixin):

    SECTION_NAME = SECTION_NAME_PROCESSING

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

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
        self.add_group('secondary_processchannel',
                       [('secondary_featureextraction', (0,0,1,1)),
                        ('secondary_classification', (1,0,1,1)),
                        ('secondary_errorcorrection', (2,0,1,1))
                        ])

        #self.add_line()

        self.add_expanding_spacer()

        self._init_control()

    @classmethod
    def get_special_settings(cls, settings):
        settings = _ProcessorMixin.get_special_settings(settings)

        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        settings.set_section('Classification')
        sec_region = settings.get2('secondary_classification_regionname')

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = [v for k,v in SECONDARY_REGIONS.iteritems()
                       if settings.get2(k)]
        lookup = dict([(v,k) for k,v in SECONDARY_REGIONS.iteritems()])

        # FIXME: we should rather show a warning here!
        if not sec_region in sec_regions:
            sec_regions.append(sec_region)
            settings.set2(lookup[sec_region], True)

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
        if settings.get2('secondary_processchannel'):
            settings.get('General', 'rendering').update(dict([('secondary_contours_%s' % x, {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                      'contours': [(x, SECONDARY_COLORS[x] , 1, show_ids)]
                                                                                             }})
                                                              for x in sec_regions]))

            if settings.get2('secondary_classification'):
                settings.get('General', 'rendering_class').update({'secondary_classification_%s' % sec_region: {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                                         'contours': [(sec_region, 'class_label', 1, False),
                                                                                                                                      (sec_region, '#000000', 1, show_ids_class),
                                                                                                                                      ]}}})
        else:
            settings.set2('secondary_classification', False)
            settings.set2('secondary_errorcorrection', False)

        return settings
