"""
exporter.py

Exporters for numerical data to text/csv files
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['TrackExporter', 'EventExporter']


import csv
import shutil
import subprocess
from os.path import join
from collections import OrderedDict

from cecog.io.imagecontainer import Coordinate
from cecog.analyzer.tracker import Tracker
from cecog.io.dotwriter import DotWriter
from cecog.util.util import makedirs


class CSVParams(object):
    """Column names, prefixes and spearator for csv files"""

    sep = '\t'

    objId = "objId"
    feature = "feature__%s"
    class_ = "class__%s"
    tracking = "tracking__%s"

    tracking_features = ['center_x', 'center_y', 'upperleft_x',
                         'upperleft_y', 'lowerright_x', 'lowerright_y']


class TrackExporter(object):

    def __init__(self):
        super(TrackExporter, self).__init__()

    def _dot2png(self, filename):
        cmd = "dot %s -Tpng -o %s" %(filename, filename.replace(".dot",".png"))
        pipe = subprocess.Popen(cmd, shell=True)
        # we dont have to wait for the subprocess...
        pipe.wait()

    def graphviz_dot(self, filename, tracker, dot2png=False):
        DotWriter(filename, tracker)
        if dot2png:
            self._dot2png(filename)

    def tracking_data(self, filename, sample_holders):
        fp = None
        for frame, sample_holder in sample_holders.iteritems():
            feature_names = sample_holder.feature_names
            if len(sample_holder) == 0:
                continue

            # just one file for all frames
            if fp is None:
                fieldnames = ['Frame', 'ObjectID'] + \
                [CSVParams.feature %f for f in feature_names] + \
                [CSVParams.class_ %x for x in ['name', 'label', 'probability']] + \
                [CSVParams.tracking %x for x in CSVParams.tracking_features]

                fp = open(filename, 'wb')
                table = csv.DictWriter(fp, fieldnames=fieldnames,
                                       delimiter=CSVParams.sep)
                table.writeheader()

            for label, sample in sample_holder.iteritems():
                data = {'Frame' : frame, 'ObjectID' : label}

                # to have it in the same order as the feature names
                features = sample_holder.features_by_name(label, feature_names)

                for feature, feature_name in zip(features, feature_names):
                    data[CSVParams.feature %feature_name] = feature

                if sample.iLabel is not None:
                    data[CSVParams.class_ %'label'] = sample.iLabel
                    data[CSVParams.class_ %'name'] = sample.strClassName
                    data[CSVParams.class_ %'probability'] = \
                        ','.join(['%d:%.5f' % (int(x), y) for x, y in \
                                  sample.dctProb.iteritems()])

                data[CSVParams.tracking %'center_x'] = sample.oCenterAbs[0]
                data[CSVParams.tracking %'center_y'] = sample.oCenterAbs[1]
                data[CSVParams.tracking %'upperleft_x'] = sample.oRoi.upperLeft[0]
                data[CSVParams.tracking %'upperleft_y'] = sample.oRoi.upperLeft[1]
                data[CSVParams.tracking %'lowerright_x'] = sample.oRoi.lowerRight[0]
                data[CSVParams.tracking %'lowerright_y'] = sample.oRoi.lowerRight[1]
                table.writerow(data)


class EventExporter(object):

    def __init__(self, meta_data):
        super(EventExporter, self).__init__()
        self.meta_data = meta_data

    def track_features(self, timeholder,  visitor_data, channel_regions,
                              position, outdir):
        shutil.rmtree(outdir, True)
        makedirs(outdir)

        for tracks in visitor_data.itervalues():
            for startid, event_data in tracks.iteritems():
                if startid.startswith('_'):
                    continue
                for chname, region in channel_regions.iteritems():
                    for region_name, feature_names in region.iteritems():
                        try:
                            frame, obj_label, branch = Tracker.split_nodeid(startid)
                        except ValueError:
                            frame, obj_label = Tracker.split_nodeid(startid)
                            branch = 1
                        filename = 'features__P%s__T%05d__O%04d__B%02d__C%s__R%s.txt' \
                            %(position, frame, obj_label, branch, chname, region_name)
                        filename = join(outdir, filename)

                        self._data_per_channel(timeholder, event_data, filename, chname,
                                               region_name, feature_names, position)


    def _data_per_channel(self, timeholder, event_data, filename, channel_name,
                          region_name, feature_names, position):

        eventid = event_data['eventId']
        event_frame, _ = Tracker.split_nodeid(eventid)
        has_split = 'splitId' in event_data

        header_names = ['Frame', 'Timestamp', 'isEvent']
        if has_split:
            header_names.append('isSplit')
            if event_data['splitId'] is not None:
                split_frame, _ = Tracker.split_nodeid(event_data['splitId'])
            else:
                split_frame = None

        table = []
        # zip nodes with same time together
        for nodeids in zip(*event_data['tracks']):
            objids = []
            frame = None
            for nodeid in nodeids:
                node_frame, objid = Tracker.split_nodeid(nodeid)
                if frame is None:
                    frame = node_frame
                else:
                    assert frame == node_frame
                objids.append(objid)

            channel = timeholder[frame][channel_name]
            sample_holder = channel.get_region(region_name)

            if feature_names is None:
                feature_names = sample_holder.feature_names

            if CSVParams.objId not in header_names:
                # setup header line
                header_names.append(CSVParams.objId)
                header_names += [CSVParams.class_ %x for x in
                                 ['name', 'label', 'probability']]
                # only feature_names scales according to settings
                header_names += [CSVParams.feature %fn for fn in feature_names]
                header_names += [CSVParams.tracking %tf for tf in CSVParams.tracking_features]

            coordinate = Coordinate(position=position, time=frame)
            data = {'Frame' : frame,
                    'Timestamp': self.meta_data.get_timestamp_relative(coordinate),
                    'isEvent': int(frame==event_frame)}

            if has_split:
                data['isSplit'] = int(frame==split_frame)

            #for iIdx, iObjId in enumerate(lstObjectIds):
            objid = objids[0]
            if objid in sample_holder:
                sample = sample_holder[objid]
                data[CSVParams.objId] = objid

                # classification data
                if sample.iLabel is not None:
                    data[CSVParams.class_ %'label'] = sample.iLabel
                    data[CSVParams.class_ %'name'] = sample.strClassName
                    data[CSVParams.class_ %'probability'] = \
                        ','.join(['%d:%.5f' % (int(x),y) for x,y in
                                  sample.dctProb.iteritems()])

                common_ftr = [f for f in set(sample_holder.feature_names).intersection(feature_names)]
                features = sample_holder.features_by_name(objid, common_ftr)
                for feature, fname in zip(features, common_ftr):
                    data[CSVParams.feature %fname] = feature

                # features not calculated are exported as NAN
                diff_ftr = [f for f in set(feature_names).difference(sample_holder.feature_names)]
                for df in diff_ftr:
                    data[CSVParams.feature %df] = float("NAN")

                # object tracking data (absolute center)
                data[CSVParams.tracking %'center_x'] = sample.oCenterAbs[0]
                data[CSVParams.tracking %'center_y'] = sample.oCenterAbs[1]
                data[CSVParams.tracking %'upperleft_x'] = sample.oRoi.upperLeft[0]
                data[CSVParams.tracking %'upperleft_y'] = sample.oRoi.upperLeft[1]
                data[CSVParams.tracking %'lowerright_x'] = sample.oRoi.lowerRight[0]
                data[CSVParams.tracking %'lowerright_y'] = sample.oRoi.lowerRight[1]
            else:
                # we rather skip the entire event in case the object ID is not valid
                return
            table.append(data)

        if len(table) > 0:
            with open(filename, 'w') as fp:
                writer = csv.DictWriter(fp, fieldnames=header_names,
                                        delimiter=CSVParams.sep)
                writer.writeheader()
                writer.writerows(table)


    def _map_feature_names(self, feature_names):
        """Return a hash table to map feature names to new names."""

        name_table = OrderedDict()
        name_table['mean'] = 'n2_avg'
        name_table['sd'] = 'n2_stddev'
        name_table['size'] = 'roisize'

        # prominent place int the table for certain features
        flkp = OrderedDict()
        for nname, name in name_table.iteritems():
            if name in feature_names:
                flkp[nname] = name
        for fn in feature_names:
            flkp[CSVParams.feature %fn] = fn
        return flkp

    def full_tracks(self, timeholder, visitor_data, position, outdir):
        shutil.rmtree(outdir, True)
        makedirs(outdir)

        for start_id, data in visitor_data.iteritems():
            for idx, track in enumerate(data['_full']):
                has_header = False
                line1 = []
                line2 = []
                line3 = []

                frame, obj_label= Tracker.split_nodeid(start_id)[:2]
                filename = 'P%s__T%05d__O%04d__B%02d.txt' \
                    %(position, frame, obj_label, idx+1)
                f = file(join(outdir, filename), 'w')

                for node_id in track:
                    frame, obj_id = Tracker.split_nodeid(node_id)

                    coordinate = Coordinate(position=position, time=frame)
                    prefix = [frame, self.meta_data.get_timestamp_relative(coordinate), obj_id]
                    prefix_names = ['frame', 'time', 'objID']
                    items = []

                    for channel in timeholder[frame].values():
                        for region_id in channel.region_names():
                            region = channel.get_region(region_id)
                            if obj_id in region:
                                flkp = self._map_feature_names(region.feature_names)
                                if not has_header:
                                    keys = ['classLabel', 'className']
                                    if channel.NAME == 'Primary':
                                        keys += ['centerX', 'centerY']
                                    keys += flkp.keys()
                                    line1 += [channel.NAME.upper()] * len(keys)
                                    line2 += [str(region_id)] * len(keys)
                                    line3 += keys
                                obj = region[obj_id]
                                features = region.features_by_name(obj_id, flkp.values())
                                values = [x if not x is None else '' for x in [obj.iLabel, obj.strClassName]]
                                if channel.NAME == 'Primary':
                                    values += [obj.oCenterAbs[0], obj.oCenterAbs[1]]
                                values += list(features)
                                items.extend(values)

                    if not has_header:
                        has_header = True
                        prefix_str = [''] * len(prefix)
                        line1 = prefix_str + line1
                        line2 = prefix_str + line2
                        line3 = prefix_names + line3
                        f.write('%s\n' %CSVParams.sep.join(line1))
                        f.write('%s\n' %CSVParams.sep.join(line2))
                        f.write('%s\n' %CSVParams.sep.join(line3))

                    f.write('%s\n' %CSVParams.sep.join([str(i) for i in prefix + items]))
                f.close()
