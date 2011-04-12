"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held, Thomas Walter'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['FileTokenImporter',
           'MetaMorphTokenImporter',
           'SimpleTokenImporter',
           'ZeissLifeTokenImporter',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       re

#------------------------------------------------------------------------------
# extension module imports:
#
from pdk.fileutils import collect_files
from pdk.iterator import unique
from pdk.datetimeutils import StopWatch

#------------------------------------------------------------------------------
# cecog imports:
#
from cecog import ccore
from cecog.util.util import (read_table,
                             write_table,
                             )
from cecog.util.token import (Token,
                              TokenHandler,
                              )
from cecog.io.imagecontainer import (MetaData,
                                     DIMENSION_NAME_POSITION,
                                     DIMENSION_NAME_TIME,
                                     DIMENSION_NAME_CHANNEL,
                                     DIMENSION_NAME_ZSLICE,
                                     META_INFO_TIMESTAMP,
                                     META_INFO_WELL,
                                     META_INFO_SUBWELL,
                                     UINT8,
                                     UINT16,
                                     )

#------------------------------------------------------------------------------
# constants:
#
TOKEN_P = Token('P', type_code='i', length='+', prefix='',
                name=DIMENSION_NAME_POSITION)
TOKEN_T = Token('T', type_code='i', length='+', prefix='',
                name=DIMENSION_NAME_TIME)
TOKEN_C = Token('C', type_code='c', length='+', prefix='',
                name=DIMENSION_NAME_CHANNEL, regex_type='\D')
TOKEN_Z = Token('Z', type_code='i', length='+', prefix='',
                name=DIMENSION_NAME_ZSLICE)

#------------------------------------------------------------------------------
# functions:
#

#------------------------------------------------------------------------------
# classes:
#
class MetaDataError(ValueError):
    pass

class DefaultCoordinates(object):
    def __init__(self):
        self.default_values = {
                               DIMENSION_NAME_TIME: 1,
                               DIMENSION_NAME_CHANNEL: 'ch0',
                               DIMENSION_NAME_ZSLICE: 1,
                               'DEFAULT': ''
                               }
        return

    def __call__(self, image_info, key):
        if self.default_values.has_key(key):
            if not image_info.has_key(key):
                return self.default_values[key]
            elif image_info[key] in ['', None]:
                return self.default_values[key]
        else:
            if image_info.has_key(key):
                return image_info[key]
            else:
                return self.default_values['DEFAULT']

        return image_info[key]


