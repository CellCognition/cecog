import os, sys, re, time

import h5py
import numpy as np
import cellh5

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

class MappingFile(object):
    def __init__(self, nb_of_fields=None):
        self.title_line = ['Position',    
                           'Well',
                           'Site' ,   
                           'Row',    
                           'Column',    
                           'Gene Symbol',    
                           'siRNA ID',    
                           'Group'
                           ]
        self.nb_of_fields = nb_of_fields
        
    def read_FIMM_Mapping(self, raw_mapping_file, nb_of_fields=None, result_dir=None):
        cm = None
        if nb_of_fields is None:
            if self.nb_of_fields is None:
                if result_dir is None:
                    print 'number of fields unknown ... I suppose there is 1.'
                    nb_of_fields = 1
                else:
                    #found_files = filter(lambda x: x[0] != '_' and x.split('.')[-1] == 'ch5', os.listdir(result_dir)
                    #                     for file in found_files:
                    cm = cellh5.CH5MappedFile(os.path.join(result_dir, '_all_positions.ch5'))                                        
            else:
                nb_of_fields = self.nb_of_fields

#        fimm_title = '\t'.join(['SAMPLE_IDENTIFIER',    
#                                'Well number (by ScanR)',    
#                                'WELL (by rows)'])                                    
        synonyms = {
                    'SAMPLE_IDENTIFIER' : 'oligo', 
                    'Well number (by ScanR)': 'pos',
                    'WELL (by rows)': 'well',
                    }
        empty_synonyms = ['cells', 'empty']
        neg_synonyms = ['NEG_1']
        pos_synonyms = ['DEATH']
        
        #mapping = np.recfromcsv(raw_mapping_file, delimiter='\t')
        fp = open(raw_mapping_file, 'r')
        temp = fp.readlines()
        fp.close()
        fimm_title = temp[0]        
        fields = filter(lambda x: len(x) > 0, [y.strip('\n').strip('\r') for y in fimm_title.split('\t')])

        res = []
        for line in temp[1:]:
            entries = filter(lambda x: len(x) > 0, [y.strip('\n').strip('\r') for y in line.split('\t')])
            info = dict(zip([synonyms[x] for x in fields], entries))
            pos = int(info['pos'][1:])
            well = info['well']
            row = well[0]
            col = int(well[1:])            
            
            if info['oligo'] in empty_synonyms:
                oligo = 'empty'
                gene = 'empty'
            else:
                exp_info = info['oligo'].split('_')                
                if len(exp_info) == 1:
                    oligo = 'unknown'
                    gene = info['oligo']
                elif len(exp_info) == 2:
                    oligo = exp_info[1]
                    gene = exp_info[0]
                else:
                    oligo = '_'.join(exp_info[1:])
                    gene = exp_info[0]
            if oligo in neg_synonyms:
                group = 'negative control'
            elif oligo in pos_synonyms:
                group = 'positive control'
            elif oligo == 'empty':
                group = 'empty'
            else: 
                group = 'experiment'
                           
            #site = 1 # will be adapted to the plate
            if nb_of_fields is None:
                pos_str = '%05i' % pos
                if not pos_str in cm.positions:
                    print '%s not found' % pos
                    continue
                for site in cm.positions[pos_str]:
                    res.append({
                                'Position': pos,
                                'Well': well,
                                'Row': row,
                                'Column': col, 
                                'Site': int(site),
                                'siRNA ID': oligo,
                                'Gene Symbol': gene,
                                'Group': group,
                                })                    
            else:                
                for site in range(1,(nb_of_fields+1)):
                    res.append({
                                'Position': pos,
                                'Well': well,
                                'Row': row,
                                'Column': col, 
                                'Site': site,
                                'siRNA ID': oligo,
                                'Gene Symbol': gene,
                                'Group': group,
                                })
        
        if not cm is None:    
            cm.close()
        return res
    
    def convert(self, input_name, output_name, result_dir=None):
        res = self.read_FIMM_Mapping(input_name, result_dir=result_dir)
        
        fp = open(output_name, 'w')
        fp.write('\t'.join(self.title_line) + '\n')
        for entry in res:            
            fp.write('\t'.join([str(entry[x]) for x in self.title_line]) + '\n')
        fp.close()
        return

