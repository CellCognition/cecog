
base_folder = '/Users/twalter/data/FIMM'
result_folder = os.path.join(base_folder, 'output')
plot_folder = os.path.join(base_folder, 'plots')
single_barplot_folder = os.path.join(plot_folder, 'single_experiments')
pheno_plot_folder = os.path.join(plot_folder, 'pheno_plate_plots')

mapping_folder = os.path.join(base_folder, 'meta_info')
mapping_info = {
                'MM1_HeLa_H2B_EGFP+10X_001': {'in_file': os.path.join(mapping_folder, 'SYSMIC_MM1_well_annotation.txt'),
                                              'out_file': os.path.join(mapping_folder, 'MM1_HeLa_H2B_EGFP+10X_001.txt')},
                
                }

make_folders = [
                plot_folder,
                single_barplot_folder,
                pheno_plot_folder,
                ]

