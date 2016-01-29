"""
eventviewer.py
"""

__author__ = 'christoph.sommer@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ('CellH5EventModule', )

import numpy

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from cecog.gui.imageviewer import QGraphicsPixmapHoverItem
from cecog.gui.modules.module import CH5BasedModule

from qimage2ndarray import array2qimage
import cellh5


class CellH5EventModule(CH5BasedModule):

    NAME = 'Event Viewer'

    def __init__(self, parent, browser, settings, imagecontainer):
        super(CellH5EventModule, self).__init__(parent, browser, settings, imagecontainer)
        self.layout = QVBoxLayout(self)

        self.x_max = 100000

    def initialize(self):
        super(CellH5EventModule, self).initialize()
        self._init_pos_table()
        self._init_event_table()
        self._init_options_box()
        self._fill_coordinate_table()

        self.pos_table.resizeColumnsToContents()
        self.pos_table.resizeRowsToContents()

        self.browser.image_viewers['gallery'].image_mouse_pressed.connect(
            self._on_new_point)


    def _fill_coordinate_table(self):
        for i, coord in enumerate(self.coordinates):
            self.pos_table.insertRow(i)
            w_item = QTableWidgetItem(coord.well)
            p_item = QTableWidgetItem(coord.site)
            pl_item = QTableWidgetItem(self.ch5file.plate)
            self.pos_table.setItem(i, 0, pl_item)
            self.pos_table.setItem(i, 1, w_item)
            self.pos_table.setItem(i, 2, p_item)

    def update_event_table(self, coord):

        pos = self.ch5file.get_position_from_coord(coord)

        try:
            events = pos.get_event_items()
        except KeyError as ke:
            QMessageBox.critical(
                self, "Error",
                ("No event data found in CellH5. Make sure tracking "
                 "and event selection has been enabled! ('%s)'"% str(ke)))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.event_table.setRowCount(0)

        selected_track = []
        start_ids = map(lambda x: x[1][0], events)
        time_idxs = pos.get_time_indecies(start_ids)

        self.tracks = []
        cnt = 0
        for (e_id, e), time_idx in zip(events, time_idxs):
            QApplication.processEvents()
            if self._cb_track.checkState():
                track = e[:-1] + pos.track_first(e[-1])
            else:
                track = e


            selected_track.append(e)
            self.event_table.insertRow(cnt)

            event_id_item = QTableWidgetItem()
            event_id_item.setData(Qt.DisplayRole, e_id)

            self.event_table.setItem(cnt, 0, event_id_item)
            tmp_i = QTableWidgetItem()
            tmp_j = QTableWidgetItem()

            # to make sorting according to numbers
            tmp_i.setData(Qt.DisplayRole, len(track))
            tmp_j.setData(Qt.DisplayRole, int(time_idx))

            self.event_table.setItem(cnt, 1, tmp_i)
            self.event_table.setItem(cnt, 2, tmp_j)

            if cnt == 0:
                self.event_table.resizeRowsToContents()
                self.event_table.resizeColumnsToContents()

            cnt+=1
            self.tracks.append(track)


        self.event_table.resizeRowsToContents()
        self.event_table.resizeColumnsToContents()
        self.event_table.setSortingEnabled(True)

    def _init_pos_table(self):
        self.pos_table = QTableWidget(self)
        self.pos_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pos_table.setSelectionMode(QTableWidget.SingleSelection)
        self.pos_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pos_table.setColumnCount(3)
        self.pos_table.setHorizontalHeaderLabels(['Plate', 'Well', 'Site'])
        self.pos_table.resizeColumnsToContents()
        self.pos_table.currentItemChanged.connect(self._on_pos_changed)
        self.pos_table.setStyleSheet('font-size: 10px;')
        self.layout.addWidget(self.pos_table)

    def _init_event_table(self):
        self.event_table = QTableWidget(self)
        self.event_table.setToolTip("Use CTRL button to select multiple events")
        self.event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.event_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.event_table.setColumnCount(3)
        self.event_table.setHorizontalHeaderLabels(['Event Id', 'Event Length', 'Start Frame',])
        self.event_table.resizeColumnsToContents()
        self.event_table.itemSelectionChanged.connect(self._on_track_changed)
        self.event_table.setStyleSheet('font-size: 10px;')
        self.layout.addWidget(self.event_table)

    def _init_options_box(self):
        grp_box = QGroupBox('Options', self)
        grp_layout = QVBoxLayout(grp_box)

        padding = (5,0,0,5)

        grp_layout.setContentsMargins(5,10,5,5)

        # object type
        frame = QWidget(self)
        layout = QHBoxLayout(frame)
        layout.addWidget(QLabel('Regions'))
        layout.setContentsMargins(*padding)
        self._cbb_object = QComboBox()
        for o in self.ch5file.object_definition.keys():
            if self.ch5file.has_object_features(o):
                self._cbb_object.addItem(str(o))
        layout.addWidget(self._cbb_object)
        self._cbb_object.currentIndexChanged.connect(self._cbb_object_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # fate tracking
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        self._cb_track = QCheckBox('Event Fate', self)
        self._cb_track.setCheckState(False)
        self._cb_track.stateChanged.connect(self._cb_track_changed)
        layout.addWidget(self._cb_track)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # Cells per row
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        layout.addWidget(QLabel('Cells per row'))
        self._sb_gallery_perrow = QSpinBox(self)
        self._sb_gallery_perrow.setMinimum(-1)
        self._sb_gallery_perrow.setValue(-1)
        self._sb_gallery_perrow.setMaximum(1000)
        self._sb_gallery_perrow.setSingleStep(1)
        layout.addWidget(self._sb_gallery_perrow)
        self._sb_gallery_perrow.valueChanged.connect(self._sb_gallery_perrow_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # Gallery Size
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        layout.addWidget(QLabel('Gallery Size'))
        self._sb_gallery_size = QSpinBox(self)
        self._sb_gallery_size.setValue(60)
        self._sb_gallery_size.setMinimum(60)
        self._sb_gallery_size.setSingleStep(10)
        layout.addWidget(self._sb_gallery_size)
        self._sb_gallery_size.valueChanged.connect(self._sb_gallery_size_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # Image Min Image Maxe
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        layout.addWidget(QLabel('Min:'))
        self._sb_image_min = QSlider(Qt.Horizontal, self)
        self._sb_image_min.setValue(0)
        self._sb_image_min.setSingleStep(10)
        layout.addWidget(self._sb_image_min)
        layout.addWidget(QLabel('Max:'))
        self._sb_image_max = QSlider(Qt.Horizontal, self)
        self._sb_image_max.setMinimum(0)
        self._sb_image_max.setMaximum(255)
        self._sb_image_max.setValue(255)
        self._sb_image_max.setSingleStep(10)
        layout.addWidget(self._sb_image_max)

        self._sb_image_min.valueChanged.connect(self._sb_gallery_size_changed)
        self._sb_image_max.valueChanged.connect(self._sb_gallery_size_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # show id
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        self._cb_show_id = QCheckBox('Show Event ID', self)
        self._cb_show_id.setTristate(False)
        self._cb_show_id.setCheckState(Qt.Unchecked)
        layout.addWidget(self._cb_show_id)

        self._cb_show_id.stateChanged.connect(self._cb_show_id_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # show seg
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        self._cb_segmentation = QCheckBox('Show Segmentation', self)
        self._cb_segmentation.setCheckState(False)
        layout.addWidget(self._cb_segmentation)

        self._cb_segmentation.stateChanged.connect(self._cb_segmentation_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        # show classificaton
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(*padding)
        self._cb_classification = QCheckBox('Show Classification', self)
        self._cb_classification.setCheckState(False)
        layout.addWidget(self._cb_classification)
        self._cb_classification.stateChanged.connect(self._cb_classification_changed)

        frame.setLayout(layout)
        grp_layout.addWidget(frame)

        self.layout.addWidget(grp_box)

    def _cb_track_changed(self, check_state):
        self.update_event_table(self.cur_coord)
        self.show_tracks(self.cur_tracks)

    def _cb_show_id_changed(self, check_state):
        self.show_tracks(self.cur_tracks)

    def _cb_segmentation_changed(self, check_state):
        self.show_tracks(self.cur_tracks)

    def _cb_classification_changed(self, check_state):
        if check_state > 0:
            self._cb_segmentation.setCheckState(2)
            return
        self.show_tracks(self.cur_tracks)

    def _sb_gallery_perrow_changed(self, value):
        if value < 0:
            self.x_max = 100000
        else:
            self.x_max = value
        self.show_tracks(self.cur_tracks)

    def _sb_gallery_size_changed(self, value):
        self.show_tracks(self.cur_tracks)

    def _cbb_object_changed(self, value):
        self.show_tracks(self.cur_tracks)

    def activate(self):
        super(CellH5EventModule, self).activate()
        self.browser.set_display_module(self)
        self.browser.set_image_viewer('gallery')
        self.browser._action_grp.setEnabled(True)
        self.browser._t_slider.setVisible(False)

    def deactivate(self):
        self.browser.set_display_module(self.browser._module_manager.get_widget('Display'))
        self.browser.set_image_viewer('image')
        self.browser._action_grp.setEnabled(False)
        self.browser._t_slider.setVisible(True)

    def _on_pos_changed(self, current, previous):

        w = str(self.pos_table.item(current.row(), 1).text())
        p = str(self.pos_table.item(current.row(), 2).text())

        coord = cellh5.CH5PositionCoordinate(self.ch5file.plate, w, p)

        pos = self.ch5file.get_position_from_coord(coord)
        self.cur_pos = pos
        self.cur_w = w
        self.cur_p = p
        self.cur_coord = coord
        self.update_event_table(coord)

    def _on_track_changed(self):
        indexes = self.event_table.selectionModel().selectedRows()

        res = []
        for index in sorted(indexes):
            track_idx = index.row()
            track_id = int(self.event_table.item(track_idx, 0).text())
            res.append((track_idx, track_id))

        self.cur_tracks = res

        self.show_tracks(res)

    def _on_new_point(self, point, button, modifier):
        pass

    def show_tracks(self, res):
        self.browser.image_viewer.clear()
        pos = self.cur_pos
        cellh5.GALLERY_SIZE = self._sb_gallery_size.value()
        step = cellh5.GALLERY_SIZE

        init_y_offset = 30
        init_x_offset = 30

        x, y = init_x_offset, 0

        object_ = str(self._cbb_object.currentText())

        for idx, track_id in res:
            track = self.tracks[idx]
            if self._cb_show_id.checkState():
                event_text_item = QGraphicsTextItem()
                event_text_item.setHtml("<span style='color:white; font:bold 12px'>Well: %s Position: %s Track Id: %s</span>" % (self.cur_w, self.cur_p, track_id))
                event_text_item.setPos(0, y-init_y_offset)
                self.browser.image_viewer._scene.addItem(event_text_item)

            for i, gallery_numpy in enumerate(pos.get_gallery_image_generator(track, object_)):
                gallery_item = QGraphicsPixmapHoverItem(QPixmap(array2qimage(self.transform_image(gallery_numpy), False )))
                gallery_item.setPos(x, y)
                self.browser.image_viewer._scene.addItem(gallery_item)

                if self._cb_segmentation.checkState():
                    contour_item = QGraphicsPolygonItem(
                        QPolygonF(map(lambda x: QPointF(x[0],x[1]),
                                      self.cur_pos.get_crack_contour(track[i],object_)[0])))
                    contour_item.setPos(x,y)
                    color = Qt.red
                    if self._cb_classification.checkState():
                        color = QColor(self.cur_pos.get_class_color(track[i]))
                    pen = QPen(color)
                    pen.setWidth(0.0)
                    contour_item.setPen(pen)
                    contour_item.setZValue(4)

                    self.browser.image_viewer._scene.addItem(contour_item)

                x += step
                if (x / step) >= self.x_max:
                    x = init_x_offset
                    y += step
            x = init_x_offset
            y += step
            if self._cb_show_id.checkState():
                y += step

    def transform_image(self, image):
        image = image.astype(numpy.float32)
        image *= 255.0 / (self._sb_image_max.value() - self._sb_image_min.value() )
        image -= self._sb_image_min.value()

        image = image.clip(0, 255)

        image2 = numpy.require(image, numpy.uint8)

        return image2
