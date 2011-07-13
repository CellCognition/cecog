
import re
import os
import time

from optparse import OptionParser

# Settings (to go into a separate settings file)
regexScheme = {
               "strRegexPosition" : "W(?P<P>\d+)",
               "strRegexField"    : "P(?P<F>\d+)",
               "strRegexTime"     : "T(?P<T>\d+)",
               #"strRegexChannel"  : "C(?P<C>\d+)",
               "strRegexChannel"  : "--(?P<C>\w+-?\w+)\.",
               "strRegexZSlice"   : "Z(?P<Z>\d+)",
               }

# defines what elements are used for identification of an experiment
# they are concatenated (separated by sep)
EXP_DEFINITION = {
                  #'keys': ('P'),
                  'keys': ('P', 'F'),
                  'sep': '_'
                  }

# entries that are to be exported (in this order); the first column is always filename
ENTRIES = ['path', 'exp_id', 'P', 'F', 'T', 'C', 'Z']

# only image with these suffixes are interpreted (lower or upper case)
imageSuffixes = ['tif', 'tiff']

# Takes a dictionary with regular expression strings
# When called with string argument, applies these regular expressions to the string
# and gives back a dictionary with the information that could be retrieved.
class RegexFilenameInterpreter(object):

    def __init__(self, regexScheme):
        self.regexScheme = regexScheme
        regexKeys = regexScheme.keys()
        self.regexObjects = dict(zip(regexKeys, [re.compile(regexScheme[x]) for x in regexKeys]))
        return

    def __call__(self, filename):
        info ={}
        for key, regexObj in self.regexObjects.iteritems():
            match_res = regexObj.search(filename)
            if not match_res is None:
                info.update(match_res.groupdict())
#
#            else:
#                print '%s did not match the regular expression (key: %s)' % (filename, key)
        return info

def relpath(target, base=os.curdir):
    """
    Return a relative path to the target from either the current dir or an optional base dir.
    Base can be a directory specified either as absolute or relative to current dir.
    """

    if not os.path.exists(target):
        raise OSError, 'Target does not exist: '+target

    if not os.path.isdir(base):
        raise OSError, 'Base is not a directory or does not exist: '+base

    if os.path.samefile(target, base):
        return ''

    base_list = (os.path.abspath(base)).split(os.sep)
    target_list = (os.path.abspath(target)).split(os.sep)

    # On the windows platform the target may be on a completely different drive from the base.
    if os.name in ['nt','dos','os2'] and base_list[0] <> target_list[0]:
        raise OSError, 'Target is on a different drive to base. Target: '+target_list[0].upper()+', base: '+base_list[0].upper()

    # Starting from the filepath root, work out how much of the filepath is
    # shared by base and target.
    for i in range(min(len(base_list), len(target_list))):
        if base_list[i] <> target_list[i]: break
    else:
        # If we broke out of the loop, i is pointing to the first differing path elements.
        # If we didn't break out of the loop, i is pointing to identical path elements.
        # Increment i so that in all cases it points to the first differing path elements.
        i+=1

    rel_list = [os.pardir] * (len(base_list)-i) + target_list[i:]
    return os.path.join(*rel_list)




