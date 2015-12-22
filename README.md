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
  ```python setup.py build_ext --inplace```

#### System installation:
  ```python setup.py install --prefix=<path-to-prefix>```

#### MacOSX
Run the make file.

#### Using VCXX Professional
Run build_win64_bin.bat


### Demo data (battery package)

The demo data contains:

- A small set of raw images (10 timepoints of H2b-aTubulin).
- The two classifiers for H2b and aTubulin to test classification.
- A pre-configured settings file which is loaded on start-up.

Using the demo data it is possible to:

- Run segmentation on H2b (primary) and aTubulin (secondary) channels.
- Test the classifier for H2b and aTubulin channels.

#####Files:

- Settings
  - demo_settings.conf, the settings file which is loaded on startup
  - graph_primary.xml, an example for a graph definition file (H2b)
  - graph_secondary.xml, an example for a graph definition file (Tubulin)
- Classifiers
  - H2B  
  - aTubulin
- Images
  - first 10 timeframes from the [H2B-Tubulin data set](http://cellcognition.org/downloads/data).

####  H2B-Tubulin data set
The demo data included in the installer contains only a hand full of images i.e. 10 time frames. Please download the bigger [H2B-Tubulin](http://cellcognition.org/downloads/data) data set to perform:

- Classifier training and cross validation
- Event selection
- Error correction

It contains 206 frames with 4 min. timelapse. Use the same settings except for the parameter *Duration [post]*. It is recommended to increase it to 35 frames.

