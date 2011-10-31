import os, sys, time, re
from scripts.EMBL.settings import Settings

class FlatFileImporter(object):

    def __init__(self):
        self.sep = '\t'
        self.track_id_regex = re.compile('T(?P<Time>\d+)__O(?P<Object>\d+)')

    def importSingleObjectTrackData(self):
        raise NotImplemented('you have to chose which result filetype is to be imported.')
        return

    def importLabtekData(self):
        raise NotImplemented('')
        return

    # transforms a string to int, float or string (attempts in that order)
    def getValue(self, stringval):
        try:
            value = int(stringval)
        except:
            try:
                value = float(stringval)
            except:
                value = stringval
        return value

    # we check for all tracks and the given features, whether it is possible
    # to sum them (only for numerical features). If not, the track is removed.
    def removeTracksWithEmptyFields(self, impdata, features_to_check):
        #numericalFeatures = self.oSettings.features_for_background_subtraction
        toremoveIds = []
        for trackId in sorted(impdata.keys()):
            for feature in features_to_check:
                if not feature in impdata[trackId]:
                    continue
                try:
                    dummy = sum(impdata[trackId][feature])
                except:
                    toremoveIds.append(trackId)
                    continue

        for remid in set(toremoveIds):
            del(impdata[remid])
        return

    # 00001/statistics/events/features__P00001__T00096__O0026__B02__CPrimary__Rprimary.txt
    # 00001/statistics/full/P00001__T00000__O0002__B01.txt
    def importMovieData(self, in_dir, filenames, channel=None, region=None):
        #filenames = filter(lambda x: x[-4:] == '.txt', os.listdir(in_dir))
        impdata = {}
        not_imported = []
        for filename in filenames:
            regex_search = self.track_id_regex.search(filename)
            if regex_search is None:
                print 'skipping %s' % filename
                continue
            dctRegex = regex_search.groupdict()
            track_id = '__'.join(['T' + dctRegex['Time'], 'O' + dctRegex['Object']])
            if not track_id in impdata:
                impdata[track_id] = {}
            try:
                impdata[track_id].update(self.importSingleObjectTrackData(os.path.join(in_dir,
                                                                                  filename),
                                                                                  channel,
                                                                                  region))
            except:
                not_imported.append(track_id)
                if track_id in impdata:
                    del(impdata[track_id])

        if len(not_imported) > 0:
            print 'from %s %i tracks were not imported' % (in_dir, len(not_imported))

        if self.oSettings.remove_empty_fields:
            self.removeTracksWithEmptyFields(impdata)

        return impdata


    def __call__(self, baseDir=None, plates=None, positions=None):

        if baseDir is None:
            if not self.oSettings.baseDir is None:
                baseDir = self.oSettings.baseDir
            else:
                raise ValueError("Please specify an input directory where the"
                                 "Cellcognition results can be found.")

        if plates is None:
            try:
                plates = self.oSettings.plates
            except:
                plates = filter(lambda x: os.path.isdir(os.path.join(baseDir, x)),
                                os.listdir(baseDir))

        impdata = {}
        for plate in plates:
            in_dir = os.path.join(baseDir, plate)
            print 'importing %s from %s' % (plate, in_dir)
            impdata[plate] = self.importLabtekData(in_dir, positions)

        return impdata


class FullDescriptionImporter(FlatFileImporter):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.oSettings = settings
        elif not settings_filename is None:
            self.oSettings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())

        self.entries = self.oSettings.import_entries_full
        self.pos_regex = self.oSettings.pos_regex

        FlatFileImporter.__init__(self)

    def importSingleObjectTrackData(self, filename, channel=None, region=None, sep=None):
        if sep is None:
            sep = self.sep

        oFile = open(filename, 'r')
        temp = oFile.readlines()
        oFile.close()

        # first line: channel
        channels = [x.lower() for x in temp[0].strip('\n').split(sep)]

        # second line: region
        regions = [x.lower() for x in temp[1].strip('\n').split(sep)]

        # third line: feature
        features = temp[2].strip('\n').split(sep)

        found_entries = zip(channels, regions, features)

        impdata = {}
        for line in temp[3:]:
            lineread = line.strip('\n').split(sep)
            lineread += ['' for i in range(len(lineread), len(found_entries))]
            tempdict = dict(zip(found_entries, lineread))
            for ch in self.entries.keys():
                for reg in self.entries[ch].keys():
                    if self.entries[ch][reg] == 'all':
                        import_features = filter(lambda x:
                                                 x not in self.common_entries,
                                                 found_entries)
                    else:
                        import_features = self.entries[ch][reg]
                    for feat in import_features:
                        if not (ch, reg, feat) in tempdict:
                            continue
                        # NEW:
                        if not ch in impdata:
                            impdata[ch] = {}
                        if not reg in impdata[ch]:
                            impdata[ch][reg] = {}
                        if not feat in impdata[ch][reg]:
                            impdata[ch][reg][feat] = []
                        impdata[ch][reg][feat].append(self.getValue(tempdict[(ch,reg,feat)]))
