"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import
from __future__ import print_function
import six
from six.moves import range
from six.moves import zip

__author__ = 'Michael Held, Thomas Walter'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ("IniFileImporter", )



import os
import re

from cecog import ccore
from cecog.util.util import read_table
from cecog.util.stopwatch import StopWatch
from cecog.util.token import Token, TokenHandler
from cecog.io.xmlserializer import XmlSerializer


from cecog.io.metadata import MetaData, MetaDataError
from cecog.io.constants import PixelType
from cecog.io.constants import MetaInfo
from cecog.io.constants import Dimensions


TOKEN_P = Token('P', type_code='i', length='+', prefix='',
                name=Dimensions.Position)
TOKEN_T = Token('T', type_code='i', length='+', prefix='',
                name=Dimensions.Time)
TOKEN_C = Token('C', type_code='c', length='+', prefix='',
                name=Dimensions.Channel, regex_type='\D')
TOKEN_Z = Token('Z', type_code='i', length='+', prefix='',
                name=Dimensions.ZSlice)


class DefaultCoordinates(object):
    def __init__(self):
        self.default_values = {
                               Dimensions.Time: 1,
                               Dimensions.Channel: 'ch0',
                               Dimensions.ZSlice: 1,
                               'DEFAULT': ''
                               }
        return

    def __call__(self, image_info, key):
        if key in self.default_values:
            if key not in image_info:
                return self.default_values[key]
            elif image_info[key] in ['', None]:
                return self.default_values[key]
        else:
            if key in image_info:
                return image_info[key]
            else:
                return self.default_values['DEFAULT']

        return image_info[key]


