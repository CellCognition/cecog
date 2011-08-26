'''
Copyright (c) 2005-2007 by Michael Held
'''

#------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       shutil, \
       random, \
       logging

#------------------------------------------------------------------------------
# extension module imports:
#
from pdk.fileutils import (safe_mkdirs,
                           collect_files,
                           collect_files_by_regex,
                           )

#------------------------------------------------------------------------------
# cecog module imports:
#
from cecog import ccore
from cecog.util.util import read_table

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# functions:
#
def compose_galleries(path, path_hmm, quality="90", one_daughter=True, sample=30):
    logger = logging.getLogger('compose_galleries')
    column_name = 'Trajectory'
    path_index = os.path.join(path_hmm, '_index')
    if not os.path.isdir(path_index):
        logger.warning("Index path '%s' does not exist. Make sure the error correction was executed successfully." %
                       path_index)
        return

    for filename in os.listdir(path_index):
        logger.info('Creating gallery overview for %s' % filename)
        group_name = os.path.splitext(filename)[0]
        t = read_table(os.path.join(path_index, filename))[1]
        t.reverse()

        if one_daughter:
            for record in t[:]:
                if record[column_name].split('__')[4] != 'B01':
                    t.remove(record)

        n = len(t)
        if not sample is None and sample <= n:
            idx = random.sample(xrange(n), sample)
            idx.sort()
            d = [t[i] for i in idx]
        else:
            d = t

        n = len(d)
        results = {}
        for idx, record in enumerate(d):
            #print idx, record
            traj = record[column_name]
            items = traj.split('__')
            pos = items[1][1:]
            key = '__'.join(items[1:5])

            gallery_path = os.path.join(path, 'analyzed', pos, 'gallery')
            if os.path.isdir(gallery_path):
                for gallery_name in os.listdir(gallery_path):

                    img = ccore.readImageRGB(os.path.join(gallery_path, gallery_name, '%s.jpg' % key))

                    if gallery_name not in results:
                        results[gallery_name] = ccore.RGBImage(img.width, img.height*n)
                    img_out = results[gallery_name]
                    ccore.copySubImage(img,
                                       ccore.Diff2D(0, 0),
                                       ccore.Diff2D(img.width, img.height),
                                       img_out,
                                       ccore.Diff2D(0, img.height*idx))

        for gallery_name in results:
            path_out = os.path.join(path_hmm, '_gallery', gallery_name)
            safe_mkdirs(path_out)
            image_name = os.path.join(path_out, '%s.jpg' % group_name)
            ccore.writeImage(results[gallery_name], image_name, quality)
            logger.debug("Gallery image '%s' successfully written." % image_name)

        yield group_name

#------------------------------------------------------------------------------
# classes:
#


class EventGallery(object):

    IMAGE_CLASS = ccore.RGBImage
    PROCESS_LABEL = False

    @staticmethod
    def read_image(name):
        return ccore.readImageRGB(name)

    def _format_name(self, pos, frame, obj_id, branch_id):
        s = "P%s__T%05d__O%04d" % (pos, frame, obj_id)
        if not branch_id is None:
            s += '__B%02d' % branch_id
        return s

    def __init__(self, oTracker, strPathIn, oP, strPathOut,
                 imageCompression="85",
                 imageSuffix=".jpg",
                 border=0,
                 writeSubdirs=True,
                 writeDescription=True,
                 method='objectCentered',
                 format=None,
                 size=None,
                 oneFilePerTrack=False):

        self._bHasImages = False
        dctTimePoints = {}

        for strStartId, lstTimeData in oTracker.getBoundingBoxes(method=method, size=size, border=border).iteritems():
            items = oTracker.getComponentsFromNodeId(strStartId)
            iStartT, iObjId = items[:2]
            if len(items) == 3:
                branch_id = items[2]
            else:
                branch_id = 1

            if writeSubdirs:
                strPathOutEvent = os.path.join(strPathOut,
                                               self._format_name(oP, iStartT, iObjId, branch_id))
            else:
                strPathOutEvent = strPathOut
            safe_mkdirs(strPathOutEvent)

            if writeDescription:
                oFile = file(os.path.join(strPathOutEvent,
                                          "_%s.txt" % self._format_name(oP, iStartT, iObjId, branch_id)), "w")
                lstData = ["Frame", "ObjId", "x1", "y1", "x2", "y2"]
                oFile.write("%s\n" % "\t".join(map(str, lstData)))

            for iCnt, (iT, tplBoundingBox, lstObjIds) in enumerate(lstTimeData):

                if writeDescription:
                    lstData = [iT, ';'.join(map(str, lstObjIds))] + list(tplBoundingBox)
                    oFile.write("%s\n" % "\t".join(map(str, lstData)))
                if not iT in dctTimePoints:
                    dctTimePoints[iT] = []
                dctTimePoints[iT].append((strStartId, lstObjIds, iCnt, strPathOutEvent, tplBoundingBox))

            if writeDescription:
                oFile.close()

        for idx, (iT, lstItems) in enumerate(dctTimePoints.iteritems()):

            #print iT, lstItems
            imgXY = self._getImage(strPathIn, iT)

            for strStartId, lstObjIds, iCnt, strPathOutEvent, tplBoundingBox in lstItems:

                x1, y1, x2, y2 = tplBoundingBox
                x1Corr = 0 if x1 < 0 else x1
                y1Corr = 0 if y1 < 0 else y1
                x2Corr = imgXY.width-1 if x2 >= imgXY.width else x2
                y2Corr = imgXY.height-1 if y2 >= imgXY.height else y2

