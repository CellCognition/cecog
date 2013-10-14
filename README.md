                          The CellCognition Project
    Copyright (c) 2006 - 2012 Christoph Sommer, Michael Held & Daniel Gerlich
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

--------------------------------------------------------------------------------

### Building the C++ Extension


To compile the ccore extension you need to adopt the library/include
paths in the setup-scripts accordingly

Dependcies are:
- libvigraimpex
- libtiff
- liblzma (only if libtiff is statically linked)

On MaxOSX simply run the make file. On Windows it depends on the developement environment.

#### 1) VCXX Professional

run ```python setup_windows.py build_ext --inplace```
for a development build or 
```build_win64_bin.bat``` to build the installer.

#### 2) Using Windows SDK's:

Run additionally the script ```build_helper\windows_sdk_env.bat```. Anything else is the same.

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
  within the 10 frames).
- for Error correction you need to install the R-project (see below)


#### Package data


The package contains a sub-folder Data with

* Settings
  - demo_settings.conf, the settings file which is loaded on startup
  - graph_primary.txt, an example for a graph definition file (H2b)
  - graph_secondary.txt, an example for a graph definition file
    (Tubulin)
  - position_labels.txt, position labels such as OligoID or GeneSymbol

* Classifier
  - the class definition and sample annotations to pick samples with the
    larger data set, feature and SVM models to test (or train) the H2b
    and aTubulin classifiers

* Images
  - the input folder of the raw images

* Analysis
  - the output folder where results are written to

###### Note
With the included raw images picking of classifier samples is not possible since
not all necessary positions/timepoints are included.
Please download the larger H2b-Tubulin data.


#### Motif selection & error correction


With the included data and settings only six mitotic events with four frames
duration are selected.

To perform motif selection and error correction as presented in our paper more
timepoints are needed than the package contains. Larger data sets can be found
online at downloads.

You also might want to increase the length of the selected tracks, especially
after the pro-prometa onset. Increase therefore the values in
Tracking -> Timepoints [post] and Timepoints [pre].


#### R-project dependency

This part of cellcognition is legacy. A python replacement is already in 
testing phase
