"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import
from six.moves import zip

__author__ = 'Michael Held, Thomas Walter'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ('AxisIterator', 'ImageContainer')

import os
import copy
import types
from collections import OrderedDict

from cecog.io.metadata import MetaImage
from cecog.io.importer import IniFileImporter
from cecog.environment import CecogEnvironment
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL


class AxisIterator(object):
    """
    Concept of iterator-generator chains, which are linked according the given
    experiment scan-order and result in nested loops of scan-order dimensions.

    e.g. for scan-order PTCZYX the generators are linked:
      P->T->C->Z where the last returns the XY image (here a MetaImage instance)

    The definition of break-points allows to yield a generator at any nd-space,
    which can yield a generator of the sub-space again or directly return the
    XY-images in the their scan-order.
    """

    def __init__(self, image_container, selected_values, possible_values,
                 name=None, interrupt=False, next_iter=None):
        self.image_container = image_container
        self.next_iter = next_iter
        self.interrupt = interrupt
        self.name = name
        # iterate on all possible values
        if selected_values is None:
            self.values = possible_values
        # iterate on the a given sequence of values
        elif type(selected_values) in [list, tuple]:
            self.values = selected_values
        # iterate just on one given value
        elif selected_values in possible_values:
            self.values = [selected_values]
        else:
            raise ValueError("Dimension %s: "
                             "Value %s not available. Candidates are %s." %
                             (name, selected_values, possible_values))

    def __str__(self):
        return "%s (%s)" % (self.__class__.__name__, self.name)

    def __call__(self, name=None, current=None, dimensions=None):
        if dimensions is None:
            dimensions = []
        else:
            dimensions.append((name, current))
        if not self.next_iter is None:
            for value in self.values:
                # interrupt: stop the iteration and return the generator
                if self.interrupt:
                    # return the generator
                    yield value, self.next_iter(self.name, value, dimensions[:])
                else:
                    # iterate over the next generator: return elements of the
                    # next dimension
                    for next_iter in self.next_iter(
                            self.name, value, dimensions[:]):
                        yield next_iter
        else:
            # end of generator-chain reached: return the MetaImages
            for value in self.values:
                params = dict(dimensions + [(self.name, value)])
                coordinate = Coordinate(**params)
                yield value, self.image_container.get_meta_image(coordinate)


class Coordinate(object):

    def __init__(self, plate=None, position=None, time=None, channel=None,
                 zslice=None):

        for c in (plate, position, time, channel, zslice):
            if isinstance(c, (list, tuple)) and (len(set(c)) != len(c)):
                raise RuntimeError(('Cannot setup unambiguous '
                                    'coordianates for image stack'))

        self.plate = plate
        self.position = position
        self.time = time
        self.channel = channel
        self.zslice = zslice

    def copy(self):
        return copy.deepcopy(self)

    def __str__(self):
        res = ''
        for key, info in zip(['plate', 'position','time', 'channel', 'zslice'],
                             [self.plate, self.position, self.time, self.channel, self.zslice]):
            if info is None:
                continue
            else:
                res += '\n%s: %s' % (key, str(info))
        return res

