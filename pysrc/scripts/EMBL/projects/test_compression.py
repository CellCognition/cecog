from cecog import ccore
from optparse import OptionParser

import re, time, os, sys
import shutil, pickle
import numpy

#--W00049--P00001--T02460--TR02570--SL00001--O03--Q01--F06--A01--C00--L00--PL01--I0020.png
positionRegex = "W(?P<P>\d+)"
BASEDIR = '/Users/twalter/data/compression'
MITODIR = '/Users/mitocheck/Thomas/mitocheck_links'
#I2--W00194--P00001--Z00000--T00034--GFP.tif
STRMITOREGEX = ".*W(?P<well>\d+)--P(?P<pos>\d+).+--T(?P<abstime>\d+)--.+\.(?P<suffix>[a-zA-Z]+)"

import scripts.EMBL.plotter.stats
reload(scripts.EMBL.plotter.stats)
#from scripts.EMBL.plotter import stats

class CompressionTester(object):

    def __init__(self, str_regex=STRMITOREGEX, mito_folder=MITODIR, base_folder=BASEDIR):
        self.regex = re.compile(STRMITOREGEX)
        self.base_folder = base_folder
        self.single_image_output_folder = os.path.join(self.base_folder, 'single_image_output_folder')
        self.compare_directory = os.path.join(self.base_folder, 'image_comparison')
        self.plot_folder = os.path.join(self.base_folder, 'plots')
        self.mitoDir = mito_folder
        self.pickleDir = os.path.join(self.base_folder, 'pickle')

        for folder in [self.compare_directory, self.plot_folder,
                       self.pickleDir, self.single_image_output_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        self.test_compression_list = [ ('png', '100'),
                                       ('jpg', '100'),
                                       ('jpg', '99'),
                                       ('jpg', '98'),
                                       ('jpg', '97'),
                                       ('jpg', '96'),
                                       ('jpg', '95'),
                                       ('jpg', '93'),
                                       ('jpg', '90')]

        return

    def readPickleFiles(self, pickleDir=None, idL=None):
        if pickleDir is None:
            pickleDir = self.pickleDir
        filenames = os.listdir(pickleDir)
        q = {}
        s = {}
        for filename in filenames:
            full_filename = os.path.join(pickleDir, filename)
            regex = re.compile("compression_quality_(?P<id>.+)\.pickle")
            searchres =  regex.search(filename)
            if searchres is None:
                print 'skipping %s' % filename
                continue
            id = searchres.groupdict()['id']
            if not idL is None and not id in idL:
                continue
            #print 'reading %s' % full_filename
            fp = open(full_filename, 'r')
            q[id], s[id] = pickle.load(fp)
            fp.close()
        return q, s

    def makeBarplotsForClassificationErrors(self, res):
        #for suffix, comp in self.test_compression_list:
        bp = scripts.EMBL.plotter.stats.Barplot()
        datavec = numpy.array([numpy.mean([res[comp][id][0]
                                           for id in res[comp].keys()])
                              for comp in self.test_compression_list[1:]],
                              dtype=numpy.float)
        errorvec = numpy.array([numpy.std([res[comp][id][0]
                                           for id in res[comp].keys()])
                               for comp in self.test_compression_list[1:]],
                               dtype=numpy.float)

        filename = os.path.join(self.plot_folder, 'absolute_classificationerrors.png' )
        bp.singleBarplot(datavec, filename,
                         errorvec=errorvec,
                         bartitles=self.test_compression_list[1:],
                         title = 'average number of classification errors for different compression levels',
                         xlab='', ylab='')

        datavec = numpy.array([numpy.mean([float(res[comp][id][0]) / float(res[comp][id][1])
                                           for id in res[comp].keys()])
                              for comp in self.test_compression_list[1:]],
                              dtype=numpy.float)
        errorvec = numpy.array([numpy.std([float(res[comp][id][0]) / float(res[comp][id][1])
                                           for id in res[comp].keys()])
                               for comp in self.test_compression_list[1:]],
                               dtype=numpy.float)

        filename = os.path.join(self.plot_folder, 'relative_classificationerrors.png' )
        bp.singleBarplot(datavec, filename,
                         errorvec=errorvec,
                         bartitles=self.test_compression_list[1:],
                         title = 'average percentage of classification errors for different compression levels',
                         xlab='', ylab='')

        return

    def makeBarplots(self, q, s):
        bp = scripts.EMBL.plotter.stats.Barplot()
        for feature in ['sum_abs_diff', 'max_abs_diff', 'mean_diff', 'nb_pix_largerthan2']:
            #q[id][('jpg', '95')][0]['mean_diff']
            #datavec = numpy.array([numpy.mean([q[x][i][feature] for i in range(len(q[x])) ])
            #                       for x in self.test_compression_list], dtype=numpy.float)
            datavec = numpy.array([numpy.mean(numpy.concatenate([ [q[id][x][i][feature]
                                   for i in range(len(q[id][x]))]
                                   for id in q.keys()]))
                                   for x in self.test_compression_list],
                                   dtype=numpy.float)
            errorvec = numpy.array([numpy.std(numpy.concatenate([ [q[id][x][i][feature]
                                    for i in range(len(q[id][x]))]
                                    for id in q.keys()]))
                                    for x in self.test_compression_list],
                                    dtype=numpy.float)

            #datavec = numpy.array([numpy.mean([q[x][i][feature] for i in range(len(q[x])) ])
            #                       for x in self.test_compression_list], dtype=numpy.float)
            filename = os.path.join(self.plot_folder, '%s.png' % feature)
            bp.singleBarplot(datavec, filename,
                             errorvec=errorvec,
                             bartitles=self.test_compression_list,
                             title = 'Quality measurements for different compression levels: %s' % feature,
                             xlab='', ylab='')

        filename = os.path.join(self.plot_folder, 'size.png')
        #s['LT0138_01--213'][('jpg', '99')][0]
        datavec = \
            numpy.array(
                        [numpy.mean([s[id][self.test_compression_list[0]][0]
                                     for id in s.keys()])] +
                        [numpy.mean([s[id][x][1] for id in s.keys()])
                         for x in self.test_compression_list], dtype=numpy.float)
        errorvec = \
            numpy.array(
                        [numpy.std([s[id][self.test_compression_list[0]][0]
                                    for id in s.keys()])] +
                        [numpy.std([s[id][x][1] for id in s.keys()])
                         for x in self.test_compression_list], dtype=numpy.float)

        #datavec=numpy.array([numpy.mean([s[x][i][0] for i in range(len(q[x])) ])
        #                     for x in self.test_compression_list], dtype=numpy.float)
        bp.singleBarplot(datavec, filename,
                         errorvec=errorvec,
                         bartitles=['Original'] + self.test_compression_list,
                         title = 'Size comparison',
                         xlab='', ylab='Size per movie in MB')

        complete_size = 545 * 384 * 1e-6 * datavec
        complete_error = 545 * 384 * 1e-6 * errorvec
        filename = os.path.join(self.plot_folder, 'expected_size_complete.png')
        bp.singleBarplot(complete_size, filename,
                         errorvec=complete_error,
                         bartitles=['Original'] + self.test_compression_list,
                         title = 'Expected sizes of the mitocheck data set',
                         xlab='', ylab='Extected size of the data set in TB')
        return

    def _compare_image_sequences(self, in_path, out_path):
        se_in = self._get_image_sequence(in_path)
        se_out = self._get_image_sequence(out_path)
        quality = []
        for in_filename, out_filename in zip(se_in, se_out):
            img1 = ccore.readImageMito(in_filename)
            img2 = ccore.readImage(out_filename)
            quality.append(self.quantifyGreyLevelDifference(img1, img2))

        return quality

    def compare_classification_results(self):
        analysis_dir = '/Volumes/mitocheck/Thomas/compression/out/analysis'
        res = {}
        for suffix, comp in self.test_compression_list[1:]:
            print suffix, comp
            res[(suffix, comp)] = {}
            subdir = '_'.join([suffix, comp])
            compdir = os.path.join(analysis_dir, subdir, 'results')
            plates = os.listdir(compdir)
            for plate in plates:
                platedir = os.path.join(compdir, plate, 'results')
                positions = os.listdir(platedir)
                for pos in positions:
                    posdir = os.path.join(platedir, pos)
                    found_files = filter(lambda x: os.path.isfile(os.path.join(posdir, x)),
                                         os.listdir(posdir))
                    if len(found_files) != 1:
                        continue
                    test_filename = os.path.join(posdir, found_files[0])
                    gt_filename = test_filename.replace(subdir, 'png')
                    if not os.path.isfile(gt_filename):
                        continue
                    res[(suffix, comp)][(plate, pos)] = self.quantifyClassificationDifference(gt_filename, test_filename)
            diffTime = time.time() - startTime
            print 'elapsed time: %02i:%02i:%02i' % ((diffTime/3600), ((diffTime%3600)/60), (diffTime%60) )

        #/jpg_90/results/LT0001_02/results/W00001_P00001/Analysis_LT0001_02_W00001_P00001_prediction_track.dat'
        #Analysis_LT0001_02_W00001_P00001_prediction_track.dat
        return res

    def convert_and_compare_from_id_list(self, filename=None, id=None):
        if not filename is None:
            fp = open(filename, 'r')
            idL = [x.strip() for x in fp.readlines()]
            fp.close()
            if not id is None:
                print 'id %s is ignored (filename given)' % id
        else:
            idL = [id]

        for id in idL:
            quality = {}
            sizes = {}

            plate, pos = id.split('--')
            for suffix, jpg_compression in self.test_compression_list:
                quality[(suffix, jpg_compression)], sizes[(suffix, jpg_compression)] = \
                    self._convert_images_and_compare(plate, pos, suffix, jpg_compression)
            fp = open(os.path.join(self.pickleDir, 'compression_quality_%s.pickle' % id), 'w')
            pickle.dump((quality, sizes), fp)
            fp.close()
        return

    def _convert_images_and_compare(self, plate, pos, suffix, jpg_compression):

        plate_folders = filter(lambda x: x[0:len(plate)] == plate, os.listdir(self.mitoDir))
        if not len(plate_folders) == 1:
            print 'no folder found for plate %s' % plate
            print 'skipping %s %s' % (plate, pos)
            return

        plate_folder = os.path.join(self.mitoDir, plate_folders[0])

        pos_folders = filter(lambda x: x[0:len(pos)] == pos, os.listdir(plate_folder))
        if not len(plate_folders) == 1:
            print 'no folder found for position %s %s' % (plate, pos)
            print 'skipping %s %s' % (plate, pos)
            return
        pos_folder = os.path.join(plate_folder, pos_folders[0])
        in_path = pos_folder

        if suffix == 'jpg':
            out_path = os.path.join(self.single_image_output_folder, '_'.join([suffix, jpg_compression]),
                                    plate, pos)
        else:
            out_path = os.path.join(self.single_image_output_folder, suffix, plate, pos)

        if not os.path.isdir(out_path):
            os.makedirs(out_path)

        print in_path, out_path

        self._convert_image_sequence(in_path, out_path, suffix, jpg_compression)
        quality = self._compare_image_sequences(in_path, out_path)
        sizes = (sum([os.path.getsize(os.path.join(in_path, f)) for f in os.listdir(in_path)]) / 1e6,
                 sum([os.path.getsize(os.path.join(out_path, f)) for f in os.listdir(out_path)]) / 1e6)

        return quality, sizes


    def _DEPRECATED_make_conversion_and_quality_comparison(self, in_path, suffix='png', jpg_compression='100'):
        if suffix == 'jpg':
            out_path = os.path.join(self.compare_directory, '_'.join([suffix, jpg_compression]))
        else:
            out_path = os.path.join(self.compare_directory, suffix)

        if not os.path.exists(out_path):
            os.makedirs(out_path)

        print in_path, out_path

        self._convert_image_sequence(in_path, out_path, suffix, jpg_compression)
        quality = self._compare_image_sequences(in_path, out_path)
        sizes = (sum([os.path.getsize(os.path.join(in_path, f)) for f in os.listdir(in_path)]) / 1e6,
                 sum([os.path.getsize(os.path.join(out_path, f)) for f in os.listdir(out_path)]) / 1e6)
        return quality, sizes

    def compare_difference_images_for_compression(self):
        in_path = '/Users/twalter/data/compression/originals/049--05--01--(1,2)--28431--INCENP'

        quality = {}
        sizes = {}

        for suffix, jpg_compression in self.test_compression_list:
            quality[(suffix, jpg_compression)], sizes[(suffix, jpg_compression)] = \
                self._make_conversion_and_quality_comparison(in_path, suffix, jpg_compression)

        return quality, sizes

    def findAllFiles(self, in_path):
        return
    
    def convertFullPlate(self, in_path, out_path, plate, suffix='png',
                         jpg_compression='100'):

        plate_folders = filter(lambda x: x[0:len(plate)] == plate, os.listdir(in_path))
        if not len(plate_folders) == 1:
            print 'no folder found for plate %s' % plate
            print 'skipping %s %s' % (plate, pos)
            return

        plate_folder = os.path.join(in_path, plate_folders[0])

        regex = re.compile('^[0-9]{3}')
        pos_folders = filter(lambda x: os.path.isdir(os.path.join(plate_folder, x))
                             and not regex.match(x) is None,
                             os.listdir(plate_folder))

        if len(pos_folders) == 0:
            print 'no folder found for position %s' % plate
            print 'skipping %s' % plate
            return
        for pos_folder in sorted(pos_folders):
            startTime = time.time()
            image_in_folder = os.path.join(plate_folder, pos_folder)
            image_out_folder = os.path.join(out_path, plate_folders[0], pos_folder)
            if not os.path.isdir(image_out_folder):
                os.makedirs(image_out_folder)
            self._convert_image_sequence(image_in_folder, image_out_folder,
                                         suffix, jpg_compression)

            diffTime = time.time() - startTime
            print 'converting %s %s: %02i:%02i:%02i' % (plate, pos_folder,
                                                        (diffTime/3600), ((diffTime%3600)/60), (diffTime%60))

        print 'DONE!'
        return

    def _convert_image_sequence(self, in_path, out_path, suffix='png', jpg_compression='100'):
        lst_image_filenames = self._get_image_sequence(in_path)
        for filename in lst_image_filenames:
            img = ccore.readImageMito(filename)
            new_filename = os.path.splitext(os.path.basename(filename))[0] + '.' +  suffix
            if suffix == 'jpg':
                ccore.writeImage(img, os.path.join(out_path, new_filename), compression=jpg_compression)
            else:
                ccore.writeImage(img, os.path.join(out_path, new_filename))
        return

    def readClassificationResult(self, filename):
        fp = open(filename, 'r')
        tempL = [x.strip() for x in fp.readlines()]
        fp.close()
        header = tempL[0].split('\t')
        res = dict(zip(header, [[] for i in header]))
        for line in tempL[1:]:
            current_data = [int(x) for x in line.split('\t')]
            for i in range(len(header)):
                res[header[i]].append(current_data[i])
        return res

    def quantifyClassificationDifference(self, filename_ground_truth, filename_test):
        res_ground_truth = self.readClassificationResult(filename_ground_truth)
        res_test = self.readClassificationResult(filename_test)

        # classes correspond to rows
        phenoClasses = sorted(res_test.keys())
        X_gt = numpy.array([res_ground_truth[phenoClass] for phenoClass in phenoClasses])
        X = numpy.array([res_test[phenoClass] for phenoClass in phenoClasses])

        classification_errors = numpy.abs(X - X_gt).sum() / 2
        total_number_classifications = X.sum()
        return classification_errors, total_number_classifications

    def quantifyGreyLevelDifference(self, img1, img2):

        Ap = img1.toArray(copy=True)
        A = Ap[:,:].astype(int)

        Bp = img2.toArray(copy=True)
        B = Bp[:,:].astype(int)

        C = A - B
        absC = numpy.abs(C)
        q = {
             'max_diff': C.max(),
             'min_diff': C.min(),
             'max_abs_diff': absC.max(),
             'sum_abs_diff': absC.sum(),
             'mean_diff': absC.mean(),
             'nb_pix_largerthan1': (absC > 1).sum(),
             'nb_pix_largerthan2': (absC > 2).sum(),
             'nb_pix_largerthan3': (absC > 3).sum(),

             }

        return q

    def _get_image_sequence(self, in_path):
        #filenames = filter(lambda x: not self.regex.search(x) is None,os.listdir(in_path))
        image_names = {}
        for filename in os.listdir(in_path):
            searchres = self.regex.search(filename)
            if searchres is None:
                continue
            well = searchres.groupdict()['well']
            image_time = searchres.groupdict()['abstime']
            image_names[image_time] = os.path.join(in_path, filename)

        lst_image_filenames = [image_names[t] for t in sorted(image_names.keys())]

        return lst_image_filenames

    def _copy_as_numbered_sequ(self, lst_image_filenames, out_path):
        i = 0
        for filename in lst_image_filenames:
            basename, suffix = os.path.splitext(filename)
            new_filename = 'image%02i%s' % (i, suffix)
            shutil.copy(filename, os.path.join(out_path, new_filename))
            i += 1

        return

if __name__=="__main__":

    parser = OptionParser()

    parser.add_option("-i", "--in_path", dest="in_path",
                      help="input directory containing the plates")
    parser.add_option("-o", "--out_path", dest="out_path",
                      help="output directory containing the plates")
    parser.add_option("-f", "--filename", dest="filename",
                      help="Filename for list of spot identifiers")
    parser.add_option("--id", dest="id",
                      help="ID of the experiment (Mitocheck specific)")
    parser.add_option("--lt", dest="lt",
                      help="labtek ID (in case a full labtek is to be compressed"
                      "It only makes sense if --id is not used")
    parser.add_option("--make_compression", action="store_true", dest="make_compression",
                      help="Performs the compression")
    parser.add_option("--make_comparison", action="store_true", dest="make_comparison",
                      help="Makes the comparison")

    (options, args) = parser.parse_args()

    if (options.in_path is None) or (options.out_path is None):
        parser.error("incorrect number of arguments!")

    if not options.lt is None and not options.id is None:
        parser.error("It is not allowed to specify the experiment ID and the Labtek ID.")

    ct = CompressionTester(mito_folder=options.in_path,
                           base_folder=options.out_path)
    if options.make_comparison:
        ct.convert_and_compare_from_id_list(filename=options.filename,
                                            id=options.id,
                                            lt=options.lt)
    if options.make_compression:
        ct.convertFullPlate(options.in_path, options.out_path,
                            options.lt, suffix='png',
                            jpg_compression='100')



