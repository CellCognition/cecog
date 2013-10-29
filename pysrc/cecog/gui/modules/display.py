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

__all__ = []

import os
import zipfile
from collections import OrderedDict
import os
import zipfile

import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.fileutils import collect_files
from pdk.datetimeutils import StopWatch

from cecog.colors import Colors
from cecog.gui.modules.module import Module
from cecog.gui.widgets.colorbox import ColorBox
from cecog.environment import CecogEnvironment
from cecog.util.palette import (NucMedPalette,
                                ZeissPalette,
                                SingleColorPalette)
from cecog.gui.util import numpy_to_qimage
from cecog.gui.widgets.colorbutton import ColorButton

DEFAULT_COLORS_BY_NAME = Colors.channel_table
DEFAULT_LUT_COLORS = Colors.colors
COLOR_DEFINITIONS = dict((c, getattr(Colors, c)) for c in Colors.colors)

def blend_images_max(images):
    """
    blend a list of QImages together by "lighten" composition (lighter color
    of source and dest image is selected; same effect as max operation)
    """
    assert len(images) > 0, 'At least one image required for blending.'
    pixmap = QPixmap(images[0].width(), images[0].height())
    # for some reason the pixmap is NOT empty
    pixmap.fill(Qt.black)
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_Lighten)
    for image in images:
        if not image is None:
            painter.drawImage(0, 0, image)
    painter.end()
    return pixmap

#-------------------------------------------------------------------------------
# classes:
#
class ImageHelper(object):

    def __init__(self, image):
        self._image = image
        self.array = image.toArray(copy=False)


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
        layout.setContentsMargins(2, 2, 2, 2)
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
            qimage = numpy_to_qimage(image, palette.qt)
            # seems to be not necessary although result is Index8
            #qimage = qimage.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        else:
            height, width = image.shape
            qimage = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
            qimage.fill(0)
        return qimage

    def on_show_toggled(self, state):
        self._show_image = state
        self.channel_changed.emit(self.name)

    def on_new_palette(self, name):
        self._current = str(name)
        self.channel_changed.emit(self.name)


class DisplaySettings(object):

    def __init__(self, default_minimum, default_maximum,
                 disp_minimum=0, disp_maximum=255):
        self.default_minimum = default_minimum
        self.default_maximum = default_maximum
        self.minimum = default_minimum
        self.maximum = default_maximum
        self.set_bitdepth(disp_maximum, disp_minimum)

    def set_bitdepth(self, disp_maximum, disp_minimum=0):
        self.slider_range = disp_maximum - disp_minimum + 1
        self.brightness = self.slider_range / 2.0
        self.contrast = self.slider_range / 2.0
        self.image_minimum = disp_minimum
        self.image_maximum = disp_maximum

    def reset(self):
        self.minimum = self.default_minimum
        self.maximum = self.default_maximum
        self.brightness = self.slider_range / 2.0
        self.contrast = self.slider_range / 2.0

    def set_image_minmax(self, image):
        self.image_minimum = numpy.min(image)
        self.image_maximum = numpy.max(image)

    def set_to_image_minmax(self, image=None):
        if not image is None:
            self.set_image_minmax(image)
        self.minimum = self.image_minimum
        self.maximum = self.image_maximum
        self._update()

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


class EnhancementFrame(QFrame):

    SLIDER_NAMES = ['minimum', 'maximum', 'brightness', 'contrast']

    values_changed = pyqtSignal(str)

    def __init__(self, names, parent, bitdepth=8):
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
            btn.setStyleSheet('QPushButton {'
                              'border: 1px solid #888888;'
                              'border-radius: 3px;'
                              'padding: 2px; font-size: 12px;'
                              'min-width: 40px;}'
                              'QPushButton:checked { background-color: #999999;'
                              'border: 1px solid #444444;}')
            grp.addButton(btn)
            layout_grp.addWidget(btn)
            self._display_settings[name] = DisplaySettings(0, 2**bitdepth)
        layout_grp.addStretch(1)
        layout.addWidget(frame_grp)

        frame = QFrame(self)
        layout_frame = QGridLayout(frame)
        layout_frame.setContentsMargins(2, 0, 2, 0)

        self._sliders = {}
        fct = lambda x: lambda : self.on_slider_changed(x)

        name = 'minimum'
        label = QLabel(name.capitalize(), frame)
        label.setAlignment(Qt.AlignRight)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 2**bitdepth)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 0, 0)
        layout_frame.addWidget(sld, 0, 1)

        name = 'maximum'
        label = QLabel(name.capitalize(), frame)
        label.setAlignment(Qt.AlignRight)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 2**bitdepth)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 1, 0)
        layout_frame.addWidget(sld, 1, 1)

        name = 'brightness'
        label = QLabel(name.capitalize(), frame)
        label.setAlignment(Qt.AlignRight)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 2*bitdepth)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 2, 0)
        layout_frame.addWidget(sld, 2, 1)

        name = 'contrast'
        label = QLabel(name.capitalize(), frame)
        label.setAlignment(Qt.AlignRight)
        sld = QSlider(Qt.Horizontal, frame)
        sld.setRange(0, 2**bitdepth)
        sld.setTickPosition(QSlider.TicksBelow)
        sld.valueChanged.connect(fct(name))
        self._sliders[name] = sld
        layout_frame.addWidget(label, 3, 0)
        layout_frame.addWidget(sld, 3, 1)

        layout.addWidget(frame)

        frame = QFrame(self)
        layout_frame = QBoxLayout(QBoxLayout.LeftToRight, frame)
        layout_frame.setContentsMargins(5, 5, 5, 5)
        btn = QPushButton('Min/Max', self)
        btn.clicked.connect(self.on_minmax)
        layout_frame.addWidget(btn)
        btn = QPushButton('Reset', self)
        btn.clicked.connect(self.on_reset)
        layout_frame.addWidget(btn)
        layout.addWidget(frame)

        if len(grp.buttons()) > 0:
            grp.buttons()[0].setChecked(True)

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

    def on_minmax(self):
        s = self._display_settings[self._current]
        s.set_to_image_minmax()
        self.set_sliders()
        self.values_changed.emit(self._current)

    def on_channel_changed(self, name, state):
        if state:
            self._current = name
            self.set_sliders()

    def transform_image(self, name, image):
        s = self._display_settings[name]
        s.set_image_minmax(image)

        # FIXME: Just a workaround, the image comes with wrong strides
        #        fixed in master
        image2 = numpy.zeros(image.shape, dtype=numpy.float32, order='F')
        image2[:] = image

        # add a small value in case max == min
        image2 *= 255.0 / (s.maximum - s.minimum + 0.1)
        image2 -= s.minimum

        image2 = image2.clip(0, 255)

        image2 = numpy.require(image2, numpy.uint8)
        return image2


