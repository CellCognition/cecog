import os, sys, re, time

#import scripts.IC.io.importer as imp

import scripts.IC.io.importer

from scripts.IC.settings import Settings

import cellh5

import numpy as np

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

import operator as op

class ScreenVisualization(object):
    
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())

        for folder in self.settings.make_folders:
            if not os.path.exists(folder):
                print 'make folder %s' % folder
                os.makedirs(folder)
        return    
                
        #self.fh = cellh5.CH5File(data_filename)
        #self.well_str = '0'
        #self.pos_str = self.fh.positions[self.well_str][0]
        #self.pos = self.fh.get_position(self.well_str, self.pos_str)

    def plot_ph3_distribution(self):
        channel = 'secondary__expanded'
        #region = 'expanded'
        feature = 'n2_avg'
        plate = 'MM1_HeLa_H2B_EGFP+10X_001'
        mapping_filename = 'MM1_HeLa_H2B_EGFP+10X_001.txt'
        
        
    def get_class_feature_distribution(self, channel, feature, plate, 
                                        mapping_filename, class_name):

        
        plate_folder = os.path.join(self.settings.result_folder, plate)
        ch5_folder = os.path.join(plate_folder, 'hdf5')
        if not os.path.isdir(ch5_folder):
            print 'problem with folder settings: hdf5-folder for plate %s not found' % plate
                
        cm = cellh5.CH5MappedFile(os.path.join(ch5_folder, '_all_positions.ch5'))
        if not mapping_filename is None:
            cm.read_mapping(mapping_filename)
        
        classes = cm.class_definition('primary__primary')
        class_colors = [x[-1] for x in classes]
        class_names = [x[1] for x in classes]
        class_labels = [x[0] for x in classes]
                
        feat_index = cm.feature_definition[channel]['object_features'].index(feature)                
        
        for w, p, pos in cm.iter_items():
            pos
        return
    
    def plot_class_feature_distribution(self, channel, region, feature, plate, 
                                        mapping_filename):

        plate_folder = os.path.join(self.settings.result_folder, plate)
        ch5_folder = os.path.join(plate_folder, 'hdf5')
        if not os.path.isdir(ch5_folder):
            print 'problem with folder settings: hdf5-folder for plate %s not found' % plate
                
        cm = cellh5.CH5MappedFile(os.path.join(ch5_folder, '_all_positions.ch5'))
        if not mapping_filename is None:
            cm.read_mapping(mapping_filename)

        classes = cm.class_definition('primary__primary')
        class_colors = [x[-1] for x in classes]
        class_names = [x[1] for x in classes]
        class_labels = [x[0] for x in classes]
                
        sirnas = dict(zip(cm.mapping['Position'], cm.mapping['siRNA ID']))
        genes = dict(zip(cm.mapping['Position'], cm.mapping['Gene Symbol']))        
        groups = dict(zip(cm.mapping['Position'], cm.mapping['Group']))
                
        return
        
    def convert_mapping_files(self):
        mapf = scripts.IC.io.importer.MappingFile()
        
        for plate in self.settings.mapping_info:
            in_file = self.settings.mapping_info[plate]['in_file']
            out_file = self.settings.mapping_info[plate]['out_file']
            res_dir = os.path.join(self.settings.result_folder, plate, 'hdf5')
            mapf.convert(in_file, out_file, result_dir=res_dir)
            
        return
    
    def __call__(self):
        plates = [('MM1_HeLa_H2B_EGFP+10X_001', 'MM1_HeLa_H2B_EGFP+10X_001_meta.txt')]
        for pl, mapping_file in plates:
            print pl, mapping_file
            mapping_filename = os.path.join(self.settings.mapping_folder, mapping_file)
            #self.make_individual_barplots(pl, mapping_filename)
            colors = self.get_colors(pl, mapping_filename)
            counts = self.get_counts(pl, mapping_filename)
            for pheno in ['total'] + sorted(colors.keys()):
                self.make_pheno_plots(counts, pheno, pl, colors, ylim=(0.0, 0.4))
        return
     
    def make_pheno_plots(self, res, pheno, plate, colors, ylim=None,
                         genes=None):

        if not colors is None and pheno in colors:
            color = colors[pheno]
        else:
            color = '#80D090'
            
        plot_folder = self.settings.pheno_plot_folder
        
        bottom = 0.2
        width = 0.7
        ylim = None
        
        title = 'Score distributions for Plate %s Pheno %s' % (plate, pheno)
        xlab = ''
        ylab = 'Phenotypic score'
        grid = True
        filename = os.path.join(plot_folder, '%s--%s.png' % (plate, pheno))

        nb_bars = len(res)
        ind = np.array(range(nb_bars))

        fig = plt.figure(1, figsize=(int(0.8*nb_bars + 1),10))
        ax = plt.subplot(1,1,1)
        ax.set_position(np.array([0.125, bottom, 0.8, 0.9 - bottom]))
    
        wells = sorted(res.keys())
        barnames = ['%s %s %s' % (x, res[x]['sirna'], res[x]['gene']) 
                    for x in wells]
        scores = [res[x][pheno] for x in wells]
                                
        temp = zip(barnames, scores)
        temp.sort(key=op.itemgetter(-1), reverse=True)
        datavec = [x[-1] for x in temp]
        barnames = [x[0] for x in temp]
        
        rects = plt.bar(ind, datavec, width=width, color=color,
                        edgecolor='none')

        # set xlim
        xmin = min(ind)
        xmax = max(ind)
        xlim = (xmin - (xmax-xmin) * 0.05,
                xmax + (xmax-xmin) * (0.05 + 1.0 / nb_bars) )

        if ylim is None:
            ymin = 0 #min(datavec)
            #ymax = 1.0
            ymax = max(datavec)
            ylim = (ymin, ymax + (ymax - ymin) * 0.05)

        axis = (xlim[0], xlim[1], ylim[0], ylim[1])
        plt.axis(axis)

        plt.xticks(ind+.5*width, barnames, rotation="vertical",
                   fontsize='small', ha='center')
        plt.title(title, size='small')            
        plt.ylabel(ylab, size='small')

        if grid:
            plt.grid(b=True, axis='y', which='major', linewidth=1.5)
    
        # write and close
        plt.savefig(filename)
        plt.close(1)

        
        return

    def get_colors(self, plate, mapping_filename=None):
        plate_folder = os.path.join(self.settings.result_folder, plate)
        ch5_folder = os.path.join(plate_folder, 'hdf5')
        if not os.path.isdir(ch5_folder):
            print 'problem with folder settings: hdf5-folder for plate %s not found' % plate
                
        cm = cellh5.CH5MappedFile(os.path.join(ch5_folder, '_all_positions.ch5'))
        if not mapping_filename is None:
            cm.read_mapping(mapping_filename)

        classes = cm.class_definition('primary__primary')
        class_colors = [x[-1] for x in classes]
        class_names = [x[1] for x in classes]
        class_labels = [x[0] for x in classes]

        color_dict = dict(zip(class_names, class_colors))
        return color_dict
    
        
    def get_counts(self, plate, mapping_filename=None):
        plate_folder = os.path.join(self.settings.result_folder, plate)
        ch5_folder = os.path.join(plate_folder, 'hdf5')
        if not os.path.isdir(ch5_folder):
            print 'problem with folder settings: hdf5-folder for plate %s not found' % plate
                
        cm = cellh5.CH5MappedFile(os.path.join(ch5_folder, '_all_positions.ch5'))
        if not mapping_filename is None:
            cm.read_mapping(mapping_filename)

        classes = cm.class_definition('primary__primary')
        class_colors = [x[-1] for x in classes]
        class_names = [x[1] for x in classes]
        class_labels = [x[0] for x in classes]
                
        sirnas = dict(zip(cm.mapping['Position'], cm.mapping['siRNA ID']))
        genes = dict(zip(cm.mapping['Position'], cm.mapping['Gene Symbol']))        
        groups = dict(zip(cm.mapping['Position'], cm.mapping['Group']))
        
        # loop over wells
        res = {}
        for well, poslist in cm.positions.iteritems():            

            print well, poslist
            # -----------------------------------------------------------------
            # get data                        
            #import pdb; pdb.set_trace()
            valid_positions = filter(lambda x: len(cm.get_position(well, x)['object']['primary__primary']) > 0,
                                     poslist)
            pos = np.concatenate([
                                  np.array([class_labels[x[0]] for x in 
                                            cm.get_position(well, pos).get_class_prediction('primary__primary')]) 
                                  for pos in valid_positions])

            #import pdb; pdb.set_trace()            
            total = len(pos)
            abs_count = {}
            rel_count = {}

            res[well] = {
                         'total': total,
                         'sirna': sirnas[int(well)],
                         'gene': genes[int(well)],
                         }

            for label, class_name, color in classes:
                abs_count[class_name] = sum(pos==label)
                if total == 0:
                    rel_count[class_name] = 0.0
                    res[well][class_name] = 0.0
                else:
                    rel_count[class_name] = float(abs_count[class_name])/total
                    res[well][class_name] = float(abs_count[class_name])/total
                    
        cm.close()
        return res
    
    def make_individual_barplots(self, plate, mapping_filename=None):
        plate_folder = os.path.join(self.settings.result_folder, plate)
        ch5_folder = os.path.join(plate_folder, 'hdf5')
        if not os.path.isdir(ch5_folder):
            print 'problem with folder settings: hdf5-folder for plate %s not found' % plate
                
        cm = cellh5.CH5MappedFile(os.path.join(ch5_folder, '_all_positions.ch5'))
        if not mapping_filename is None:
            cm.read_mapping(mapping_filename)

        classes = cm.class_definition('primary__primary')
        class_colors = [x[-1] for x in classes]
        class_names = [x[1] for x in classes]
        class_labels = [x[0] for x in classes]
                
        sirnas = dict(zip(cm.mapping['Position'], cm.mapping['siRNA ID']))
        genes = dict(zip(cm.mapping['Position'], cm.mapping['Gene Symbol']))        
        groups = dict(zip(cm.mapping['Position'], cm.mapping['Group']))
        
        # loop over wells
        for well, poslist in cm.positions.iteritems():            

            print well, poslist
            # -----------------------------------------------------------------
            # get data                        
            #import pdb; pdb.set_trace()
            valid_positions = filter(lambda x: len(cm.get_position(well, x)['object']['primary__primary']) > 0,
                                     poslist)
            pos = np.concatenate([
                                  np.array([class_labels[x[0]] for x in 
                                            cm.get_position(well, pos).get_class_prediction('primary__primary')]) 
                                  for pos in valid_positions])

            #import pdb; pdb.set_trace()            
            total = len(pos)
            abs_count = {}
            rel_count = {}
            for label, class_name, color in classes:
                abs_count[class_name] = sum(pos==label)
                if total == 0:
                    rel_count[class_name] = 0.0
                else:
                    rel_count[class_name] = float(abs_count[class_name])/total
            #import pdb; pdb.set_trace()
            
            
            # -----------------------------------------------------------------
            # plot            
            # new figure
            bottom = 0.2
            width = 0.7
            ylim = None
            title = 'Position %s siRNA %s gene %s\ntotal cell number: %i' % (well, sirnas[int(well)], genes[int(well)], total)
            xlab = ''
            ylab = 'relative cell counts'
            grid = True
            filename = os.path.join(self.settings.single_barplot_folder, '%s--%s--%s.png' % (well, sirnas[int(well)], genes[int(well)]))

            fig = plt.figure(1)
            ax = plt.subplot(1,1,1)
            ax.set_position(np.array([0.125, bottom, 0.8, 0.9 - bottom]))

            nb_bars = len(classes)
            ind = np.array(range(nb_bars))
    
            datavec = [rel_count[x] for x in class_names]
            rects = plt.bar(ind, datavec, width=width, color=class_colors,
                            edgecolor='none')

            # set xlim
            xmin = min(ind)
            xmax = max(ind)
            xlim = (xmin - (xmax-xmin) * 0.05,
                    xmax + (xmax-xmin) * (0.05 + 1.0 / nb_bars) )
    
            if ylim is None:
                ymin = 0 #min(datavec)
                ymax = 1.0
                ylim = (ymin, ymax + (ymax - ymin) * 0.05)
    
            axis = (xlim[0], xlim[1], ylim[0], ylim[1])
            plt.axis(axis)
    
            plt.xticks(ind+.5*width, class_names, rotation="vertical",
                       fontsize='small', ha='center')
            plt.title(title, size='small')            
            plt.ylabel(ylab, size='small')

            if grid:
                plt.grid(b=True, axis='y', which='major', linewidth=1.5)
        
            # write and close
            plt.savefig(filename)
            plt.close(1)
        
        cm.close()
        return

    

