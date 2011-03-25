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
import time as time_lib

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

import numpy

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.modules.module import Module
from cecog.util.util import yesno
from cecog.io.imagecontainer import Coordinate

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#

class NavigationModule(Module):

    NAME = 'Navigation'

    coordinate_changed = pyqtSignal(Coordinate)

    def __init__(self, parent, browser, imagecontainer):
        Module.__init__(self, parent, browser)

        self._imagecontainer = imagecontainer

        frame_info = QGroupBox('Plate Information', self)
        layout = QGridLayout(frame_info)
        frame_info.setStyleSheet('QLabel { font-size: 10px }')
        self._label_info = QLabel(frame_info)
        layout.addWidget(self._label_info, 0, 0, 0, 0,
                         Qt.AlignCenter | Qt.AlignHCenter)

        splitter = QSplitter(Qt.Vertical, self)
        splitter.setMinimumWidth(40)

        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter)

        grp1 = QGroupBox('Plates', splitter)
        grp2 = QGroupBox('Positions', splitter)
        splitter.addWidget(grp1)
        splitter.addWidget(grp2)

        layout = QGridLayout(grp1)
        layout.setContentsMargins(5, 10, 5, 5)

        table = QTableWidget(grp1)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet('font-size: 10px;')
        table.currentItemChanged.connect(self._on_plate_changed)
        self._table_plate = table
        layout.addWidget(table, 0, 0)

        self._update_plate_table()

        layout = QGridLayout(grp2)
        layout.setContentsMargins(5, 10, 5, 5)

        table = QTableWidget(grp2)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet('font-size: 10px;')
        table.currentItemChanged.connect(self._on_position_changed)
        self._table_position = table
        layout.addWidget(table, 0, 0)

        if self._imagecontainer.has_timelapse:
            grp3 = QGroupBox('Time', splitter)
            splitter.addWidget(grp3)

            layout = QGridLayout(grp3)
            layout.setContentsMargins(5, 10, 5, 5)

            table = QTableWidget(grp3)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            table.setStyleSheet('font-size: 10px;')
            table.currentItemChanged.connect(self._on_time_changed)
            self._table_time = table
            layout.addWidget(table, 0, 0)

        splitter.addWidget(frame_info)

    def _update_plate_table(self):
        table = self._table_plate
        table.blockSignals(True)
        table.clearContents()

        column_names = ['Plate ID']
        table.setColumnCount(len(column_names))
        table.setHorizontalHeaderLabels(column_names)
        plates = self._imagecontainer.plates
        table.setRowCount(len(plates))

        for idx, plate in enumerate(plates):
            item = QTableWidgetItem(plate)
            item.setData(0, plate)
            table.setItem(idx, 0, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.blockSignals(False)

    def _update_time_table(self, meta_data, coordinate):
        coordinate = coordinate.copy()
        table = self._table_time
        table.blockSignals(True)
        table.clearContents()

        column_names = ['Frame']
        if meta_data.has_timestamp_info:
            column_names += ['rel. t (min)', 'abs. t (GMT)']
        table.setColumnCount(len(column_names))
        table.setHorizontalHeaderLabels(column_names)
        table.setRowCount(len(meta_data.times))

        for idx, time in enumerate(meta_data.times):
            item = QTableWidgetItem(str(time))
            item.setData(0, time)
            table.setItem(idx, 0, item)

            if meta_data.has_timestamp_info:
                coordinate.time = time
                ts_rel = meta_data.get_timestamp_relative(coordinate)
                ts_abs = meta_data.get_timestamp_absolute(coordinate)
                if not numpy.isnan(ts_rel):
                    info = '%.1f' % (ts_rel / 60)
                    table.setItem(idx, 1, QTableWidgetItem(info))
                if not numpy.isnan(ts_abs):
                    info = time_lib.strftime("%Y-%m-%d %H:%M:%S",
                                             time_lib.gmtime(ts_abs))
                    table.setItem(idx, 2, QTableWidgetItem(info))
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.blockSignals(False)

    def _update_position_table(self, meta_data):
        table = self._table_position
        table.blockSignals(True)
        table.clearContents()

        column_names = ['Position']
        if meta_data.has_well_info:
            column_names += ['Well', 'Subwell']
        if meta_data.has_condition_info:
            column_names.append('Condition')
        if meta_data.has_timestamp_info and meta_data.has_timelapse:
            column_names.append('Time-lapse')

        table.setColumnCount(len(column_names))
        table.setHorizontalHeaderLabels(column_names)
        table.setRowCount(len(meta_data.positions))

        for idx, pos in enumerate(meta_data.positions):
            item = QTableWidgetItem(pos)
            item.setData(0, pos)
            table.setItem(idx, 0, item)

            if 'Time-lapse' in column_names:
                column = column_names.index('Time-lapse')
                info = meta_data.get_timestamp_info(pos)
                info_str = '%.1fmin (%.1fs)' % (info[0] / 60, info[1])
                table.setItem(idx, column, QTableWidgetItem(info_str))

            if 'Well' in column_names:
                column = column_names.index('Well')
                well, subwell = meta_data.get_well_and_subwell(pos)
                if not well is None:
                    table.setItem(idx, column, QTableWidgetItem(well))
                if not subwell is None:
                    table.setItem(idx, column+1, QTableWidgetItem(subwell))

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.blockSignals(False)

    def _update_info_frame(self, meta_data):
        meta = meta_data
        txt  = '<table>' \
               '<tr><td align="right">Positions: </td><td>%s</td></tr>' \
               '<tr><td align="right">Frames: </td><td>%d</td></tr>' % \
               (meta.dim_p, meta.dim_t)
        txt += '<tr><td align="right">Channels: </td><td>%d (%s)</td></tr>' \
               '<tr><td align="right">Z-slices: </td><td>%d</td></tr>' \
               '<tr><td align="right">Width / Height: </td><td>%d x %d</td></tr>' \
               '<tr><td colspan="2"></td></tr>' \
               '<tr><td align="right">Image Files: </td><td>%d</td></tr>' % \
               (meta.dim_c, meta.pixel_info, meta.dim_z, meta.dim_x,
                meta.dim_y, meta.image_files)
        txt += '<tr><td></td></tr>'
        if meta.has_timestamp_info and meta.has_timelapse:
            info = meta.plate_timestamp_info
            txt += \
               '<tr><td align="right">Time-lapse info: </td><td>%.1f min (+/- %.1f s)</td></tr>' % \
               (info[0]/60, info[1])
        else:
            txt += '<tr><td align="right">Time-lapse info: </td><td>no</td></tr>'

        txt += '<tr><td align="right">Well info: </td><td>%s</td></tr>' % \
               yesno(meta.has_well_info)
        txt += '<tr><td align="right">Condition info: </td><td>%s</td></tr>' % \
               yesno(meta.has_condition_info)
        txt += '</table>'
        self._label_info.setText(txt)

    def initialize(self):
        self.coordinate_changed.connect(self.browser.on_coordinate_changed)
        coordinate = self.browser.get_coordinate()
        meta_data = self._imagecontainer.get_meta_data(coordinate.plate)
        self._update_position_table(meta_data)
        self._update_info_frame(meta_data)

        self._set_current_plate(coordinate.plate)
        self._set_current_position(coordinate.position)

        if self._imagecontainer.has_timelapse:
            self._update_time_table(meta_data, coordinate)
            self._set_current_time(coordinate.time)

    def nav_to_coordinate(self, coordinate):
        """
        Set the browser coordinate to a coordinate and emit signal
        """
        meta_data = self._imagecontainer.get_meta_data(coordinate.plate)
        self._set_current_plate(coordinate.plate)
        self._update_position_table(meta_data)
        self._set_current_position(coordinate.position)
        if self._imagecontainer.has_timelapse:
            meta_data = self._imagecontainer.get_meta_data(coordinate.plate)
            self._update_time_table(meta_data, coordinate)
            self._set_current_time(coordinate.time)
        self._update_info_frame(meta_data)
        self.coordinate_changed.emit(coordinate)

    def nav_to_time(self, time):
        """
        Set the browser coordinate to a coordinate and emit signal
        """
        coordinate = self.browser.get_coordinate()
        coordinate.time = time
        self._set_time(coordinate, True)

    def nav_to_prev_position(self):
        coordinate = self.browser.get_coordinate()
        meta_data = self._imagecontainer.get_meta_data(coordinate.plate)
        pos = meta_data.positions
        idx = pos.index(coordinate.position)
        if idx > 0:
            coordinate.position = pos[idx-1]
            self._set_position(coordinate, True)

    def nav_to_next_position(self):
        coordinate = self.browser.get_coordinate()
        meta_data = self._imagecontainer.get_meta_data(coordinate.plate)
        pos = meta_data.positions
        idx = pos.index(coordinate.position)
        if idx < len(pos)-1:
            coordinate.position = pos[idx+1]
            self._set_position(coordinate, True)

    def nav_to_prev_plate(self):
        coordinate = self.browser.get_coordinate()
        plates = self._imagecontainer.plates
        idx = plates.index(coordinate.plate)
        if idx > 0:
            coordinate.plate = plates[idx-1]
            self._set_plate(coordinate, True)

    def nav_to_next_plate(self):
        coordinate = self.browser.get_coordinate()
        plates = self._imagecontainer.plates
        idx = plates.index(coordinate.plate)
        if idx < len(plates)-1:
            coordinate.plate = plates[idx+1]
            self._set_plate(coordinate, True)

    def _get_closeby_position(self, coordinate_old, coordinate_new):
        #md_old = self._imagecontainer.get_meta_data(coordinate_old.plate)
        md_new = self._imagecontainer.get_meta_data(coordinate_new.plate)
        if coordinate_old.position in md_new.positions:
            coordinate_new.position = coordinate_old.position
        else:
            coordinate_new.position = md_new.positions[0]

    def _get_closeby_time(self, coordinate_old, coordinate_new):
        #md_old = self._imagecontainer.get_meta_data(coordinate_old.plate)
        md_new = self._imagecontainer.get_meta_data(coordinate_new.plate)
        if coordinate_old.time in md_new.times:
            coordinate_new.time = coordinate_old.time
        else:
            coordinate_new.time = md_new.times[0]

    def _on_plate_changed(self, current, previous):
        coordinate_new = self.browser.get_coordinate()
        item = self._table_plate.item(current.row(), 0)
        plate = item.data(0).toPyObject()
        coordinate_new.plate = plate
        self._set_plate(coordinate_new)

    def _set_plate(self, coordinate_new, set_current=False):
        coordinate_old = self.browser.get_coordinate()
        plate = coordinate_new.plate
        meta_data = self._imagecontainer.get_meta_data(plate)
        if set_current:
            self._set_current_plate(plate)
        self._update_position_table(meta_data)
        self._get_closeby_position(coordinate_old, coordinate_new)
        self._set_current_position(coordinate_new.position)
        if self._imagecontainer.has_timelapse:
            meta_data = self._imagecontainer.get_meta_data(plate)
            self._update_time_table(meta_data, coordinate_new)
            self._get_closeby_time(coordinate_old, coordinate_new)
            self._set_current_time(coordinate_new.time)
        self._update_info_frame(meta_data)
        self.coordinate_changed.emit(coordinate_new)

    def _on_position_changed(self, current, previous):
        coordinate = self.browser.get_coordinate()
        item = self._table_position.item(current.row(), 0)
        position = item.data(0).toPyObject()
        coordinate.position = position
        self._set_position(coordinate)

    def _set_position(self, coordinate, set_current=False):
        if set_current:
            self._set_current_position(coordinate.position)
        if self._imagecontainer.has_timelapse:
            meta_data = self._imagecontainer.get_meta_data(coordinate.plate)
            self._update_time_table(meta_data, coordinate)
            self._set_current_time(coordinate.time)
        self.coordinate_changed.emit(coordinate)

    def _on_time_changed(self, current, previous):
        coordinate = self.browser.get_coordinate()
        item = self._table_time.item(current.row(), 0)
        time = int(item.data(0).toPyObject())
        coordinate.time = time
        self._set_time(coordinate)

    def _set_time(self, coordinate, set_current=False):
        if set_current:
            self._set_current_time(coordinate.time)
        self.coordinate_changed.emit(coordinate)

    def _set_current_plate(self, plate):
        self._table_plate.blockSignals(True)
        item = self._table_plate.findItems(plate, Qt.MatchExactly)[0]
        self._table_plate.setCurrentItem(item)
        self._table_plate.blockSignals(False)
        self._table_plate.scrollToItem(item)
        self._table_plate.update()

    def _set_current_position(self, position):
        self._table_position.blockSignals(True)
        item = self._table_position.findItems(position, Qt.MatchExactly)[0]
        self._table_position.setCurrentItem(item)
        self._table_position.blockSignals(False)
        self._table_position.scrollToItem(item)
        self._table_position.update()

    def _set_current_time(self, time):
        if self._imagecontainer.has_timelapse:
            self._table_time.blockSignals(True)
            item = self._table_time.findItems(str(time), Qt.MatchExactly)[0]
            self._table_time.setCurrentItem(item)
            self._table_time.blockSignals(False)
            self._table_time.scrollToItem(item)
            self._table_time.update()