class ObjectsFrame(QFrame):

    show_objects_toggled = pyqtSignal('bool')
    show_classify_toggled = pyqtSignal('bool')
    
    object_region_changed = pyqtSignal(str, str)

    def __init__(self, browser, region_names, parent):
        QFrame.__init__(self, parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.show_objects_toggled.connect(browser.on_show_objects)
        self.show_classify_toggled.connect(browser.on_classify_objects)
        self._show_objects = False
        self._classify_objects = False
        self.browser = browser

        box_detect = QCheckBox('Detect Objects', self)
        box_detect.toggled.connect(self._on_show_objects)
        box_detect.setChecked(self._show_objects)
        layout.addWidget(box_detect, 0, 0)
        self._box_detect = box_detect

        box = QComboBox(self)
        box.setEnabled(box_detect.checkState() == Qt.Checked)
        box.addItems(region_names)
        box.currentIndexChanged[str].connect(self._on_current_region_changed)
        if len(region_names) > 0:
            box.setCurrentIndex(0)
        layout.addWidget(box, 1, 0, 1, 2)
        self._box_region = box

        box = QRadioButton('Show Contours', self)
        box.setEnabled(box_detect.checkState() == Qt.Checked)
        box.setChecked(self.browser.image_viewer.show_contours)
        box.toggled.connect(self.browser.on_act_show_contours)
        layout.addWidget(box, 2, 0)
        self._box_contours = box
        
        box_classify = QRadioButton('Classify Objects', self)
        box.setEnabled(box_detect.checkState() == Qt.Checked)
        box.setChecked(self.browser.image_viewer.show_contours)
        box_classify.toggled.connect(self._on_classify_objects)
        box_classify.setChecked(self._classify_objects)
        layout.addWidget(box_classify, 3, 0)
        self._box_classify = box_classify

        self._btn_contour_color = ColorButton(None, self)
        self._btn_contour_color.setEnabled(box_detect.checkState() == Qt.Checked)
        self._btn_contour_color.color_changed.connect(self._on_contour_color_changed)
        # set the color button color and propagate the color to the observers
        color = QColor('white')
        color.setAlphaF(0.5)
        self._btn_contour_color.set_color(color)
        layout.addWidget(self._btn_contour_color, 2, 1)

        self.browser.show_contours_toggled.connect(self._on_set_contour_state)

    def _on_current_region_changed(self, name):
        channel, region = name.split(' - ')
        self.object_region_changed.emit(channel, region)

    def _on_show_objects(self, state):
        self._box_region.setEnabled(state)
        self._box_contours.setEnabled(state)
        self._box_classify.setEnabled(state)
        self._btn_contour_color.setEnabled(state)
        self.show_objects_toggled.emit(state)
        
    def _on_classify_objects(self, state):
        self.show_classify_toggled.emit(state)

    def _on_set_contour_state(self, state):
        self._box_contours.blockSignals(True)
        self._box_contours.setChecked(state)
        self._box_contours.blockSignals(False)

    def _on_contour_color_changed(self, color):
        self.browser.image_viewer.set_contour_color(color)


class DisplayFrame(QFrame):

    def __init__(self, browser, parent):
        QFrame.__init__(self, parent)
        layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        layout.setContentsMargins(5, 5, 5, 5)
        btn = QPushButton('100%', self)
        btn.clicked.connect(browser.on_act_zoom100)
        layout.addWidget(btn)
        btn = QPushButton('Fit', self)
        btn.clicked.connect(browser.on_act_zoomfit)
        layout.addWidget(btn)
        btn = QPushButton('+', self)
        btn.clicked.connect(browser.on_act_zoomin)
        layout.addWidget(btn)
        btn = QPushButton('-', self)
        btn.clicked.connect(browser.on_act_zoomout)
        layout.addWidget(btn)


class DisplayModule(Module):

    NAME = 'Display'
    object_region_changed = pyqtSignal(str, str)

    def __init__(self, parent, browser, image_container, region_names):
        Module.__init__(self, parent, browser)
        self._imagecontainer = image_container
        self._image_dict = {}
        self._display_images = {}
        self._rgb_images = {}

        palettes = self.import_palettes()

        self.object_region_changed.connect(browser.on_object_region_changed)

        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        layout.setContentsMargins(5, 5, 5, 5)

        frame_channels = QGroupBox('Channels', self)
        layout_channels = QBoxLayout(QBoxLayout.TopToBottom, frame_channels)
        layout_channels.setContentsMargins(10, 12, 7, 10)
        frame_enhance = QGroupBox('Image Enhancement', self)
        layout_enhance = QBoxLayout(QBoxLayout.TopToBottom, frame_enhance)
        layout_enhance.setContentsMargins(5, 10, 5, 5)
        frame_objects = QGroupBox('Objects', self)
        layout_objects = QBoxLayout(QBoxLayout.TopToBottom, frame_objects)
        layout_objects.setContentsMargins(5, 10, 5, 5)
        frame_display = QGroupBox('Display', self)
        layout_display = QBoxLayout(QBoxLayout.TopToBottom, frame_display)
        layout_display.setContentsMargins(5, 10, 5, 5)

        layout.addSpacing(15)
        layout.addWidget(frame_channels)
        layout.addSpacing(7)
        layout.addWidget(frame_enhance)
        layout.addSpacing(7)
        layout.addWidget(frame_display)
        layout.addSpacing(7)
        layout.addWidget(frame_objects)
        layout.addStretch(1)

        self._channels = OrderedDict()
        channel_names = sorted(self._imagecontainer.channels)
        for idx, channel_name in enumerate(channel_names):
            widget = ChannelItem(channel_name, idx, palettes, self)
            layout_channels.addWidget(widget)
            self._channels[channel_name] = widget
            widget.channel_changed.connect(self.on_channel_changed)

        self._enhancement = EnhancementFrame(channel_names, frame_enhance)
        self._enhancement.values_changed.connect(self.on_display_changed)
        layout_enhance.addWidget(self._enhancement)

        display = ObjectsFrame(browser, region_names, frame_objects)
        display.object_region_changed.connect(self.on_object_region_changed)
        layout_objects.addWidget(display)

        display = DisplayFrame(browser, frame_display)
        layout_display.addWidget(display)

    def import_palettes(self):
        palettes = OrderedDict()

        for name in DEFAULT_LUT_COLORS:
            p = SingleColorPalette.from_hex_color(name, COLOR_DEFINITIONS[name])
            palettes[p.name] = p
        # iterator over palettes
        path_zeiss = os.path.join(CecogEnvironment.RESOURCE_DIR,
                                  'palettes', 'zeiss')
        for filename in collect_files(path_zeiss, ['.zip'], absolute=True):
            with zipfile.ZipFile(filename, 'r') as f:
                name = f.namelist()[0]
                data = f.read(name)
            name = os.path.splitext(name)[0]
            p = ZeissPalette(name, data)
            palettes[p.name] = p
        for palette in palettes.values():
            # FIXME: not optimal, mixin required for Qt purposes
            palette.qt = [qRgb(r, g, b) for r,g,b in palette.lut]
        return palettes

    def set_image_dict(self, image_dict):
        self._image_dict.clear()
        for name, image in image_dict.iteritems():
            if not name in self._image_dict:
                self._image_dict[name] = ImageHelper(image)
        self._display_images.clear()
        self._rgb_images.clear()
        self.update_display()
        self.update_renderer()

    def update_display(self, restrict=None):
        for name, image_helper in self._image_dict.iteritems():
            image = image_helper.array
            if restrict is None or restrict == name:
                image = self._enhancement.transform_image(name, image)
                self._display_images[name] = image

    def update_renderer(self, restrict=None):
        for name, image in self._display_images.iteritems():
            widget = self._channels[name]
            if restrict is None or restrict == name:
                rgb_image = widget.render_image(image)
                self._rgb_images[name] = rgb_image
        rgb_images = self._rgb_images.values()
        self.browser.image_viewer.from_pixmap(blend_images_max(rgb_images))

    def on_object_region_changed(self, channel, region):
        self.object_region_changed.emit(channel, region)

    def on_channel_changed(self, name):
        name = str(name)
        self.update_renderer(restrict=name)

    def on_display_changed(self, name):
        # in case all channels are changed no restriction applies
        if not name is None:
            name = str(name)
        self.update_display(restrict=name)
        self.update_renderer(restrict=name)

    def set_object_dict(self, d):
        pass