class CoordinatesGeneration(object):
    def __init__(self, expDefinition=EXP_DEFINITION):
        self.expDefinition = expDefinition
        return

    # takes a base directory, a filename interpreter class and a list of entries (optional) to be retrieved from the filenames.
    # retrieves all images with suffixes defined above.
    # retrieves information from filenames according to filenameInterpreter (can be based on regular expr)
    # gives back a dictionary containing for each filename the retrieved coordinates
    # if a coordinate defined in entries was not found, the string is empty.
    def readCoordinatesFromFileStructure(self, baseDir, filenameInterpreter, entries=None):
        if entries is None:
            entries = []
        imageInfo = {}
        for dirpath, dirnames, filenames in os.walk(baseDir):
            imgFilenames = filter(lambda x: os.path.splitext(x)[-1].strip('.').lower() in imageSuffixes, filenames)
            for filename in imgFilenames:
                if filename in imageInfo:
                    raise ValueError('duplicate for %s ... filenames are not unique ... abort' % filename)

                try:
                    relDir = relpath(dirpath, baseDir)
                except:
                    raise ValueError('ERROR in readCoordinatesFromFileStructure: relative path between %s and %s' % (dirpath, baseDir))

                imageInfo[filename] = filenameInterpreter(filename)
                imageInfo[filename]['path'] = relDir

                for entry in entries:
                    if not imageInfo[filename].has_key(entry):
                        imageInfo[filename][entry] = ''

                imageInfo[filename]['exp_id'] = self.expDefinition['sep'].join([x + imageInfo[filename][x] for x in self.expDefinition['keys']])
        return imageInfo

    def __call__(self, baseDir, filenameInterpreter, filename, entries=None):
        imageInfo = self.readCoordinatesFromFileStructure(baseDir, filenameInterpreter, entries=entries)
        self.exportFlatFile(imageInfo, filename, entries=entries)

        return

    def exportFlatFile(self, imageInfo, outputFilename, entries=None):
        if entries is None:
            entries = imageInfo[imageInfo.keys()[0]].keys()

        file = open(outputFilename, 'w')
        tempStr = '\t'.join(['filename'] + entries)
        file.write(tempStr + '\n')
        filenames = sorted(imageInfo.keys())
        for filename in filenames:
            tempStr = '\t'.join([filename] + [imageInfo[filename][x] for x in entries])
            file.write(tempStr + '\n')
        file.close()
        return

    def getExpDict(self, imageInfo, dctKeys=None):
        if dctKeys is None:
            dctKeys = {
                        'well': 'P',
                        'field': 'F',
                        'timepoint': 'T',
                        'channel': 'C'
                        }
        imgContainer = {}
        for imageName in imageInfo.keys():
            exp_id = imageInfo[imageName]['exp_id']
            well = int(imageInfo[imageName][dctKeys['well']])
            field = int(imageInfo[imageName][dctKeys['field']])
            timepoint = int(imageInfo[imageName][dctKeys['timepoint']])
            channel = imageInfo[imageName][dctKeys['channel']]
            if not exp_id in imgContainer:
                imgContainer[exp_id] = {}
            if not timepoint in imgContainer[exp_id]:
                imgContainer[exp_id][timepoint] = {}
            if not channel in imgContainer[exp_id][timepoint]:
                imgContainer[exp_id][timepoint][channel] = \
                    {'filename': imageName, 'path': imageInfo[imageName]['path'],
                     'well': well, 'field': field}

        return imgContainer

    def invertDict(self, imageInfo, dctKeys=None):
        if dctKeys is None:
            dctKeys = {
                        'well': 'P',
                        'field': 'F',
                        'timepoint': 'T',
                        'channel': 'C'
                        }
        imgContainer = {}
        for imageName in imageInfo.keys():
            well = int(imageInfo[imageName][dctKeys['well']])
            field = int(imageInfo[imageName][dctKeys['field']])
            timepoint = int(imageInfo[imageName][dctKeys['timepoint']])
            channel = imageInfo[imageName][dctKeys['channel']]
            if not well in imgContainer:
                imgContainer[well] = {}
            if not field in imgContainer[well]:
                imgContainer[well][field] = {}
            if not timepoint in imgContainer[well][field]:
                imgContainer[well][field][timepoint] = {}
            if not channel in imgContainer[well][field][timepoint]:
                imgContainer[well][field][timepoint][channel] = \
                    {'filename': imageName, 'path': imageInfo[imageName]['path']}

        return imgContainer

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-f", "--filename",
                      help="output filename (flat file)" , dest="filename")
    parser.add_option("-i", "--inputdirectory",
                      help="input directory (image data base directory)", dest="baseDir")

    options, args = parser.parse_args()

    startTime = time.time()
    filenameInterpreter = RegexFilenameInterpreter(regexScheme)

    cg = CoordinatesGeneration()
    cg(options.baseDir, filenameInterpreter, options.filename, ENTRIES)

    diffTime = time.time() - startTime
    print 'Base Directory: %s' % options.baseDir
    print 'Flat File: %s' % options.filename
    print 'Elapsed time: %02i:%02i:%02i' % ((diffTime/3600), ((diffTime%3600)/60), diffTime%60)
    print 'DONE'



