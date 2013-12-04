from cecog import ccore
from cecog.io.imagecontainer import Coordinate

import numpy

import os, sys, re, time, pickle

from collections import OrderedDict

from scripts.EMBL.plotter import colors

class Panel(object):
    """Abstract class for panel generation
       Panels are used in Single-Cell-HTML-pages
       to decorate the single-cell galleries"""
    def __init__(self, single_image_width, panel_height=5,
                 background_color='#FFFFFF'):
        self.single_image_width = single_image_width
        self.panel_height = panel_height
        self.cm = colors.ColorMap()
        self.bg_color = background_color

    def _convertColor(self, color_str):
        col = [int(round(255 * float(x)))
               for x in self.cm.getRGBValues([color_str])[0]]
        cecog_col = ccore.RGBValue(*col)
        return cecog_col

    def _setBackgroundColor(self, imout):

        col = self._convertColor(self.bg_color)

        for y in range(imout.height):
            ccore.drawLine(ccore.Diff2D(0, y),
                           ccore.Diff2D(imout.width, y),
                           imout, col, False)

        return

class ClassificationPanel(Panel):
    """ClassificationPanel
       generates a panel to illustrated classification results, i.e.
       a series of colored rectangles, each of them representing one classification result.
       usage:
       >>> from scripts.EMBL.cutter.data_for_cutouts import *
       >>> cp = ClassificationPanel(single_image_width=50, panel_height=5)
       >>> cp("classficiationpanel.png", ['#AA0000', '#11BB22', '#11BB22', '#AA0000'])"""
    def __call__(self, filename, color_vector):
        nb_fields = len(color_vector)
        imout = ccore.RGBImage(nb_fields * self.single_image_width,
                               self.panel_height)
        colvec = [self._convertColor(x) for x in color_vector]
        for i in range(nb_fields):
            col = colvec[i]
            x = i * self.single_image_width
            for y in range(self.panel_height):
                ccore.drawLine(ccore.Diff2D(x, y),
                               ccore.Diff2D(x + self.single_image_width, y),
                               imout, col, False)
        ccore.writeImage(imout, filename)
        return

class TickPanel(Panel):
    """TickPanel
       generates a panel with the ticks, each placed at the middle of one cut-out image
       typically used in conjunction with DelayPanel
       usage:
       >>> from scripts.EMBL.cutter.data_for_cutouts import *
       >>> tp = TickPanel(single_image_width=50, panel_height=5)
       >>> tp("tickpanel.png", track_len=10)"""

    # color_vector can be any list; only the length of the list is important
    # (in order to make is more coherent with ClassficiationPanel)
    def __call__(self, filename, color_vector=None, track_len=None):
        if color_vector is None and track_len is None:
            raise ValueError("either a vector or the gallery length must be given.")
        if not color_vector is None and not track_len is None:
            if not len(color_vector) == track_len:
                raise ValueError("vector and gallery length are not compatible.")
        if color_vector is None:
            nb_fields = track_len
        else:
            nb_fields = len(color_vector)

        half_size = self.single_image_width / 2

        imout = ccore.RGBImage(nb_fields * self.single_image_width,
                               self.panel_height)
        if not color_vector is None:
            colvec = [self._convertColor(x) for x in color_vector]
        else:
            colvec = None

        # dirty hack for settings the background color
        # basically, lines in the background color are drawn.
        self._setBackgroundColor(imout)

        for i in range(nb_fields):
            if not colvec is None:
                col = colvec[i]
            else:
                # default for ticks is dark grey
                col = ccore.RGBValue(80,80,80)
            x = i * self.single_image_width + half_size

            ccore.drawLine(ccore.Diff2D(x, 0),
                           ccore.Diff2D(x, self.panel_height),
                           imout, col, False)
        ccore.writeImage(imout, filename)
        return

class DelayPanel(Panel):
    """DelayPanel
       generates a panel with the delay durations.
       For this, the time_lapse and event_index have to be given to the constructor,
       time_lapse being the time between two frames (default = 1) and
       event_index being the frame index (starting from 0) at which the selected event
       occurs.
       usage:
       >>> from scripts.EMBL.cutter.data_for_cutouts import *
       >>> dp = DelayPanel(single_image_width=50, panel_height=5, time_lapse=2, event_index=3)
       >>> dp("delaypanel.png", [(2.2, 2.5, '#A02000'), (4.5, 6.7, '#00EE66)], track_len=10)"""
    def __init__(self, single_image_width, panel_height=5,
                 time_lapse=1, event_index=0):
        self.time_lapse = time_lapse
        self.event_index = event_index
        Panel.__init__(self, single_image_width, panel_height)

    # timepoints is a list of the form [(start, end, (color)), (start, end, (color)), ... ]
    def __call__(self, filename, timepoints, track_len):

        nb_fields = track_len

        half_size = self.single_image_width / 2

        imout = ccore.RGBImage(nb_fields * self.single_image_width,
                               self.panel_height)

        self._setBackgroundColor(imout)

        self.default_colors = self.cm.makeDivergentColorRamp(len(timepoints))
        i = 0
        for line_val in timepoints:
            start_time = line_val[0]
            end_time = line_val[1]
            if len(line_val) > 2:
                col = self._convertColor(line_val[2])
            else:
                col = self._convertColor(default_colors[i])

            start_frame = start_time / self.time_lapse + self.event_index
            x_start = int(start_frame * self.single_image_width + half_size)

            end_frame = end_time / self.time_lapse + self.event_index
            x_end = int(end_frame * self.single_image_width + half_size)

            ccore.drawLine(ccore.Diff2D(x_start, 0),
                           ccore.Diff2D(x_start, self.panel_height),
                           imout, col, False)
            ccore.drawLine(ccore.Diff2D(x_end, 0),
                           ccore.Diff2D(x_end, self.panel_height),
                           imout, col, False)
            ccore.drawLine(ccore.Diff2D(x_start, (self.panel_height / 2)),
                           ccore.Diff2D(x_end, (self.panel_height / 2)),
                           imout, col, False)

            i += 1

        ccore.writeImage(imout, filename)

        return