# DEPRECATED
class CountImporter(object):
    GROUP_BY = enum('POS', "OLIGO", "GENE", "GROUP")
    
    def __init__(self, input_dir, mapping_file):
        self.input_dir = input_dir
        self.mapping_file = mapping_file
        
        self.fp = None
        self.class_definitions  = {}
        self.plate = None
        
    def get_classes(self):
        if self.fp is None:
            print 'no hdf5 file open ... skipped class definitions'

        # f['definition']['feature']['primary__primary']['object_classification']['class_labels'][0:8]
        # f['definition']['feature']['primary__primary']['object_classification']['class_labels'][2]
            
        self.class_definitions = {}
        regions_with_classification = filter(lambda x: 'object_classification' in self.fp['definition']['feature'][x], 
                                             self.fp['definition']['feature'].keys())
        for region in regions_with_classification:
            self.class_definitions[region] = self.fp['definition']['feature'][region]['object_classification']['class_labels'][:].tolist()

        return
                
    def open_plate_hdf5(self, plate):
        #/Users/twalter/data/FIMM/output/MM1_HeLa_H2B_EGFP+10X_001/hdf5/_all_positions.ch5
        filename = os.path.join(self.input_dir, plate, 'hdf5', '_all_positions.ch5')
        if not self.fp is None: 
            self.fp.close()
                        
        self.fp = h5py.File(filename, 'r')        
        self.get_classes()
        self.plate = plate
        return
            
    def close_plate_hdf5(self):
        if not self.fp is None:
            self.fp.close()
            self.fp = None
        self.class_definitions = {}
        self.plate = None
        return

    def _import_count_sums(self, exp_list, region_name):    
        class_count = {}
        
        for well, pos in exp_list:
            class_count = self._import_counts_atom(well, pos, region_name, class_count)

        return class_count

    def _readMappingFile(self):
        if os.path.exists(self.mapping_file):
            mapping = numpy.recfromcsv(self.mapping_file, delimiter='\t', comments='###')
        else:
            raise RuntimeError("Mapping file does not exist %s" % self.mapping_file)

        if len(mapping.shape) == 0:
            # stupid numpy bug, when the tsv file contains one single entry
            mapping.shape = (1,)

        if mapping.shape[0] == 0:
            raise RuntimeError("Mapping file is empty %s" % self.mapping_file)

        self._logger.info('Found mapping file: %s' % self.mapping_file)

        return mapping

    def get_grouping(self):
        res = {}
        for pos in self._positions.values():
            if self.group_by == self.GROUP_BY.POS:
                group_key = pos.position
            elif self.group_by == self.GROUP_BY.OLIGO:
                group_key = pos.oligoid
            elif self.group_by == self.GROUP_BY.GENE:
                group_key = pos.gene_symbol
            elif self.group_by == self.GROUP_BY.GROUP:
                group_key = pos.group
            else:
                raise AttributeError("group_by argument not understood %r" % self.group_by)

            if pos.position not in res:
                res[group_key] = []
            res[group_key].append(pos)
        return res
    
    # this imports the class counts from one experiment. 
    def _import_counts_atom(self, well_name, position, region_name, class_count=None):
        #f['sample']['0']['plate']['LT0073_07']['experiment']['00184']['position']['1']['object']['primary__primary']
        objects = self.fp['sample']['0']['plate'][self.plate]['experiment'][well_name]['position'][position]['object'][region_name]
        classification_res = self.fp['sample']['0']['plate'][self.plate]['experiment'][well_name]['position'][position]['feature'][region_name]['object_classification']['prediction']
        max_time = objects[-1][0]
        class_labels = [x[0] for x in self.class_definitions]
        if class_count is None or len(class_count) == 0:
            class_count = dict(class_labels, 
                               dict(range(max_time), [0 for t in range(max_time)]))
        for i, obj_id in enumerate(objects):
            class_label = classification_res[i][0]
            lb, timepoint = obj_id
            class_count[class_label][timepoint] += 1
        
        return class_count
     
 