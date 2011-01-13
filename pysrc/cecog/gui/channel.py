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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import os
from collections import OrderedDict

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.fileutils import collect_files
from pdk.datetimeutils import StopWatch

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.module import Module
from cecog.gui.colorbox import ColorBox
from cecog.traits.config import RESOURCE_PATH
from cecog.util.palette import (NucMedPalette,
                                ZeissPalette,
                                SingleColorPalette,
                                )

#-------------------------------------------------------------------------------
# constants:
#
DEFAULT_COLORS_BY_NAME = {'rfp' : 'red',
                          'gfp' : 'green',
                          'yfp' : 'yellow',
                          'cfp' : 'cyan',
                          }
DEFAULT_LUT_COLORS = ['red', 'green', 'blue',
                      'yellow', 'magenta', 'cyan', 'white']

COLOR_DEFINITIONS = {'red'    : '#FF0000',
                     'green'  : '#00FF00',
                     'blue'   : '#0000FF',
                     'yellow' : '#FFFF00',
                     'magenta': '#FF00FF',
                     'cyan'   : '#00FFFF',
                     'white'  : '#FFFFFF',
                     }

#-------------------------------------------------------------------------------
# functions:
#
def blend_images_max(images):
    '''
    blend a list of rgb images together by element-wise maximum
    color must be the innermost dimension
    '''
    if len(images) > 1:
        d = numpy.maximum(images[0], images[1])
        for image in images[2:]:
            d = numpy.maximum(d, image)
        return d
    elif len(images) == 1:
        return images[0]

#-------------------------------------------------------------------------------
# classes:
#
class ImageHelper:

    def __init__(self, vigra_image):
        self._vigra_image = vigra_image
        self.array = vigra_image.toArray(copy=False)


class ChannelItem(QFrame):

    channel_changed = pyqtSignal(str)

    def __init__(self, name, idx, palettes, parent):
        QFrame.__init__(self, parent)
        self.name = name
        self._show_image = True

        if name.lower() in DEFAULT_COLORS_BY_NAME:
            self._current = DEFAULT_COLORS_BY_NAME[name.lower()]
        else:
            self._current = DEFAULT_LUT_COLORS[idx]

        assert self._current in palettes, \
               "Color name '%s' not found in defined palettes." % self._current
        self._palettes = palettes

        layout = QGridLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        box = QCheckBox(name, self)
        box.setChecked(self._show_image)
        box.toggled.connect(self.on_show_toggled)
        layout.addWidget(box, 0, 0)
        combo = ColorBox(self._current, palettes, self)
        combo.selection_changed.connect(self.on_new_palette)
        layout.addWidget(combo, 1, 0)

    def render_image(self, image):
        if self._show_image:
            palette = self._palettes[self._current]
            rgb_image = palette.apply_to_numpy(image)
        else:
            rgb_image = numpy.zeros(list(image.shape)+[3], numpy.uint8)
        return rgb_image

    def on_show_toggled(self, state):
        self._show_image = state
        self.channel_changed.emit(self.name)

    def on_new_palette(self, name):
        self._current = str(name)
        self.channel_changed.emit(self.name)


