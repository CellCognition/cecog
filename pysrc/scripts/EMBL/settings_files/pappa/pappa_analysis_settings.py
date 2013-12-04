_output_folder = '/Users/twalter/data/PAPPA/output2'
_plotDir = '/Users/twalter/data/PAPPA/plots2'
_lstPlates = ['plate1']

output_folder = '/Users/twalter/data/PAPPA/output4'
plotDir = '/Users/twalter/data/PAPPA/plots'

annotation_filename = '/Users/twalter/data/PAPPA/annotations/results_single_images.txt'

lstPlates = [
#             'ASlide1_20msoffset_001',
#             'ASlide2_20msoffset_001',
#             'ASlide3_20msoffset_001',
#             'BSlide1_20msoffset_002',
#             'BSlide2_20msoffset_002',
#             'BSlide3_20msoffset_002',
#             'CSlide1_20msoffset_003',
#             'CSlide2_20msoffset_003',
#             'CSlide3_20msoffset_003',
#             'DSlide1_20msoffset_004',
#             'DSlide2_20msoffset_004',
#             'DSlide3_20msoffset_004',
#             'plate1',
             'Exp10',
             'Exp11',
             'Exp12',
             ]

class_code = {
              1:    'Interphase',    #00ff00
              2:    'EarlyMitosis',    #ff8000
              3:    'Metaphase',    #ff00ff
              4:    'Anaphase',    #00ffff
              5:    'Polylobed',    #0000ff
              6:    'Apoptosis',   #ff0000
              7:    'SegArt',    #646822
              8:    'JoinArt',    #591b41
              #9:    'Debris',    #996633
              }

colors = {
          'Interphase'  :       '#00ff00',
          'EarlyMitosis':       '#ff8000',
          'Metaphase'   :       '#ff00ff',
          'Anaphase'    :       '#00ffff',
          'Polylobed'   :       '#0000ff',
          'Apoptosis'   :       '#ff0000',
          'SegArt'      :       '#646822',
          'JoinArt'     :       '#591b41',
          # here I am
          'mito'        :       '#1050a0',
          #'Debris'      :       '#996633',
          }

sec_class_code = {
                  1:    'EarlyMitosis',    #ff8000
                  2:    'Metaphase',    #ff00ff
                  3:    'NoMitosis',    #0000ff
                  4:    'Anaphase',    #00ffff
                  5:    'MitosisSegError',    #008000
                  }

sec_colors = {
              'EarlyMitosis'    :   '#ff8000',
              'Metaphase'       :   '#ff00ff',
              'NoMitosis'       :   '#0000ff',
              'Anaphase'        :   '#00ffff',
              'MitosisSegError' :   '#008000',

              }

condition_colors = {
                    'untreated': (0.1, 0.3, 0.8),
                    'control': (0.1, 0.3, 0.8),
                    'siRNA 42 knock down': (0.5, 0.0, 0.2),
                    'siRNA 42 rescue': (0.7, 0.1, 0.3),
                    'siRNA 28 knock down': (0.0, 0.5, 0.2),
                    'siRNA 28 rescue': (0.1, 0.7, 0.3),
                    }
#class_code = {
#              1: 'inter',
#              2: 'pro',
#              3: 'prometa',
#              4: 'meta',
#              5: 'earlyana',
#              6: 'lateana',
#              7: 'telo',
#              8: 'apo',
#              9: 'dis',
#              10:'map'
#              }

sumClasses = {
              'primary': {
                          'mito' : ['EarlyMitosis', 'Metaphase', 'Anaphase'],
                          'before_division' : ['EarlyMitosis', 'Metaphase'],
                          },
              'secondary': {
                            'mito' : ['EarlyMitosis', 'Metaphase', 'Anaphase', 'MitosisSegError'],
                            'before_division' : ['EarlyMitosis'],
                            },
              }

pheno_classes = class_code.values()
mitotic_classes = ['EarlyMitosis', 'Metaphase', 'Anaphase']

sec_pheno_classes = sec_class_code.values()
sec_mitotic_classes = ['EarlyMitosis', 'Metaphase', 'Anaphase', 'MitosisSegError']


#colors =  {
#           'inter':     '#00ff00',
#           'pro':       '#ffff00',
#           'prometa':   '#ff8000',
#           'meta':      '#ff00ff',
#           'earlyana':  '#800080',
#           'lateana':   '#0000ff',
#           'telo':      '#00ffff',
#           'apo':       '#ff0000',
#           'dis':       '#5b783c',
#           'map':       '#fface4',
#
#           'pre_align': '#50f020',
#           'early_mitosis': '#22ffa0',
#           'mitosis': '#22a0ff',
#           'proliferation': '#5555ff',
#
#           'mito_phospho_histo': '#006020',
#           'mito_classification': '#22a0ff',
#           'early_mito_classification': '#22ffa0',
#           }
