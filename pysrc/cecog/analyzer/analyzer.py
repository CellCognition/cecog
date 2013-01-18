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

import numpy as np
from os.path import join
from collections import OrderedDict

from cecog import ccore
from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel
from cecog.analyzer.channel import MergedChannel
from cecog.analyzer.object import ObjectHolder

from cecog.util.logger import LoggerObject
from cecog.util.util import makedirs
from cecog.util.util import hexToRgb

class CellAnalyzer(LoggerObject):

    def __init__(self, time_holder, position, create_images, binning_factor,
                 detect_objects):
        super(CellAnalyzer, self).__init__()

        self.time_holder = time_holder
        self.P = position
        self.bCreateImages = create_images
        self.iBinningFactor = binning_factor
        self.detect_objects = detect_objects

        self._iT = None
        self._channel_registry = OrderedDict()

    def initTimepoint(self, iT):
        self._channel_registry.clear()
        self._iT = iT
        self.time_holder.initTimePoint(iT)

    # XXX rename it to "add_channel"
    def register_channel(self, channel):
        self._channel_registry[channel.NAME] = channel

    def get_channel_names(self):
        return self._channel_registry.keys()

    def get_channel(self, name):
        return self._channel_registry[name]

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

    def process(self, apply=True, extract_features=True):
        """Perform the segmentation and feature extraction."""
        channels = sorted(self._channel_registry.values())
        primary_channel = None

        for channel in channels:
            self.time_holder.prepare_raw_image(channel)
            if self.detect_objects:
                if channel.NAME == PrimaryChannel.NAME:
                    self.time_holder.apply_segmentation(channel)
                    primary_channel = channel
                elif channel.NAME == SecondaryChannel.NAME:
                    self.time_holder.apply_segmentation(channel, primary_channel)
                    secondary_channel = channel
                elif channel.NAME == TertiaryChannel.NAME:
                    self.time_holder.apply_segmentation(channel, primary_channel, secondary_channel)
                elif channel.NAME == MergedChannel.NAME:
                    channel.meta_image = primary_channel.meta_image
                    self.time_holder.apply_segmentation(channel, self._channel_registry)
                else:
                    raise ValueError("Channel with name '%s' not supported." % channel.NAME)

                if extract_features:
                    self.time_holder.apply_features(channel)

        if apply:
            # want apply also the pseudo channels
            for channel in sorted(self._channel_registry.values()):
                self.time_holder.apply_channel(channel)

    def purge(self, features=None):
        for channel in self._channel_registry.values():
            if not features is None and channel.strChannelId in features:
                channelFeatures = features[channel.strChannelId]
            else:
                channelFeatures = None
            channel.purge(features=channelFeatures)

    def exportLabelImages(self, pathOut, compression='LZW'):
        # TODO no label images for virtual channels
        for name, channel in self.proc_channels.iteritems():
            channel_id = channel.strChannelId
            for strRegion, oContainer in channel.containers.iteritems():
                strPathOutImage = join(pathOut, channel_id, strRegion)
                makedirs(strPathOutImage)
                oContainer.exportLabelImage(join(strPathOutImage,
                                                 'P%s_T%05d.tif' % (self.P, self._iT)),
                                            compression)

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
#                        print len(lstImages)
                        lstImages.append((oChannel.meta_image.image, strHexColor, 1.0))
#                        print len(lstImages)

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
                                    #print dctLabels
#                                    imgRaw = oChannel.meta_image.image
                                    imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                    for iLabel, lstObjIds in dctLabels.iteritems():
                                        imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                        ### Flip this and use drawContours with fill option enables to get black background
                                        oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