class DisplaySettings:

    def __init__(self, default_minimum, default_maximum,
                 disp_minimum=0, disp_maximum=255):
        self.default_minimum = default_minimum
        self.default_maximum = default_maximum
        self.slider_range = disp_maximum - disp_minimum + 1
        self.brightness = self.slider_range / 2.0
        self.contrast = self.slider_range / 2.0
        self.minimum = default_minimum
        self.maximum = default_maximum

    def reset(self):
        self.minimum = self.default_minimum
        self.maximum = self.default_maximum
        self.brightness = self.slider_range / 2.0
        self.contrast = self.slider_range / 2.0

    def set_contrast(self, contrast):
        self.contrast = contrast
        center = self.minimum + (self.maximum - self.minimum) / 2.0
        mid = self.slider_range / 2.0
        if contrast <= mid:
            slope = contrast / mid
        else:
            slope = mid / (self.slider_range - contrast)
        if slope > 0.0:
            range = self.default_maximum - self.default_minimum
            self.minimum = center - (0.5 * range) / slope
            self.maximum = center + (0.5 * range) / slope

    def set_brightness(self, brightness):
        self.brightness = brightness
        center = self.default_minimum + \
                 (self.default_maximum - self.default_minimum) * \
                 (self.slider_range - brightness) / self.slider_range
        width = self.maximum - self.minimum
        self.minimum = center - width / 2.0
        self.maximum = center + width / 2.0

    def set_minimum(self, minimum):
        self.minimum = minimum
        if self.minimum > self.maximum:
            self.maximum = self.minimum
        self._update()

    def set_maximum(self, maximum):
        self.maximum = maximum
        if self.minimum > self.maximum:
            self.minimum = self.maximum
        self._update()

    def _update(self):
        range = float(self.default_maximum - self.default_minimum + 1)
        range2 = float(self.maximum - self.minimum + 1)
        mid = self.slider_range / 2.0
        self.contrast = (range / range2) * mid
        if self.contrast > mid:
            self.contrast = self.slider_range - (range2 / range) * mid
        level = self.minimum + range2 / 2.0
        normalized = 1.0 - (level - self.default_minimum) / range
        self.brightness = normalized * self.slider_range


class DisplayChannelGroup(QFrame):

    SLIDER_NAMES = ['minimum', 'maximum', 'brightness', 'contrast']

    values_changed = pyqtSignal(str)

    def __init__(self, names, parent):
        QFrame.__init__(self, parent)

        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        layout.setContentsMargins(5,5,5,5)

        frame_grp = QFrame(self)
        layout_grp = QBoxLayout(QBoxLayout.LeftToRight, frame_grp)
        layout_grp.setContentsMargins(0,0,0,0)
        layout_grp.addStretch(1)
        grp = QButtonGroup(frame_grp)
        grp.setExclusive(True)
        self._display_settings = {}
        self._current = None
        fct = lambda x: lambda y: self.on_channel_changed(x, y)
        for idx, name in enumerate(names):
            btn = QPushButton(name, frame_grp)
            btn.toggled.connect(fct(name))
            btn.setCheckable(True)
            btn.setStyleSheet('QPushButton {border: 1px solid #8f8f91;'
                              'border-radius: 3px;'
                              'min-width: 40px;}'
                              'QPushButton:checked { background-color: #afafb1; }')
            grp.addButton(btn)
            layout_grp.addWidget(btn)
            if idx == 0:
                btn.setChecked(True)
                self._current = name
            #if idx > 0:
            self._display_settings[name] = DisplaySettings(0, 255)
        layout_grp.addStretch(1)
        layout.addWidget(frame_grp)

        frame = QFrame(self)
        layout_frame = QGridLayout(frame)
        layout_frame.setContentsMargins(5,5,5,5)

        self._sliders = {}
        fct = lambda x: lambda : self.on_slider_changed(x)

        name = 'minimum'
        label = QLabel(name.capitalize(), frame)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 255)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 0, 0)
        layout_frame.addWidget(sld, 0, 1)

        name = 'maximum'
        label = QLabel(name.capitalize(), frame)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 255)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 1, 0)
        layout_frame.addWidget(sld, 1, 1)

        name = 'brightness'
        label = QLabel(name.capitalize(), frame)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 255)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 2, 0)
        layout_frame.addWidget(sld, 2, 1)

        name = 'contrast'
        label = QLabel(name.capitalize(), frame)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 255)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 3, 0)
        layout_frame.addWidget(sld, 3, 1)

        self.set_sliders()
        layout.addWidget(frame)

        btn = QPushButton('Reset', self)
        btn.clicked.connect(self.on_reset)
        layout.addWidget(btn)

    def set_sliders(self, ignore=None):
        s = self._display_settings[self._current]
        for name in self.SLIDER_NAMES:
            if name != ignore:
                sld = self._sliders[name]
                sld.blockSignals(True)
                sld.setValue(getattr(s, name))
                sld.blockSignals(False)

    def on_slider_changed(self, name):
        s = self._display_settings[self._current]
        sld = self._sliders[name]
        eval('s.set_%s(%d)' % (name, sld.value()))
        self.set_sliders(ignore=name)
        self.values_changed.emit(self._current)

    def on_reset(self):
        s = self._display_settings[self._current]
        s.reset()
        self.set_sliders()
        self.values_changed.emit(self._current)

    def on_channel_changed(self, name, state):
        if state:
            self._current = name
            self.set_sliders()

    def transform_image(self, name, image):
        s = self._display_settings[name]
        print s.maximum, s.minimum
        image = numpy.require(image, numpy.float)
        image *= 255.0 / (s.maximum - s.minimum + 0.1)
        image -= s.minimum
        image[image > 255] = 255
        image[image < 0] = 0
        image = numpy.require(image, numpy.uint8)
        return image