class AbstractImporter(XmlSerializer):

    EXTENSIONS = ['.tif', '.png', '.png']
    IGNORE_PREFIXES = ['.']

    MULTIIMAGE_IGNORE = 'ignore'
    MULTIIMAGE_USE_ZSLICE = 'zslice'

    def __init__(self):
        super(AbstractImporter, self).__init__()

    def setup(self, path,
                 extensions=None, ignore_prefixes=None, multi_image=None):
        self.path = os.path.normpath(path)
        self.extensions = self.EXTENSIONS if extensions is None \
                          else extensions
        self.ignore_prefixes = self.IGNORE_PREFIXES if ignore_prefixes is None \
                               else ignore_prefixes
        self.multi_image = self.MULTIIMAGE_USE_ZSLICE if multi_image is None \
                           else multi_image
        self.has_multi_images = False
        self.timestamps_from_file = None
        self.use_frame_indices = False
        self.dimension_lookup = {}
        self.meta_data = MetaData()

    def __setstate__(self, state):
        for k,v in six.iteritems(state):
            self.__dict__[k] = v

    def scan(self):
        self.dimension_lookup = self._build_dimension_lookup()
        self.meta_data.setup()

    @property
    def is_valid(self):
        """
        Return the import success. For now only the number of identified files
        is checked.
        """
        return self.meta_data.image_files > 0

    def get_image(self, coordinate):
        index = 0
        zslice = coordinate.zslice
        if (self.has_multi_images and
            self.multi_image == self.MULTIIMAGE_USE_ZSLICE):
            index = zslice - 1
            zslice = None

        filename_rel = self.dimension_lookup[coordinate.position] \
                                            [coordinate.time] \
                                            [coordinate.channel] \
                                            [zslice]
        filename_abs = os.path.join(self.path, filename_rel)
        # make sure no back-slashes are left in the path
        filename_abs = filename_abs.replace('\\', '/')
        if self.meta_data.pixel_type == PixelType.name(PixelType.Uint8):
            image = ccore.readImage(filename_abs, index)
        elif self.meta_data.pixel_type == PixelType.name(PixelType.Uint16):
            image = ccore.readImageUInt16(filename_abs, index)
        else:
            image = ccore.readImageUInt16(filename_abs, index)
        return image

    def _build_dimension_lookup(self):
        s = StopWatch(start=True)
        lookup = {}
        has_xy = False
        positions = []
        times = []
        channels = []
        zslices = []

        dimension_items = self._get_dimension_items()
        print(("Get dimensions: %s" %s.interim()))
        s.reset(start=True)

        # if use_frame_indices is set in the ini file,
        # we make a first scan of the items and determine for each position
        # the list of timepoints.
        # Then, we can assign to each position a dictionary that assigns to each timepoint
        # its index (after ordering).
        if self.use_frame_indices:
            #all_times = list(set([int(item[Dimensions.Time]) if Dimensions.Time in item else 0
            #                      for item in dimension_items]))
            #all_times.sort()
            first_pass = {}
            for item in dimension_items:
                position = item[Dimensions.Position]
                if not position in first_pass:
                    first_pass[position] = []

                if Dimensions.Time in item:
                    time_val = int(item[Dimensions.Time])
                else:
                    time_val = 0
                first_pass[position].append(time_val)

            time_index_correspondence = {}
            for pos in list(first_pass.keys()):
                first_pass[position].sort()
                time_index_correspondence[pos] = dict(list(zip(first_pass[position],
                                                          list(range(len(first_pass[position]))))))

        for item in dimension_items:
            # import image info only once
            if not has_xy:
                has_xy = True
                info = ccore.ImageImportInfo(os.path.join(self.path,
                                                          item['filename']))

                self.meta_data.set_image_info(info)
                self.has_multi_images = False #info.images > 1

            # position
            position = item[Dimensions.Position]
            if not position in lookup:
                lookup[position] = {}

            # time
            if Dimensions.Time in item:
                time_from_filename = int(item[Dimensions.Time])
            else:
                time_from_filename = 0
                item[Dimensions.Time] = str(time_from_filename)

            if self.use_frame_indices:
                time = time_index_correspondence[position][time_from_filename]
            else:
                time = time_from_filename
            if not time in lookup[position]:
                lookup[position][time] = {}

            # channels
            if Dimensions.Channel in item:
                channel = item[Dimensions.Channel]
            else:
                channel = '1'
                item[Dimensions.Channel] = channel
            if not channel in lookup[position][time]:
                lookup[position][time][channel] = {}

            # leave zslice optional.
            # in case of multi-images it must not be defined
            if Dimensions.ZSlice in item:
                zslice = item[Dimensions.ZSlice]
            else:
                zslice = 0
                item[Dimensions.ZSlice] = zslice
            if zslice == '':
                zslice = None
            if not zslice is None:
                zslice = int(zslice)
            if not zslice in lookup[position][time][channel]:
                lookup[position][time][channel][zslice] = item['filename']

            # allow to read timestamps from file if not present
            if MetaInfo.Timestamp in item:
                timestamp = float(item[MetaInfo.Timestamp])
                self.meta_data.append_absolute_time(position, time, timestamp)
            elif self.timestamps_from_file in ['mtime', 'ctime']:
                filename_full = os.path.join(self.path, item['filename'])
                if self.timestamps_from_file == 'mtime':
                    timestamp = os.path.getmtime(filename_full)
                else:
                    timestamp = os.path.getctime(filename_full)
                item[MetaInfo.Timestamp] = timestamp
                self.meta_data.append_absolute_time(position, time, timestamp)

            if MetaInfo.Well in item:
                well = item[MetaInfo.Well]
                subwell = item.get(MetaInfo.Subwell, None)
                self.meta_data.append_well_subwell_info(position, well, subwell)

            if (self.has_multi_images and
                self.multi_image == self.MULTIIMAGE_USE_ZSLICE):
                if not zslice is None:
                    raise ValueError('Multi-image assigned for zslice conflicts'
                                     ' with zslice token in filename!')
                zslices.extend(list(range(1,info.images+1)))
            else:
                zslices.append(zslice)

            positions.append(position)
            times.append(time)
            channels.append(channel)

        self.meta_data.positions = tuple(sorted(set(positions)))

        # assure that all items of one dimension are of same length
        times = set(times)
        channels = set(channels)
        zslices = set(zslices)
        # find overall valid number of frames
        for p in lookup:
            times = times.intersection(list(lookup[p].keys()))
        # find overall valid channels/zslices based on overall valid frames
        for p in lookup:
            for t in times:
                channels = channels.intersection(list(lookup[p][t].keys()))
                for c in channels:
                    zslices = zslices.intersection(list(lookup[p][t][c].keys()))
        self.meta_data.times = sorted(times)
        self.meta_data.channels = sorted(channels)
        self.meta_data.zslices = sorted(zslices)
        self.meta_data.image_files = len(dimension_items)

        print(('Build time: %s' %s.stop()))
        return lookup

    def _get_dimension_items(self):
        raise NotImplementedError()