#                                        oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, True)
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
                                        [ccore.RGBValue(*hexToRgb(x[1])) for x in lstImages],
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

    def collectObjects(self, plate_id, P, sample_readers, oLearner, byTime=True):
        self.logger.debug('* collecting samples...')
        self.process(apply = False, extract_features = False)

        region_images = dict()
        training_data = OrderedDict()
        feature_names = []

        for chname, region in oLearner.channels.iteritems():
            oChannel = self._channel_registry[chname]
            oContainer = oChannel.get_container(region)
            objects = oContainer.getObjects()
            object_lookup = {}
            object_ids = set()

            for reader in sample_readers:
                if (byTime and P == reader.getPosition() and self._iT in reader):
                    coords = reader[self._iT]
                elif (not byTime and P in reader):
                    coords = reader[P]
                else:
                    coords = None

                if coords is not None:
                    for data in coords:
                        label = data['iClassLabel']
                        if (label in oLearner.dctClassNames and
                            0 <= data['iPosX'] < oContainer.width and
                            0 <= data['iPosY'] < oContainer.height):

                            center1 = ccore.Diff2D(data['iPosX'], data['iPosY'])
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

            self.time_holder.apply_features(oChannel)
            tdata = self.exportObjects(plate_id, object_lookup,
                                                 oLearner, oContainer,
                                                 oChannel.get_region(region))

            # book keeping btw. color channels
            # XXX move this functionality to the learner class
            for label, sample in tdata.iteritems():
                if training_data.has_key(label):
                    td = training_data[label]
                    td["features"] = np.append(td['features'], np.array(sample.aFeatures))
                    td["files"].append(sample.sample_id)
                    assert td["class"] == sample.iLabel
                else:
                    training_data[label] = {"features": np.array(sample.aFeatures),
                                            "files": [sample.sample_id],
                                            "class": sample.iLabel}

            # book keeping for feature names
            # move this functionality to the learner class_name
            if len(oLearner.channels) > 1:
                pfx = "%s_%s" %(chname, region)
                feature_names.extend(["_".join((pfx, f)) for f in oChannel.lstFeatureNames])
            else:
                feature_names.extend(oChannel.lstFeatureNames)

            name = join(oLearner.controls_dir, "P%s_T%05d_C%s_R%s.jpg"
                        %(self.P, self._iT, oLearner.color_channel, region))
            oContainer.exportRGB(name, "90")
            region_images["%s_%s" %(chname.lower(), region)] = oContainer.img_rgb

        oLearner.set_training_data(training_data, feature_names)
        return region_images

    def exportObjects(self, plate, sample_objects, learner, container, region):
        """
        Exports mask and images of annotated objects after picking.
        Also draw labels and cirles.
        """

        learner_objects = {}
        for label, object_ids in sample_objects.iteritems():
            class_name = learner.dctClassNames[label]
            hex_color = learner.dctHexColors[class_name]
            rgb_value = ccore.RGBValue(*hexToRgb(hex_color))

            for obj_id in object_ids:
                obj = region[obj_id]
                obj.iLabel = label
                obj.strClassName = class_name
                obj.strHexColor = hex_color

                if (obj.oRoi.upperLeft[0] >= 0 and
                    obj.oRoi.upperLeft[1] >= 0 and
                    obj.oRoi.lowerRight[0] < container.width and
                    obj.oRoi.lowerRight[1] < container.height):

                    learner_objects[obj_id] = obj

                    cxi, cyi = obj.oCenterAbs
                    label_dir = join(learner.samples_dir, class_name)
                    makedirs(label_dir)
                    samplefile = 'PL%s___P%s___T%05d___X%04d___Y%04d' \
                        %(plate, self.P, self._iT, cxi, cyi)
                    obj.sample_id = samplefile
                    imgfile = join(label_dir, '%s___img.png' %samplefile)
                    mskfile = join(label_dir, '%s___msk.png' %samplefile)

                    # FIXME: export Objects is segfaulting for objects
                    #        where its bounding box is touching the border
                    #        i.e. one corner point equals zero!
                    container.exportObject(obj_id, imgfile, mskfile)
                    container.markObjects([obj_id], rgb_value, False, True)
                    ccore.drawFilledCircle(ccore.Diff2D(cxi, cyi),
                                           3, container.img_rgb, rgb_value)
        return learner_objects

    def classify_objects(self, predictor):
        channel = self._channel_registry[predictor.name]
        holder = channel.get_region(predictor.regions)
        for label, obj in holder.iteritems():
            if obj.aFeatures.size != len(holder.feature_names):
                msg = ('Incomplete feature set found (%d/%d): skipping sample '
                       'object label %s'
                       %(obj.aFeatures.size, len(holder.feature_names), label))
                self.logger.warning(msg)
            else:
                label, probs = predictor.predict(obj.aFeatures, holder.feature_names)
                obj.iLabel = label
                obj.dctProb = probs
                obj.strClassName = predictor.dctClassNames[label]
                obj.strHexColor = predictor.dctHexColors[obj.strClassName]
                self.time_holder.serialize_classification(predictor.name, holder, predictor)