class Channel(Module):

    NAME = 'Channel'

    def __init__(self, parent, browser, meta_data):
        Module.__init__(self, parent, browser)
        self._meta_data = meta_data
        self._image_dict = {}
        self._display_images = {}
        self._rgb_images = {}

        palettes = self.import_palettes()

        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        layout.setContentsMargins(5, 5, 5, 5)

        frame_channels = QGroupBox('Channels', self)
        #frame_channels.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
        #                                         QSizePolicy.Minimum))
        layout.addWidget(frame_channels)
        frame_display = QGroupBox('Display', self)
        layout.addWidget(frame_display)
        layout_channels = QBoxLayout(QBoxLayout.TopToBottom, frame_channels)
        layout_channels.setContentsMargins(5, 5, 5, 5)
        layout_display = QBoxLayout(QBoxLayout.TopToBottom, frame_display)
        layout_display.setContentsMargins(5, 5, 5, 5)
        layout.addStretch(1)

        self._channels = OrderedDict()
        channel_names = sorted(self._meta_data.channels)
        for idx, channel_name in enumerate(channel_names):
            widget = ChannelItem(channel_name, idx, palettes, frame_channels)
            layout_channels.addWidget(widget)
            self._channels[channel_name] = widget
            widget.channel_changed.connect(self.on_channel_changed)

        self._display_ctrl = DisplayChannelGroup(channel_names, frame_display)
        self._display_ctrl.values_changed.connect(self.on_display_changed)
        layout_display.addWidget(self._display_ctrl)

    def import_palettes(self):
        palettes = OrderedDict()

        for name in DEFAULT_LUT_COLORS:
            p = SingleColorPalette.from_hex_color(name,
                                                  COLOR_DEFINITIONS[name])
            palettes[p.name] = p
        path_zeiss = os.path.join(RESOURCE_PATH, 'palettes', 'zeiss')
        for filename in collect_files(path_zeiss, ['.lut'], absolute=True):
            filename = os.path.abspath(filename)
            p = ZeissPalette(filename)
            palettes[p.name] = p
        return palettes

    def set_image_dict(self, image_dict):
        for name, image in image_dict.iteritems():
            self._image_dict[name] = ImageHelper(image)
        self._display_images.clear()
        self._rgb_images.clear()
        self.update_display()
        self.update_renderer()

    def update_display(self, restrict=None):
        for name, image_helper in self._image_dict.iteritems():
            image = image_helper.array
            if restrict is None or restrict == name:
                image = self._display_ctrl.transform_image(name, image)
                self._display_images[name] = image

    def update_renderer(self, restrict=None):
        for name, image in self._display_images.iteritems():
            widget = self._channels[name]
            if restrict is None or restrict == name:
                rgb_image = widget.render_image(image)
                self._rgb_images[name] = rgb_image
        rgb_images = self._rgb_images.values()
        self._browser.image_viewer.from_numpy(blend_images_max(rgb_images))

    def on_channel_changed(self, name):
        name = str(name)
        self.update_renderer(restrict=name)

    def on_display_changed(self, name):
        # in case all channels is changed no restriction applies
        if not name is None:
            name = str(name)
        self.update_display(restrict=name)
        self.update_renderer(restrict=name)

    def set_object_dict(self, d):
        pass