class AbstractImporter(object):

    EXTENSIONS = ['.tif', '.png', '.png']
    IGNORE_PREFIXES = ['.']

    MULTIIMAGE_IGNORE = 'ignore'
    MULTIIMAGE_USE_ZSLICE = 'zslice'

    def __init__(self, path,
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
        self.dimension_lookup = {}
        self.meta_data = MetaData()

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
        filename_abs = filename_abs.replace('\\', '/')
        if self.meta_data.pixel_type == UINT8:
            image = ccore.readImage(filename_abs, index)
        elif self.meta_data.pixel_type == UINT16:
            image = ccore.readImageUInt16(filename_abs, index)
        return image

    def _build_dimension_lookup(self):
        s = StopWatch()
        lookup = {}
        has_xy = False
        positions = []
        times = []
        channels = []
        zslices = []

        dimension_items = self._get_dimension_items()
        print("Get dimensions: %s" % s)
        s.reset()
        for item in dimension_items:

            # import image info only once
            if not has_xy:
                has_xy = True
                info = ccore.ImageImportInfo(os.path.join(self.path,
                                                          item['filename']))
                self.meta_data.set_image_info(info)
                self.has_multi_images = False#info.images > 1

            position = item[DIMENSION_NAME_POSITION]
            if not position in lookup:
                lookup[position] = {}
            if DIMENSION_NAME_TIME in item:
                time = int(item[DIMENSION_NAME_TIME])
            else:
                time = 0
                item[DIMENSION_NAME_TIME] = str(time)
            if not time in lookup[position]:
                lookup[position][time] = {}

            if DIMENSION_NAME_CHANNEL in item:
                channel = item[DIMENSION_NAME_CHANNEL]
            else:
                channel = '1'
                item[DIMENSION_NAME_CHANNEL] = channel
            if not channel in lookup[position][time]:
                lookup[position][time][channel] = {}

            # leave zslice optional.
            # in case of multi-images it must not be defined
            if DIMENSION_NAME_ZSLICE in item:
                zslice = item[DIMENSION_NAME_ZSLICE]
            else:
                zslice = 0
                item[DIMENSION_NAME_ZSLICE] = zslice
            if zslice == '':
                zslice = None
            if not zslice is None:
                zslice = int(zslice)
            if not zslice in lookup[position][time][channel]:
                lookup[position][time][channel][zslice] = item['filename']

            # allow to read timestamps from file if not present
            if META_INFO_TIMESTAMP in item:
                timestamp = float(item[META_INFO_TIMESTAMP])
                self.meta_data.append_absolute_time(position, time, timestamp)
            elif self.timestamps_from_file in ['mtime', 'ctime']:
                filename_full = os.path.join(self.path, item['filename'])
                if self.timestamps_from_file == 'mtime':
                    timestamp = os.path.getmtime(filename_full)
                else:
                    timestamp = os.path.getctime(filename_full)
                item[META_INFO_TIMESTAMP] = timestamp
                self.meta_data.append_absolute_time(position, time, timestamp)

            if META_INFO_WELL in item:
                well = item[META_INFO_WELL]
                subwell = item.get(META_INFO_SUBWELL, None)
                self.meta_data.append_well_subwell_info(position, well, subwell)

            if (self.has_multi_images and
                self.multi_image == self.MULTIIMAGE_USE_ZSLICE):
                if not zslice is None:
                    raise ValueError('Multi-image assigned for zslice conflicts'
                                     ' with zslice token in filename!')
                zslices.extend(range(1,info.images+1))
            else:
                zslices.append(zslice)

            positions.append(position)
            times.append(time)
            channels.append(channel)

        self.meta_data.positions = tuple(sorted(unique(positions)))

        # assure that all items of one dimension are of same length
        times = set(times)
        channels = set(channels)
        zslices = set(zslices)
        for p in lookup:
            times = times.intersection(lookup[p].keys())
            for t in times:
                channels = channels.intersection(lookup[p][t].keys())
                for c in channels:
                    zslices = zslices.intersection(lookup[p][t][c].keys())
        self.meta_data.times = sorted(times)
        self.meta_data.channels = sorted(channels)
        self.meta_data.zslices = sorted(zslices)
        self.meta_data.image_files = len(dimension_items)

        print('Build time: %s' % s)
        return lookup

    def _get_dimension_items(self):
        raise NotImplementedError()

#    def export_to_flatfile(self, filename):
#        has_timestamps = (len(self._dimension_items) > 0 and
#                          META_INFO_TIMESTAMP in self._dimension_items[0])
#        has_wellinfo = (len(self._dimension_items) > 0 and
#                        META_INFO_WELL in self._dimension_items[0])
#
#        column_names = ['path', 'filename',
#                        DIMENSION_NAME_POSITION,
#                        DIMENSION_NAME_TIME,
#                        DIMENSION_NAME_CHANNEL,
#                        DIMENSION_NAME_ZSLICE,
#                        ]
#        if has_timestamps:
#            column_names.append(META_INFO_TIMESTAMP)
#        if has_wellinfo:
#            column_names += [META_INFO_WELL, META_INFO_SUBWELL]
#
#        dimension_items = self._dimension_items[:]
#        for item in dimension_items:
#            item['path'] = ''
#            item['filename'] = item['filename'].replace('\\', '/')
#        write_table(filename, dimension_items, column_names,
#                    sep='\t', guess_compression=True)



class FileTokenImporter(AbstractImporter):

    def __init__(self, path, token_handler,
                 extensions=None, ignore_prefixes=None, multi_image=None):
        super(FileTokenImporter, self).__init__(path, extensions=extensions,
                                                ignore_prefixes=ignore_prefixes,
                                                multi_image=multi_image)
        self.token_handler = token_handler

    def _get_dimension_items(self):
        file_list = collect_files(self.path, self.extensions, absolute=True,
                                  follow=False, recursive=True,
                                  ignore_case=True, force_python=True)
        token_list = []
        for filename in file_list:
            filename_rel = filename[len(self.path)+1:]
            filename_short = os.path.split(filename_rel)[1]
            if filename_short[0] not in self.ignore_prefixes:
                result = self.token_handler.search_all(filename_short)
                result['filename'] = filename_rel
                token_list.append(result)
        return token_list


class SimpleTokenImporter(FileTokenImporter):

    TOKEN_P = None
    TOKEN_T = None
    TOKEN_C = None
    TOKEN_Z = None

    def __init__(self, path, separator='_',
                 extensions=None, ignore_prefixes=None, multi_image=None):
        simple_token = TokenHandler(separator=separator)
        simple_token.register_token(self.TOKEN_P)
        simple_token.register_token(self.TOKEN_T)
        simple_token.register_token(self.TOKEN_C)
        simple_token.register_token(self.TOKEN_Z)

        super(SimpleTokenImporter,
              self).__init__(path, simple_token,
                             extensions=extensions,
                             ignore_prefixes=ignore_prefixes,
                             multi_image=multi_image)


class MetaMorphTokenImporter(SimpleTokenImporter):

    TOKEN_P = Token('P', type_code='c', length='+', prefix='',
                    name=DIMENSION_NAME_POSITION)
    TOKEN_T = Token('T', type_code='i', length='+', prefix='',
                    name=DIMENSION_NAME_TIME)
    TOKEN_C = Token('C', type_code='c', length='+', prefix='',
                    name=DIMENSION_NAME_CHANNEL)
    TOKEN_Z = Token('Z', type_code='i', length='+', prefix='',
                    name=DIMENSION_NAME_ZSLICE)

    def __init__(self, path, separator='_',
                 extensions=None, ignore_prefixes=None, multi_image=None):
        super(MetaMorphTokenImporter,
              self).__init__(path, separator=separator,
                             extensions=extensions,
                             ignore_prefixes=ignore_prefixes,
                             multi_image=multi_image)


class ZeissLifeTokenImporter(SimpleTokenImporter):

    TOKEN_P = Token('s', type_code='i', length='+', prefix='',
                    name=DIMENSION_NAME_POSITION)
    TOKEN_T = Token('t', type_code='i', length='+', prefix='',
                    name=DIMENSION_NAME_TIME)
    TOKEN_C = Token('w', type_code='c', length='+', prefix='',
                    name=DIMENSION_NAME_CHANNEL)
    TOKEN_Z = Token('Z', type_code='i', length='+', prefix='',
                    name=DIMENSION_NAME_ZSLICE)

    def __init__(self, path, separator='_',
                 extensions=None, ignore_prefixes=None,
                 multi_image=None):
        super(ZeissLifeTokenImporter,
              self).__init__(path, separator=separator,
                             extensions=extensions,
                             ignore_prefixes=ignore_prefixes,
                             multi_image=multi_image)


class FlatFileImporter(AbstractImporter):

    def __init__(self, path, filename):
        self.flat_filename = filename
        super(FlatFileImporter, self).__init__(path)

    def _get_dimension_items(self):
        column_names, table = read_table(self.flat_filename, True,
                                         guess_compression=True)
        test = ['path',
                'filename',
                DIMENSION_NAME_POSITION,
                ]
        for name in test:
            if not name in column_names:
                raise ValueError("Missing column '%s' in coordinate file "\
                                 "'%s'." % (name, self.flat_filename))
        for i in range(len(table)):
            table[i]['filename'] = os.path.join(table[i]['path'],
                                                table[i]['filename'])
        return table


class IniFileImporter(AbstractImporter):
    '''
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
    '''

    def __init__(self, path, config_parser, section_name):
        super(IniFileImporter, self).__init__(path)
        self.config_parser = config_parser
        self.section_name = section_name

        regex_subdirectories = self.config_parser.get(self.section_name,
                                                      'regex_subdirectories')
        # take all sub-directories if parameter is empty
        if regex_subdirectories == '':
            regex_subdirectories = '.*'
        self._re_subdir = re.compile(regex_subdirectories)

        regex_filename_substr = self.config_parser.get(self.section_name,
                                                      'regex_filename_substr')
        # take the entire filename if parameter is empty
        if regex_filename_substr == '':
            regex_filename_substr = '(.*)'
        self._re_substr = re.compile(regex_filename_substr)

        self._re_dim = re.compile(self.config_parser.get(self.section_name,
                                                         'regex_dimensions'))
        if self.config_parser.has_option(self.section_name,
                                         'timestamps_from_file'):
            self.timestamps_from_file = \
                self.config_parser.get(self.section_name,
                                       'timestamps_from_file')

        if self.config_parser.has_option(self.section_name,
                                         'reformat_well'):
            self.reformat_well = \
                eval(self.config_parser.get(self.section_name,
                                            'reformat_well'))
        else:
            self.reformat_well = True

    def _get_dimension_items(self):
        token_list = []
        extensions = self.config_parser.get(self.section_name,
                                            'file_extensions').split()

        re_subwell_str = r"[a-zA-Z]\d{1,2}"
        re_subwell = re.compile(re_subwell_str)

        for dirpath, dirnames, filenames in os.walk(self.path):
            # prune filenames by file extension
            if len(extensions) > 0:
                filenames = [x for x in filenames
                             if os.path.splitext(x)[1].lower() in extensions]
            # prune dirnames by regex search for next iteration of os.walk
            # dirnames must be removed in-place!
            for dirname in dirnames[:]:
                if self._re_subdir.search(dirname) is None:
                    dirnames.remove(dirname)

            # extract dimension informations according to regex patterns from
            # relative filename (including extension)
            path_rel = os.path.relpath(dirpath, self.path)
            search_path = self._re_subdir.search(os.path.split(dirpath)[1])

            if not search_path is None:
                result_path = search_path.groupdict()
            else:
                result_path = {}

            for filename in filenames:
                filename_rel = os.path.join(path_rel, filename)

                # search substring to reduce relative filename for
                # dimension search
                search = self._re_substr.search(filename)
                if not search is None and len(search.groups()) > 0:
                    found_name = search.groups()[0]
                    # check substring according to regex pattern
                    # extract dimension information
                    search2 = self._re_dim.search(found_name)
                    if not search2 is None:
                        result = search2.groupdict()

                        # use path data if not defined for the filename
                        for key in [DIMENSION_NAME_POSITION, META_INFO_WELL,
                                    META_INFO_SUBWELL]:
                            if not key in result and key in result_path:
                                result[key] = result_path[key]

                        if META_INFO_WELL in result:

                            # reformat well information
                            if self.reformat_well:
                                well = result[META_INFO_WELL]
                                if re_subwell.match(well) is None:
                                    raise MetaDataError("Well data '%s' not "
                                                        "valid.\nValid are '%s'"
                                                        % (re_subwell_str, well))
                                result[META_INFO_WELL] = "%s%02d" % \
                                    (well[0].upper(), int(well[1:]))

                            # subwell is converted to int (default 1)
                            if not META_INFO_SUBWELL in result:
                                result[META_INFO_SUBWELL] = 1
                            else:
                                result[META_INFO_SUBWELL] = \
                                    int(result[META_INFO_SUBWELL])

                        # create position value if not found
                        if not DIMENSION_NAME_POSITION in result:
                            if META_INFO_WELL in result:
                                result[DIMENSION_NAME_POSITION] = '%s_%02d' % \
                                    (result[META_INFO_WELL],
                                     result[META_INFO_SUBWELL])
                            else:
                                raise MetaDataError("Either 'position' or "
                                                    "'well' information "
                                                    "required in naming schema."
                                                    )

                        result['filename'] = filename_rel
                        token_list.append(result)
        return token_list


class LsmImporter(object):

    def __init__(self):
        pass

