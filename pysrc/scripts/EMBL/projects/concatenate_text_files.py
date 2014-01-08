import os, re, time, sys, pickle

#/Volumes/ellenberg2/Bianca/CellCognition_data/cecog_output/2011-11-24/
# flask1_control/analyzed/statistics/PW00001--P00001__object_counts.txt

baseDir = '/Volumes/ellenberg2/Bianca/CellCognition_data/cecog_output'
outDir = '/Users/twalter/data/Bianca/'

screens = os.listdir(baseDir)
regex = re.compile('PW(?P<position>\d+)--.+__object_counts.txt')

for screen in screens:
    filename = os.path.join(outDir, '%s.txt' % screen)
    header_row = True
    fp = open(filename, 'w')
    plates = os.listdir(os.path.join(baseDir, screen))
    for plate in plates:
        stat_dir = os.path.join(baseDir, screen, plate,
                                'analyzed', 'statistics')
        countfilenames = os.listdir(stat_dir)
        for countfilename in countfilenames:
            searchres = regex.search(countfilename)
            if searchres is None:
                continue
            pos = searchres.groupdict()['position']
            cfp = open(os.path.join(stat_dir, countfilename), 'r')
            temp = cfp.readlines()
            cfp.close()
            if len(temp) < 5:
                print 'a problem occurred in file %s' % countfilename
                continue
            if header_row:
                fp.write('\t'.join(['plate', 'position'] + temp[3].split('\t')[2:]))
                header_row = False
            fp.write('\t'.join([plate, pos] + temp[4].split('\t')[2:] ))
    fp.close()