#OLD:
#                        if not (ch,reg,feat) in impdata:
#                            impdata[(ch,reg,feat)] = []
#                        impdata[(ch,reg,feat)].append(self.getValue(tempdict[(ch,reg,feat)]))

        return impdata


    def importLabtekData(self, in_dir):

        positions = filter(lambda x: self.pos_regex.search(x),
                           os.listdir(os.path.join(in_dir, 'analyzed')))
        print 'found %i positions in %s' % (len(positions), in_dir)

        impdata = {}
        for pos in positions:
            posfolder = os.path.join(in_dir, 'analyzed', pos,
                                     'statistics', 'full')
            filenames = filter(lambda x: x[-4:] == '.txt', os.listdir(posfolder))

            impdata[pos] = self.importMovieData(posfolder, filenames)

        return impdata


class EventDescriptionImporter(FlatFileImporter):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.oSettings = settings
        elif not settings_filename is None:
            self.oSettings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())

        self.entries = self.oSettings.import_entries_event
        self.pos_regex = self.oSettings.pos_regex

        # features__PA01_01__T00010__O0213__B01__CSecondary__Rpropagate.txt
        self.channel_region_regex = re.compile('C(?P<Channel>.+)__R(?P<Region>.+)')
        self.common_entries = [
                               'Frame',
                               'Timestamp',
                               'isEvent',
                               'isSplit',
                               'objId'
                               ]

        FlatFileImporter.__init__(self)

    def importSingleObjectTrackData(self, filename, channel, region, sep=None):
        if sep is None:
            sep = self.sep

        oFile = open(filename, 'r')
        temp = oFile.readlines()
        oFile.close()

        found_entries = temp[0].strip('\n').split(sep)

        if self.entries[channel][region] == 'all':
            import_features = filter(lambda x: x not in self.common_entries, found_entries)
        elif self.entries[channel][region] == 'all_features':
            import_features =  filter(lambda x: x.split('__')[0]=='feature', found_entries)
        elif self.entries[channel][region] == 'all_tracking':
            import_features =  filter(lambda x: x.split('__')[0]=='tracking', found_entries)
        else:
            import_features = self.entries[channel][region]

        impdata = {}
        for line in temp[1:]:
            lineread = line.strip('\n').split(sep)
            tempdict = dict(zip(found_entries, lineread))
            for entry in import_features:
                if not entry in tempdict:
                    continue

                # NEW:
                if not channel in impdata:
                    impdata[channel] = {}
                if not region in impdata[channel]:
                    impdata[channel][region] = {}
                if not entry in impdata[channel][region]:
                    impdata[channel][region][entry] = []
                impdata[channel][region][entry].append(self.getValue(tempdict[entry]))
                #if not (channel, region, entry) in impdata:
                #    impdata[(channel, region, entry)] = []
                #impdata[(channel, region, entry)].append(self.getValue(tempdict[entry]))

            # for common entries, the channel and region information
            # is dropped
            for entry in self.common_entries:
                if not entry in tempdict:
                    continue
                if not entry in impdata:
                    impdata[entry] = []
                impdata[entry].append(self.getValue(tempdict[entry]))

        return impdata


    def getFilenamesForChannelsAndRegions(self, posfolder):
        filenames = filter(lambda x: x[-4:] == '.txt',
                           os.listdir(posfolder))

        # get all different channel,region combinations
        #channels_regions = set([(x[0],x[1]) for x in self.entries])
        channels_regions = []
        for channel in self.entries.keys():
            for region in self.entries[channel].keys():
                channels_regions.append((channel, region))

        cr_filenames = {}
        for filename in filenames:
            regex_search = self.channel_region_regex.search(os.path.splitext(filename)[0])
            if regex_search is None:
                #print 'no interpretation: ', filename
                continue
            dctRegex = regex_search.groupdict()
            channel = dctRegex['Channel'].lower()
            region = dctRegex['Region'].lower()
            if (channel, region) in channels_regions:
                if not (channel, region) in cr_filenames:
                    cr_filenames[(channel, region)] = []
                cr_filenames[(channel, region)].append(filename)

        return cr_filenames


    def getPositionsForPlate(self, plate):

        in_dir = os.path.join(self.oSettings.baseDir, plate)
        positions = filter(lambda x: self.pos_regex.search(x),
                   os.listdir(os.path.join(in_dir, 'analyzed')))
        return positions

    def importLabtekData(self, in_dir, positions=None):

        if positions is None:
            positions = filter(lambda x: self.pos_regex.search(x),
                               os.listdir(os.path.join(in_dir, 'analyzed')))
        else:
            positions = filter(lambda x: self.pos_regex.search(x),
                               positions)

        #positions = filter(lambda x: self.pos_regex.search(x),
        #                   os.listdir(os.path.join(in_dir, 'analyzed')))
        print 'found %i positions in %s' % (len(positions), in_dir)

        impdata = {}

        for pos in positions:
            posfolder = os.path.join(in_dir, 'analyzed', pos,
                                     'statistics', 'events')
            impdata[pos] = {}
            cr_filenames = self.getFilenamesForChannelsAndRegions(posfolder)

            for ch, r in cr_filenames.keys():
                filenames = sorted(cr_filenames[(ch, r)])
                movie_data = self.importMovieData(posfolder, filenames, ch, r)

                tracks = sorted(movie_data.keys())
                for track in tracks:
                    if track in impdata[pos]:
                        if not ch in impdata[pos][track]:
                            impdata[pos][track][ch] = {}
                        impdata[pos][track][ch].update(movie_data[track][ch])
                    else:
                        impdata[pos][track] = movie_data[track]

        return impdata

