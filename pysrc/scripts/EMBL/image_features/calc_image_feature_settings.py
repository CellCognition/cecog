

regexScheme = {
               "strRegexWell"       : "W(?P<W>\d+)",
               "strRegexPosition"   : "--P(?P<P>\d+)",
               "strRegexTime"       : "--T(?P<T>\d+)",
               "strRegexChannel"    : "--(?P<C>\w+-?\w+)\.",
               "strRegexZSlice"     : "--Z(?P<Z>\d+)",
               }

EXP_DEFINITION = {
                  'keys': ('W', 'P'),
                  'sep': '_'
                  }


dctKeys = {
           'well': 'W',
           'field': 'P',
           'timepoint': 'T',
           'channel': 'C'
           }

baseDir = '/Volumes/ellenberg/ToThomasfromAndrea'
#baseDir = '/Users/twalter/data/Andrea/data/20X'

lstIndir = [
            '/Volumes/ellenberg/ToThomasfromAndrea/110322 NS3-CMPK 20X Cube5',
            #'/Users/twalter/data/Andrea/data/20X/110322 20X Cube5 Hela H2b NS3',
            #'/Users/twalter/data/Andrea/data/20X/110406 883 NS3-mcherry Cube5 Hela 883 NS3 mCherry 20x WO2_001',
            #'/Users/twalter/data/Andrea/data/20X/110406 883 NS3-mcherry Cube5 Hela 883 NS3 mCherry 20x_001',
            #'/Users/twalter/data/Andrea/data/20X/110407 449 Ns3-mCherry Cube5 Hela 449 NS3Cherry 1ug WO1  GFPexp200 Cy3Exp400 20X'
            ]

primaryChannelDict = {
                      '110322 NS3-CMPK 20X Cube5': 'Cy3',
                      '110322 20X Cube5 Hela H2b NS3': 'Cy3',
                      '110406 883 NS3-mcherry Cube5 Hela 883 NS3 mCherry 20x WO2_001': 'DAPI',
                      '110406 883 NS3-mcherry Cube5 Hela 883 NS3 mCherry 20x_001': 'DAPI',
                      '110407 449 Ns3-mCherry Cube5 Hela 449 NS3Cherry 1ug WO1  GFPexp200 Cy3Exp400 20X': 'DAPI',
                      }

output_dir = '/Users/twalter/data/ttt'

# intermediate images (mainly for debuging)
write_images = True
output_images_dir = os.path.join(output_dir, 'out_images')

# pickle files (output)
pickle_result_dir = os.path.join(output_dir, 'results')