class ImageContainer(object):

    _structfile_tmpl = 'FileStructure_PL%s.xml'

    def __init__(self):
        self._plates = OrderedDict()
        self._path_in = OrderedDict()
        self._path_out = OrderedDict()
        self._importer = None
        self.current_plate = None
        self.has_timelapse = None

    def register_plate(self, plate_id, path_in, path_out, filename):
        self._plates[plate_id] = filename
        self._path_in[plate_id] = path_in
        self._path_out[plate_id] = path_out
        # FIXME: check some dimensions!!!

    def iterator(self, coordinate,
                 interrupt_time=False,
                 interrupt_channel=False,
                 interrupt_zslice=False):
        meta_data = self.get_meta_data()
        # FIXME: linking of iterators should adapt to any scan-order
        iter_zslice = AxisIterator(self, coordinate.zslice,
                                   meta_data.zslices, 'zslice')
        iter_channel = AxisIterator(self, coordinate.channel,
                                    meta_data.channels, 'channel',
                                    interrupt_zslice, iter_zslice)
        iter_time = AxisIterator(self, coordinate.time,
                                 meta_data.times, 'time',
                                 interrupt_channel, iter_channel)
        iter_position = AxisIterator(self, coordinate.position,
                                     meta_data.positions, 'position',
                                     interrupt_time, iter_time)
        return iter_position()

    __call__ = iterator

    def set_plate(self, plate):
        if plate != self.current_plate:
            self.current_plate = plate
            filename = self._plates[plate]
            self._importer = IniFileImporter.load_xml(filename)
            self._importer.path = self._path_in[plate]

    def check_dimensions(self):
        self.has_timelapse = self._importer.meta_data.has_timelapse

    def get_meta_image(self, coordinate):
        meta_data = self.get_meta_data()
        return MetaImage(self, coordinate, meta_data.dim_y, meta_data.dim_x)

    def get_image(self, coordinate):
        return self._importer.get_image(coordinate)

    def get_meta_data(self):
        return self._importer.meta_data

    def get_path_out(self, plate=None):
        if plate is None:
            plate = self.current_plate
        return self._path_out[plate]

    @property
    def plates(self):
        return sorted(self._plates.keys())

    @property
    def has_multiple_plates(self):
        return len(self.plates) > 1

    @property
    def channels(self):
        meta_data = self.get_meta_data()
        return sorted(meta_data.channels)

    @classmethod
    def _get_structure_filename(cls, settings, plate_id,
                                path_plate_in, path_plate_out):
        if settings('General', 'structure_file_pathin'):
            path_structure = path_plate_in
        elif settings('General', 'structure_file_pathout'):
            path_structure = path_plate_out
        else:
            path_structure = \
                settings('General', 'structure_file_extra_path_name')

        filename = cls._structfile_tmpl %plate_id
        return os.path.join(path_structure, filename)

    @classmethod
    def iter_check_plates(cls, settings, plates_restriction=None):
        path_in = settings('General', 'pathin')
        path_out = settings('General', 'pathout')
        has_multiple_plates = settings('General', 'has_multiple_plates')

        if has_multiple_plates:
            plate_folders = [x for x in os.listdir(path_in)
                             if os.path.isdir(os.path.join(path_in, x))]
            if plates_restriction is not None:
                plate_folders = [x for x in plate_folders if x in plates_restriction]
        else:
            plate_folders = [os.path.split(path_in)[1]]

        for plate_id in plate_folders:

            if has_multiple_plates:
                path_plate_in = os.path.join(path_in, plate_id)
                path_plate_out = os.path.join(path_out, plate_id)
            else:
                path_plate_in = path_in
                path_plate_out = path_out

            # check if structure file exists
            filename = cls._get_structure_filename(
                settings, plate_id, path_plate_in, path_plate_out)
            if not os.path.isfile(filename):
                filename = None
            yield plate_id, path_plate_in, path_plate_out, filename

    def iter_import_from_settings(self, settings, plates_restriction=None, scan_plates=None):
        settings.set_section(SECTION_NAME_GENERAL)

        for info in self.iter_check_plates(settings, plates_restriction):
            plate_id, path_plate_in, path_plate_out, filename = info

            # check whether this plate has to be rescanned
            if not scan_plates is None:
                scan_plate = scan_plates[plate_id]
            else:
                scan_plate = False

            # if no structure file was found scan the plate
            if filename is None:
                scan_plate = True

            # (re)scan the file structure
            if scan_plate:
                config_parser = CecogEnvironment.naming_schema
                section_name = settings.get2('namingscheme')
                importer = IniFileImporter()
                importer.setup(path_plate_in, config_parser, section_name)
                importer.scan()

                if importer.is_valid:
                    filename = self._get_structure_filename(settings, plate_id,
                                                            path_plate_in,
                                                            path_plate_out)

                    importer.save_xml(filename)
                    self.register_plate(plate_id, path_plate_in,
                                        path_plate_out, filename)
            else:
                self.register_plate(plate_id, path_plate_in,
                                    path_plate_out, filename)

            yield info

    def import_from_settings(self, settings, plates_restriction=None, scan_plates=None):
        list(self.iter_import_from_settings(settings,plates_restriction, scan_plates))
