"""
cellanalyzer.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from os.path import join
from collections import OrderedDict
import numpy as np

from cecog import ccore
from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel
from cecog.analyzer.channel import MergedChannel
from cecog.analyzer.object import ObjectHolder

from cecog.logging import LoggerObject
from cecog.util.util import makedirs
from cecog.colors import hex2rgb


class CellAnalyzer(LoggerObject):

    def __init__(self, timeholder, position, create_images, binning_factor,
                 detect_objects):

        super(CellAnalyzer, self).__init__()

        self.timeholder = timeholder
        self.P = position
        self.bCreateImages = create_images
        self.iBinningFactor = binning_factor
        self.detect_objects = detect_objects

        self._iT = None
        self._channel_registry = OrderedDict()

    def initTimepoint(self, iT):
        self._channel_registry.clear()
        self._iT = iT
        self.timeholder.initTimePoint(iT)

    # XXX rename it to "add_channel"
    def register_channel(self, channel):
        self._channel_registry[channel.NAME] = channel

    def get_channel_names(self):
        return self._channel_registry.keys()

    def get_channel(self, name):
        return self._channel_registry[str(name)]

    @property
    def proc_channels(self):
        """Return processing channels i.e the dict contains no virtual or
        pseudo channels.
        """
        pchannels = OrderedDict()
        for name, channel in self._channel_registry.iteritems():
            if not channel.is_virtual():
                pchannels[name] =  channel
        return pchannels

    @property
    def virtual_channels(self):
        """Return a dict that contains all virtual channels."""
        channels = dict()
        for name, channel in self._channel_registry.iteritems():
            if channel.is_virtual():
                channels[name] =  channel
        return channels

    def process(self, apply=True, extract_features=True):
        """Perform the segmentation and feature extraction."""
        channels = sorted(self._channel_registry.values())
        primary_channel = None

        cnames = [c.NAME for c in channels]
        for channel in channels:
            self.timeholder.prepare_raw_image(channel)
            if self.detect_objects:
                if channel.NAME == PrimaryChannel.NAME:
                    self.timeholder.apply_segmentation(channel)
                    primary_channel = channel
                elif channel.NAME == SecondaryChannel.NAME:
                    self.timeholder.apply_segmentation(channel, primary_channel)
                    secondary_channel = channel
                elif channel.NAME == TertiaryChannel.NAME:
                    if SecondaryChannel.NAME not in cnames:
                        raise RuntimeError(("Tertiary channel requiers a "
                                            "secondary channel"))
                    self.timeholder.apply_segmentation(channel,
                                                       primary_channel,
                                                       secondary_channel)
                elif channel.NAME == MergedChannel.NAME:
                    channel.meta_image = primary_channel.meta_image
                    self.timeholder.apply_segmentation(channel, self._channel_registry)
                else:
                    raise ValueError("Channel with name '%s' not supported." % channel.NAME)

                if extract_features:
                    self.timeholder.apply_features(channel)

        if apply:
            # want apply also the pseudo channels
            for channel in sorted(self._channel_registry.values()):
                self.timeholder.apply_channel(channel)

    def purge(self, features=None):

        for channel in self._channel_registry.values():
            if not features is None and channel.strChannelId in features:
                channelFeatures = features[channel.strChannelId]
            else:
                channelFeatures = None
            channel.purge(features=channelFeatures)

    def getImageSize(self, name):
        oChannel = self._channel_registry[name]
        w = oChannel.meta_image.width
        h = oChannel.meta_image.height
        return (w,h)

    def render(self, strPathOut, dctRenderInfo=None,
               strFileSuffix='.jpg', strCompression='98', writeToDisc=True,
               images=None):

        lstImages = []
        if not images is None:
            lstImages += images

        if dctRenderInfo is None:
            for name, oChannel in self._channel_registry.iteritems():
                for strRegion, oContainer in oChannel.containers.iteritems():
                    strHexColor, fAlpha = oChannel.dctAreaRendering[strRegion]
                    imgRaw = oChannel.meta_image.image
                    imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                    ccore.drawContour(oContainer.getBinary(), imgCon, 255, False)
                    lstImages.append((imgRaw, strHexColor, 1.0))
                    lstImages.append((imgCon, strHexColor, fAlpha))
        else:
            for channel_name, dctChannelInfo in dctRenderInfo.iteritems():
                if channel_name in self._channel_registry:
                    oChannel = self._channel_registry[channel_name]
                    if 'raw' in dctChannelInfo:
                        strHexColor, fAlpha = dctChannelInfo['raw']
                        # special casing for virtual channel to mix
                        # raw images together
                        if oChannel.is_virtual():
                            lstImages.extend(oChannel.meta_images(fAlpha))
                        else:
                            lstImages.append((oChannel.meta_image.image, strHexColor, 1.0))

                    if 'contours' in dctChannelInfo:
                        # transform the old dict-style to the new tuple-style,
                        # which allows multiple definitions for one region
                        if isinstance(dctChannelInfo['contours'], dict):
                            lstContourInfos = [(k,)+v
                                               for k,v in dctChannelInfo['contours'].iteritems()]
                        else:
                            lstContourInfos = dctChannelInfo['contours']

                        for tplData in lstContourInfos:
                            strRegion, strNameOrColor, fAlpha, bShowLabels = tplData[:4]
                            # draw contours only if region is present
                            if oChannel.has_region(strRegion):
                                if len(tplData) > 4:
                                    bThickContours = tplData[4]
                                else:
                                    bThickContours = False
                                imgRaw = oChannel.meta_image.image
                                if strNameOrColor == 'class_label':
                                    oContainer = oChannel.containers[strRegion]
                                    oRegion = oChannel.get_region(strRegion)
                                    dctLabels = {}
                                    dctColors = {}
                                    for iObjId, oObj in oRegion.iteritems():
                                        iLabel = oObj.iLabel
                                        if not iLabel is None:
                                            if not iLabel in dctLabels:
                                                dctLabels[iLabel] = []
                                            dctLabels[iLabel].append(iObjId)
                                            dctColors[iLabel] = oObj.strHexColor
                                    imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                    for iLabel, lstObjIds in dctLabels.iteritems():
                                        imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                        # Flip this and use drawContours with fill option enables to get black background
                                        oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
                                        lstImages.append((imgCon, dctColors[iLabel], fAlpha))

                                        if isinstance(bShowLabels, bool) and bShowLabels:
                                            oContainer.drawTextsByIds(lstObjIds, [str(iLabel)]*len(lstObjIds), imgCon2)
                                    lstImages.append((imgCon2, '#FFFFFF', 1.0))

                                else:
                                    oContainer = oChannel.containers[strRegion]
                                    oRegion = oChannel.get_region(strRegion)
                                    lstObjIds = oRegion.keys()
                                    imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                    if not strNameOrColor is None:
                                        oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
                                    else:
                                        strNameOrColor = '#FFFFFF'
                                    lstImages.append((imgCon, strNameOrColor, fAlpha))
                                    if bShowLabels:
                                        imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                        oContainer.drawLabelsByIds(lstObjIds, imgCon2)
                                        lstImages.append((imgCon2, '#FFFFFF', 1.0))

        if len(lstImages) > 0:
            imgRgb = ccore.makeRGBImage([x[0].getView() for x in lstImages],
                                        [ccore.RGBValue(*hex2rgb(x[1])) for x in lstImages],
                                        [x[2] for x in lstImages])

            if writeToDisc:
                strFilePath = join(strPathOut, "P%s_T%05d%s"
                                   %(self.P, self._iT, strFileSuffix))
                makedirs(strPathOut)
                ccore.writeImage(imgRgb, strFilePath, strCompression)
                self.logger.debug("* rendered image written '%s'" % strFilePath)
            else:
                strFilePath = ''
            return imgRgb, strFilePath

    def collectObjects(self, plate_id, P, sample_readers, oLearner):

        self.logger.debug('* collecting samples...')
        self.process(apply = False, extract_features = False)

        chname = oLearner.name
        region = oLearner.regions

        oChannel = self._channel_registry[chname]
        oContainer = oChannel.get_container(region)
        objects = oContainer.getObjects()
        # key = class_label, value = list of samples
        object_lookup = {}
        object_ids = set()

        for reader in sample_readers:
            if (P == reader.position() and self._iT in reader):
                coords = reader[self._iT]
            else:
                coords = None

            if coords is not None:
                for pos in coords:
                    label = pos.label
                    if (label in oLearner.class_names and
                        0 <= pos.x < oContainer.width and
                        0 <= pos.y < oContainer.height):

                        center1 = ccore.Diff2D(pos.x, pos.y)
                        # test for obj_id "under" annotated pixel first
                        obj_id = oContainer.img_labels[center1]

                        # if not background: valid obj_id found
                        if obj_id > 0:
                            object_ids.add(obj_id)
                            try:
                                object_lookup[label].extend([obj_id])
                            except KeyError:
                                object_lookup[label] = [obj_id]
                        # otherwise try to find nearest object in a search
                        # radius of 30 pixel (compatibility with CellCounter)
                        else:
                            dists = []
                            for obj_id, obj in objects.iteritems():
                                diff = obj.oCenterAbs - center1
                                dist_sq = diff.squaredMagnitude()
                                # limit to 30 pixel radius
                                if dist_sq < 900:
                                    dists.append((obj_id, dist_sq))
                            if len(dists) > 0:
                                dists.sort(lambda a,b: cmp(a[1], b[1]))
                                obj_id = dists[0][0]
                                object_ids.add(obj_id)
                                try:
                                    object_lookup[label].extend([obj_id])
                                except KeyError:
                                    object_lookup[label] = [obj_id]

        objects_del = set(objects.keys()) - object_ids
        for obj_id in objects_del:
            oContainer.delObject(obj_id)

        # calculate features of sub channels first
        # want invoke time_holder for hdf5
        if oChannel.is_virtual():
            for mchannel, _ in oChannel.sub_channels():
                self.timeholder.apply_features(mchannel)

        self.timeholder.apply_features(oChannel)
        training_samples = self.annotate(object_lookup,
                                         oLearner, oContainer,
                                         oChannel.get_region(region))

        if training_samples:
            oLearner.add_samples(training_samples)


    def annotate(self, sample_objects, learner, container, region):
        """Annotate predefined class labels to picked samples."""

        training_set = ObjectHolder(region.name)
        training_set.feature_names = region.feature_names

        for class_label, object_ids in sample_objects.iteritems():
            class_name = learner.class_names[class_label]
            hex_color = learner.hexcolors[class_name]

            for obj_id in object_ids:
                obj = region[obj_id]
                obj.iLabel = class_label
                obj.strClassName = class_name
                obj.strHexColor = hex_color
                training_set[obj_id] = obj
        return training_set

    def classify_objects(self, predictor, channel):

        channel = self._channel_registry[channel]
        holder = channel.get_region(predictor.regions)

        try:
            signal_idx = holder.feature_names.index('n2_avg')
            roisize_idx = holder.feature_names.index('roisize')
            has_basic_features = True
        except ValueError:
            has_basic_features = False


        for l, obj in holder.iteritems():

            if obj.aFeatures.size != len(holder.feature_names):
                msg = ('Incomplete feature set found (%d/%d): skipping sample '
                       'object label %s'
                       %(obj.aFeatures.size, len(holder.feature_names), l))
                self.logger.warning(msg)
            elif np.isnan(obj.aFeatures).any():
                msg = ('Feature set containes NaN and is skipped therefore')
                self.logger.warning(msg)
            else:
                label, probs = predictor.predict(obj.aFeatures)
                #, holder.feature_names)
                obj.iLabel = label[0]
                obj.dctProb = probs[0]
                obj.strClassName = predictor.class_names[label[0]]
                obj.strHexColor = predictor.hexcolors[obj.strClassName]

                if has_basic_features:
                    obj.roisize = obj.aFeatures[roisize_idx]
                    obj.signal = obj.aFeatures[signal_idx]
