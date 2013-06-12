classifier_basedir = '/Users/twalter/data/Moritz Classifier'

plotDir = '/Users/twalter/data/LDA_study/LaminB'

makefolders = [plotDir]

classifier_names = {
                    'la_rnai_lb': os.path.join(classifier_basedir,
                                               '110719_H2B_LB1_RNAi_LB1',
                                               'data', 'features.arff'),
                    'lb_rnai_lb_stringent': os.path.join(classifier_basedir,
                                                         '110721_H2B_LB1_RNAi_LB1_stringent',
                                                         'data', 'features.arff'),
                    'la_mutant_la': os.path.join(classifier_basedir,
                                                 '110719_H2B_TRFX_LA',
                                                 'data', 'features.arff'),
                    'lb_mutant_h2b': os.path.join(classifier_basedir,
                                                  '110720_H2B_LB1_RNAi_H2B',
                                                  'data', 'features.arff'),
                    'la_mutant_h2b': os.path.join(classifier_basedir,
                                                  '110720_H2B_TRFX_H2B',
                                                  'data', 'features.arff'),
                    'lb_mutant_lb': os.path.join(classifier_basedir,
                                                 '110720_H2B_TRFX_LB1',
                                                 'data', 'features.arff'),
                    'la_mutant_la_stringent': os.path.join(classifier_basedir,
                                                           '110721_H2B_TRFX_LA_stringent',
                                                           'data', 'features.arff'),
                    }

FEATURES_REMOVE = [
                   'h4_2ASM', 'h4_2CON', 'h4_2COR', 'h4_2COV',
                   'h4_2DAV', 'h4_2ENT', 'h4_2IDM', 'h4_2PRO',
                   'h4_2SAV', 'h4_2SET', 'h4_2SHA', 'h4_2SVA',
                   'h4_2VAR', 'h4_2average', 'h4_2variance',
                   'h4_ASM', 'h4_CON', 'h4_COR', 'h4_COV',
                   'h4_DAV', 'h4_ENT', 'h4_IDM', 'h4_PRO',
                   'h4_SAV', 'h4_SET', 'h4_SHA', 'h4_SVA',
                   'h4_VAR', 'h4_average', 'h4_variance',
                   'h8_2ASM', 'h8_2CON', 'h8_2COR', 'h8_2COV',
                   'h8_2DAV', 'h8_2ENT', 'h8_2IDM', 'h8_2PRO',
                   'h8_2SAV', 'h8_2SET', 'h8_2SHA', 'h8_2SVA',
                   'h8_2VAR', 'h8_2average', 'h8_2variance',
                   'h8_ASM', 'h8_CON', 'h8_COR', 'h8_COV',
                   'h8_DAV', 'h8_ENT', 'h8_IDM', 'h8_PRO',
                   'h8_SAV', 'h8_SET', 'h8_SHA', 'h8_SVA',
                   'h8_VAR', 'h8_average', 'h8_variance'
                   ]

PHENOCLASSES_FOR_TRAINING = ['assembled', 'disassembled']
PHENOCLASSES = ['assembled', 'disassembling', 'disassembled']

colordict = {
             'disassembling': (0.4, 0.1, 0.5),
             'disassembled': (0.1, 0.1, 0.9),
             'deforming': (0.2, 0.7, 0.2),
             'assembled': (0.9, 0.1, 0.1),
             'defective': (0.2, 0.2, 0.2),
             }

# nomenclature:
# Date
# cell-line (e.g. H2B-LB1)
# Treatment (RNAi, TRFX)
# classified channel (H2B, LB1 or LA)
# stringent (non-stringent is default)
