# The CellCognition Project
 Copyright (c) 2006 - 2015 Gerlich Lab, IMBA Vienna, Austria  
 CellCognition is distributed under the terms of LGPL. 

 [www.cellcognition.org](www.cellcognition.org)  
 [doc.cellcognition.org](http://doc.cellcognition.org)

### Building the C++ Extension

To compile the ccore extension you need to adopt the library/include
paths in the setup.cfg accordingly.

Dependcies are:
- libvigraimpex
- libtiff

Remove the build- and dist directories and also the file
cecog/ccore/_cecog.so(pyd)

#### Development build
  python setup.py build_ext --inplace

#### System installation:
  python setup.py install --prefix=\<path-to-prefix\>

#### MacOSX
run the make file.

#### Using VCXX Professional
run build_win64_bin.bat

The CecogAnalyzer package comes with batteries included.

It contains

    - a small set of raw images (10 timepoints of H2b-aTubulin)
    - the two classifiers for H2b and aTubulin to test classification
    - a pre-configured settings file which is loaded on start-up.

You can

    - test Object Detection of the primary (H2b) and secondary (aTubulin)
      channels
    - retrain and test the classifier for H2b and aTubulin in Classification
    - test the tracking and select events in Tracking (only six tracks are found
      within the 10 frames)
    - for Error correction you need to install the R-project (see below)


#### Package data


The package contains a sub-folder Data with

    - Settings
        - demo_settings.conf, the settings file which is loaded on startup
        - graph_primary.xm., an example for a graph definition file (H2b)
        - graph_secondary.xml, an example for a graph definition file
          (Tubulin)

    - Classifier
        - *H2B* for the primary channel  
        - *aTubulin* for the secondary channel
        
        The classifiers contain trained and cross validated data suitable for demonstration purpose.
        Retraining (annoation of new cells, picking and cross validation) is only possible if one downloads 
        the [H2B-Tubulin data set](http://cellcognition.org/downloads/data).

    - Images
        - the input folder of the raw images

    - Analysis
        - the output folder where results are written to

#### Motif selection

With the included data and settings only six mitotic events with four frames
duration are selected.

To perform motif selection and error correction as presented in our paper more
timepoints are needed than the package contains. Larger data sets can be found
online at downloads.

You also might want to increase the length of the selected tracks, especially
after the pro-prometa onset. Increase therefore the values in
Tracking -> Timepoints [post] and Timepoints [pre].
