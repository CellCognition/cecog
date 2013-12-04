from cecog import ccore
from cecog.io.imagecontainer import Coordinate
import os, pickle

class Cutter(object):

    def __init__(self, imoutDir, width=50):
        self.baseOutDir = imoutDir
        self.width = width
        self.track_channel = 'primary'
        self.track_region = 'primary'
        self.img_container_regex = re.compile('\.cecog_imagecontainer___PL(?P<plate>.+)\.pkl')

    def readImageContainer(self, image_container_filename):

        if not os.path.isfile(image_container_filename):
            raise ValueError("%s does not exist. Please provide a valid"
                             "image container file." % image_container_filename)

        img_cont_file = open(image_container_filename, 'r')
        img_container = pickle.load(img_cont_file)
        img_cont_file.close()

        return img_container

    def __call__(self, raw_img_dir, plate, track_data_filename,
                 positions=None, skip_done=True):

        track_data_file = open(track_data_filename, 'r')
        track_data = pickle.load(track_data_file)
        track_data_file.close()

        img_in_dir = os.path.join(raw_img_dir, plate)
        img_container_filenames = filter(lambda x:
                                         not self.img_container_regex(x) is None and
                                         self.img_container_regex(x).groupdict()['plate'] == plate,
                                         os.listdir(img_in_dir))

        if len(img_container_filenames) == 0:
            raise ValueError("No container file found.")
        if len(img_container_filenames) > 0:
            raise ValueError("More than one container file found.")

        img_container_filename = img_container_filenames[0]
        img_container = self.readImageContainer(img_container_filename)

        if positions is None:
            positions = img_container.meta_data.positions

        not_worked = []
        for pos in positions:
            print
            print ' *** PROCESSING POSITION %s %s ***' % (plate, pos)
            try:
                self.cutTracks(track_data, img_container, plate, pos, skip_done=skip_done)
            except:
                print 'a problem occurred while processing %s %s' % (plate, pos)
                not_worked.append(pos)
                continue

        total = len(positions)
        worked = len(not_worked) - total

        print 'processed %i out of %i positions' % (len(worked), len(total))
        print 'elapsed time: %02i:%02i:%02i' % ((diffTime/3600), ((diffTime%3600)/60), (diffTime%60))
        print 'DONE!'

        return

    def cutTracks(self,
                  full_track_data,
                  img_container,
                  plate, pos,
                  lstTracks=None,
                  channels=None,
                  skip_done=False):

        #imoutDir = self.oSettings.galleryDir
        #inDir = os.path.join(self.oSettings.rawImgDir, plate)

        #lstTracks.sort()
        #imgContainer = self.imageImporter(inDir)

        #channels = self.oSettings.plateChannelDict[plate].values()

        #filter(lambda x: x.split('__')[0] != 'feature', impdata['plate1_1_013']['00008']['T00181__O0031']['primary']['primary'].keys())
        #filter(lambda x: x.split('__')[0] != 'feature', impdata['plate1_1_013']['00008']['T00181__O0031']['primary']['primary'].keys())
        #['tracking__upperleft_x', 'tracking__center_x', 'tracking__lowerright_y', 'class__label', 'class__name', 'tracking__lowerright_x', 'tracking__center_y', 'class__probability', 'tracking__upperleft_y']

        if channels is None:
            channels = img_container.meta_data.channels

        imoutDir = os.path.join(self.baseOutDir, plate, pos)
        if not os.path.exists(imoutDir):
            print 'generating the folder %s' % imoutDir
            os.makedirs(imoutDir)

        if lstTracks is None:
            lstTracks = sorted(full_track_data[plate][pos].keys())

        for trackId in lstTracks:
            center_values = zip(full_track_data[plate][pos][trackId][self.track_channel][self.track_region]['tracking__center_x'],
                                full_track_data[plate][pos][trackId][self.track_channel][self.track_region]['tracking__center_y'],
                                full_track_data[plate][pos][trackId][self.track_channel][self.track_region]['Frame'])

            print 'cutting ', trackId
            imout_filename = os.path.join(imoutDir, 'Gallery--%s.png' % (trackId))

            if skip_done and os.path.isfile(imout_filename):
                continue

            # allocate output image
            imout = ccore.Image(len(center_values) * (2*self.width + 1), len(channels) * (2*self.width + 1))

            images = {}
            x = 0
            for cx, cy, timepoint in center_values:
                y = 0
                for channel in channels :
                    #image_filename = os.path.join(inDir, imageInfo[pos][timepoint][channel]['path'],
                    #                              imageInfo[pos][timepoint][channel]['filename'])
                    image_filename = os.path.join(img_container.path,
                                                  img_container.dimension_lookup[pos][timepoint][channel][0])
                    #print image_filename
                    imin = ccore.readImageMito(image_filename)

                    x_ul = cx - self.width if cx >= self.width else 0 # max(cx - width, 0)
                    #x_ul = max(cx - width, 0)
                    y_ul = cy - self.width if cy >= self.width else 0 # max(cy - width, 0)
                    #y_ul = max(cy - width, 0)
                    x_lr = cx + self.width if cx + self.width < imin.width else imin.width - 1
                    #x_lr = min(cx + width, imin.width-1)
                    y_lr = cy + self.width if cy + self.width < imin.height else imin.height - 1
                    #y_lr = min(cx + width, imin.height-1)
                    w_x = x_lr - x_ul
                    w_y = y_lr - y_ul

                    #print x_ul, y_ul, x_lr, y_lr, w_x, w_y

                    imsub = ccore.subImage(imin,
                                           ccore.Diff2D(int(x_ul), int(y_ul)),
                                           ccore.Diff2D(int(w_x), int(w_y)))
                    ccore.copySubImage(imsub, imout, ccore.Diff2D(x, y))
                    y += (2 * self.width + 1)
                x += (2 * self.width + 1)
            ccore.writeImage(imout, imout_filename)

        return

if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("--raw_image_path", dest="raw_image_path",
                      help="raw image directory (base directory)")
    parser.add_option("--out_path", dest="out_path",
                      help="base output path for galleries")
    parser.add_option("--plate", dest="plate",
                      help="plate for cutting")
    parser.add_option("--track_data_filename", dest="track_data_filename",
                      help="filename containing track data")
    parser.add_option("--positions", dest="positions",
                      help="positions to be cut")
    parser.add_option("--skip_done", action="store_true", dest='skip_done',
                      help="if this option is set, tracks with existing galleries are skipped.")
    parser.add_option("--not_skip_done", action="store_false", dest='skip_done',
                      help="if this option is set, tracks with existing galleries are not skipped.")


    (options, args) = parser.parse_args()

    if (options.raw_image_path is None or
        options.out_path is None or
        options.plate is None or
        options.track_data_filename is None):
        parser.error("incorrect number of arguments!")

    if options.skip_done:
        print 'processed positions are skipped.'
    if not options.skip_done:
        print 'processed positions are not skipped.'

    if not options.positions is None:
        positions = [x.strip() for x in options.positions.split(',')]
    else:
        positions = None

    cutter = Cutter(options.out_path)
    cutter(options.raw_image_path, options.plate, options.track_data_filename,
           positions=positions, skip_done=options.skip_done)