#                print x1, x1Corr
#                print y1, y1Corr
#                print x2, x2Corr
#                print y2, y2Corr
                imgSub = ccore.subImage(imgXY,
                                        ccore.Diff2D(x1Corr, y1Corr),
                                        ccore.Diff2D(x2Corr-x1Corr+1, y2Corr-y1Corr+1))

                if (x1 < 0 or y1 < 0 or
                    x2 >= imgXY.width or y2 >= imgXY.height):
#                    print " * ", x2-x1+1
#                    print " * ", y2-y1+1
#                    m = ccore.Diff2D(x1Corr-x1, y1Corr-y1)
#                    print " * ", m.x, m.y
                    imgSub2 = self.IMAGE_CLASS(size[0], size[1])
                    ccore.copySubImage(imgSub, imgSub2, ccore.Diff2D(x1Corr-x1, y1Corr-y1))
                    imgSub = imgSub2

#                print "w", imgSub.width, size[0], x2-x1+1
#                print "h", imgSub.height, size[1], y2-y1+1
                assert imgSub.width == size[0]
                assert imgSub.width == x2-x1+1
                assert imgSub.height == size[1]
                assert imgSub.height == y2-y1+1

                if self.PROCESS_LABEL:
                    lstImages = []
                    for iObjId in lstObjIds:
                        lstImages.append(ccore.copyImageIfLabel(imgSub, imgSub, iObjId))
                    imgSub = ccore.projectImage(lstImages, ccore.ProjectionType.MaxProjection)

                strFilenameImage = os.path.join(strPathOutEvent, "P%s__T%05d%s" % (oP, iT, imageSuffix))
                ccore.writeImage(imgSub,
                                 strFilenameImage)

        if oneFilePerTrack and os.path.isdir(strPathOut):
            self.convertToOneFilePerTrack(strPathOut, imageCompression)


    @classmethod
    def convertToOneFilePerTrack(cls, path_out, image_compression=''):
        for event_id in os.listdir(path_out):
            event_path = os.path.join(path_out, event_id)
            #print event_path
            if os.path.isdir(event_path):
                # get all image cutter files
                filenames = collect_files(event_path,
                                          extensions=['.jpg', '.png', '.tif'],
                                          absolute=True)
                if len(filenames) > 0:
                    img_out = None
                    # determine file extension
                    ext = os.path.splitext(filenames[0])[1]

                    # stitch image horizontally
                    for idx, filename in enumerate(filenames):
                        img = cls.read_image(filename)
                        if img_out is None:
                            size = img.width, img.height
                            img_out = cls.IMAGE_CLASS(size[0] * len(filenames),
                                                      size[1])
                        ccore.copySubImage(img,
                                           ccore.Diff2D(0, 0),
                                           ccore.Diff2D(size[0], size[1]),
                                           img_out,
                                           ccore.Diff2D(size[0]*idx, 0))

                    # save a one file with event_id (P,T,O) + extension
                    filename_out = os.path.join(path_out, event_id) + ext
                    #print filename_out
                    ccore.writeImage(img_out,
                                     filename_out)

                    path_out_info = os.path.join(path_out, '_info')
                    safe_mkdirs(path_out_info)
                    shutil.copy2(os.path.join(event_path, '_%s.txt' % event_id),
                                 os.path.join(path_out_info, '_%s.txt' % event_id))
                    shutil.rmtree(event_path, ignore_errors=True)


    def _getImage(self, strPathIn, iT):
        if not self._bHasImages:
            self._dctImages = {}
            self._bHasImages = True
            lstResults = collect_files_by_regex(strPathIn,
                                                '.*?_T(?P<T>\d+).*?',
                                                extensions=['.jpg', '.png', '.tif'],
                                                absolute=True)
            for strFilename, oMatch in lstResults:
                iTime = int(oMatch.group('T'))
                self._dctImages[iTime] = strFilename
            #print self._dctImages

        img = self.read_image(self._dctImages[iT])
        return img


class EventGalleryLabel(EventGallery):

    IMAGE_CLASS = ccore.Int16Image
    PROCESS_LABEL = True

    @staticmethod
    def read_image(name):
        return ccore.readImageInt16(name)


#-------------------------------------------------------------------------------
# main:
#
if __name__ == "__main__":
    compose_galleries("/Volumes/share-gerlich-2-$/juan/Analysis/mimics_secondary_screening_H2B_3/001658",
                      "/Volumes/share-gerlich-2-$/juan/Analysis/mimics_secondary_screening_H2B_3/001658/hmm/primary_byoligo",
                      one_daughter=True,
                      sample=400)