class IniFileImporter(AbstractImporter):
    """
    Scan file structure based on config file (see ConfigParser) definitions.

    Parameters for the config file are:

    file_extensions = .tiff .tif
     - a list of file extensions separated by whitespace(s)
     - example: take all files with .tif or .tiff extension

    regex_subdirectories = ^[^_].*
     - a filter rule for any sub-directory from which images should be imported
     - is a regular expression which must be found via re.search()
     - can be empty, in that case all directories are taken
     - example: ignore all directories with a leading underscore

    allow_subfolder = NAME
     - defines a sub-folder or path relative to the input path. in case no valid images are found in the
       input path this sub-folder is searched next
     - will be ignored if not specified or if the sub-folder does not exist

    regex_filename_substr = (.+?)\.
     - defines a part of the relative filename in which the dimension definition
       will be searched
     - is a regular expression which is searched and must define a group via ()
     - can be empty, in that case the entire filename is considered
     - example: take sub-string till the first dot

    regex_dimensions = P(?P<position>.+?)_+?T(?P<time>\d+)_+?C(?P<channel>.+?)_+?Z(?P<zslice>\d+)
     - defines how the dimensions 'position', 'time', 'channel', and 'zslice' are
       extracted from the sub-string of the relative filename (see above)
     - is a regular expression with named groups which is searched
     - time, channel, and zslice are optional and default to 0, w1, 0
     - time and zslice MUST be digits!
     - example: defines position, time, channel, and zslice with tokens separated
                by at least one underscore, e.g. will find
                abcd_P0023_T00001_Cgfp_Z1_efg

    timestamps_from_file = mtime
     - decide if the timestamp information is taken from the file directly
     - valid values are:
           * mtime - file modification time
           * ctime - file creation time
     - any other value (or omitting the parameter) will disable the timestamp
       extraction from file
     - NOTE: using timestamps from files can be dangerous, because the
             information can be lost during file copy. nevertheless this is for
             TIFF stacks often the only source of this information.

    reformat_well = True
     - boolean value defining whether the well information is reformatted to the
       canonical form "[A-Z]\d{2}"
     - default: True
     - example: a1 -> A01
                P5 -> P05
    """

    def __init__(self):
        super(IniFileImporter, self).__init__()

    @classmethod
    def load_xml(self, filename):
        with open(filename, 'rb') as fp:
            obj = XmlSerializer.deserialize(fp.read())
        return obj

    def save_xml(self, filename):
        with open(filename, 'wb') as fp:
            fp.write(self.serialize())

    def setup(self, path, config_parser, section_name):
        super(IniFileImporter, self).setup(path)
        config_parser = config_parser
        section_name = section_name

        self._regex_subdirectories = config_parser.get(section_name, 'regex_subdirectories')
        # take all sub-directories if parameter is empty
        if self._regex_subdirectories == '':
            self._regex_subdirectories = '.*'

        self._regex_filename_substr = config_parser.get(section_name, 'regex_filename_substr')
        # take the entire filename if parameter is empty
        if self._regex_filename_substr == '':
            self._regex_filename_substr = '(.*)'

        self._regex_dimensions = config_parser.get(section_name, 'regex_dimensions')
        if config_parser.has_option(section_name, 'timestamps_from_file'):
            self.timestamps_from_file = \
                config_parser.get(section_name, 'timestamps_from_file')

        if config_parser.has_option(section_name, 'reformat_well'):
            self.reformat_well = \
                eval(config_parser.get(section_name, 'reformat_well'))
        else:
            self.reformat_well = True

        self.extensions = config_parser.get(section_name, 'file_extensions').split()

        if config_parser.has_option(section_name, 'allow_subfolder'):
            self.allow_subfolder = config_parser.get(section_name, 'allow_subfolder')
        else:
            self.allow_subfolder = None

        if config_parser.has_option(section_name, 'use_frame_indices'):
            self.use_frame_indices = config_parser.get(section_name, 'use_frame_indices').lower() == 'true'
        else:
            self.use_frame_indices = False


    def __setstate__(self, state):
        super(IniFileImporter, self).__setstate__(state)
        if 'config_parser' in state:
            del self.config_parser

    def __get_token_list(self, path, sub_folder=None):
        token_list = []

        re_subdir = re.compile(self._regex_subdirectories)
        re_substr = re.compile(self._regex_filename_substr)
        re_dim = re.compile(self._regex_dimensions)

        re_well_str = r"[a-zA-Z]\d{1,5}"
        re_well = re.compile(re_well_str)

        re_well_str2 = r"\d{1,5}"
        re_well2 = re.compile(re_well_str2)

        re_well_str3 = r"(?P<letter>[a-zA-Z])\D*(?P<number>\d{1,5})"
        re_well3 = re.compile(re_well_str3)
        
        for dirpath, dirnames, filenames in os.walk(path):
            # prune filenames by file extension
            if len(self.extensions) > 0:
                filenames = [x for x in filenames
                             if os.path.splitext(x)[1].lower() in self.extensions]
                filenames.sort()
            # prune dirnames by regex search for next iteration of os.walk
            # dirnames must be removed in-place!
            for dirname in dirnames[:]:
                if re_subdir.search(dirname) is None:
                    dirnames.remove(dirname)

            # extract dimension informations according to regex patterns from
            # relative filename (including extension)
            path_rel = os.path.relpath(dirpath, path)
            search_path = re_subdir.search(os.path.split(dirpath)[1])

            if not search_path is None:
                result_path = search_path.groupdict()
            else:
                result_path = {}

            for filename in filenames:
                filename_rel = os.path.join(path_rel, filename)
                # search substring to reduce relative filename for
                # dimension search
                search = re_substr.search(filename_rel)
                if not search is None and len(search.groups()) > 0:
                    found_name = search.groups()[0]
                    # check substring according to regex pattern
                    # extract dimension information
                    search2 = re_dim.search(found_name)
                    if not search2 is None:
                        result = search2.groupdict()
                        # use path data if not defined for the filename
                        for key in [Dimensions.Position, MetaInfo.Well,
                                    MetaInfo.Subwell]:
                            if not key in result and key in result_path:
                                result[key] = result_path[key]

                        if MetaInfo.Well in result:

                            # reformat well information
                            if self.reformat_well:
                                well = result[MetaInfo.Well]
                                if re_well.match(well) is None:
                                    if re_well2.match(well) is None:
                                        res3 = re_well3.match(well)
                                        if res3 is None:
                                            raise MetaDataError("Well data '%s' not "
                                                                "valid.\nValid are '%s' or '%s' or '%s'"
                                                                % (well, re_well_str, re_well_str2, re_well_str3))
                                        else:                                            
                                            letter = res3.groupdict()['letter']
                                            number = res3.groupdict()['number']
                                            result[MetaInfo.Well] = "%s%02d" % (letter.upper(), int(number))                                            
                                            #result[MetaInfo.Well] = "%s%02d" % (well[0].upper(), int(well[1:]))
                                    else:
                                        result[MetaInfo.Well] = "%05d" % int(well)
                                else:
                                    result[MetaInfo.Well] = "%s%02d" % (well[0].upper(), int(well[1:]))

                            # subwell is converted to int (default 1)
                            if MetaInfo.Subwell not in result:
                                result[MetaInfo.Subwell] = 1
                            elif result[MetaInfo.Subwell] is None:
                                result[MetaInfo.Subwell] = 1
                            else:
                                result[MetaInfo.Subwell] = \
                                    int(result[MetaInfo.Subwell])

                        # create position value if not found
                        if not Dimensions.Position in result:
                            if MetaInfo.Well in result:
                                result[Dimensions.Position] = '%s_%02d' % \
                                    (result[MetaInfo.Well],
                                     result[MetaInfo.Subwell])
                            else:
                                raise MetaDataError("Either 'position' or "
                                                    "'well' information "
                                                    "required in naming schema."
                                                    )
                        if sub_folder is None:
                            result['filename'] = filename_rel
                        else:
                            result['filename'] = os.path.join(sub_folder, filename_rel)
                        token_list.append(result)
        return token_list

    def _get_dimension_items(self):
        token_list = self.__get_token_list(self.path)
        # try a possible allowed sub-folder in case no results are found in the original path
        if len(token_list) == 0 and not self.allow_subfolder is None:
            path = os.path.join(self.path, self.allow_subfolder)
            if os.path.isdir(path):
                token_list = self.__get_token_list(path, self.allow_subfolder)
        return token_list
