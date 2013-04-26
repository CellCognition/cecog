
                          The CellCognition Project
    Copyright (c) 2006 - 2012 Christoph Sommer, Michael Held & Daniel Gerlich
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

--------------------------------------------------------------------------------

The CecogAnalyzer package comes with batteries included.

It contains

    * a small set of raw images (10 timepoints of H2b-aTubulin)
    * the two classifiers for H2b and aTubulin to test classification
    * a pre-configured settings file which is loaded on start-up.

You can

    * test Object Detection of the primary (H2b) and secondary (aTubulin)
      channels
    * retrain and test the classifier for H2b and aTubulin in Classification
    * test the tracking and select events in Tracking (only six tracks are found
      within the 10 frames)
    * for Error correction you need to install the R-project (see below)


Package data
************

The package contains a sub-folder Data with

    * Settings
          o demo_settings.conf, the settings file which is loaded on startup
          o graph_primary.txt, an example for a graph definition file (H2b)
          o graph_secondary.txt, an example for a graph definition file
            (Tubulin)
          o position_labels.txt, position labels such as OligoID or GeneSymbol

    * Classifier
          o the class definition and sample annotations to pick samples with the
            larger data set, feature and SVM models to test (or train) the H2b
            and aTubulin classifiers

    * Images
          o the input folder of the raw images

    * Analysis
          o the output folder where results are written to

Note
With the included raw images picking of classifier samples is not possible since
not all necessary positions/timepoints are included.
Please download the larger H2b-Tubulin data.


Motif selection & error correction
**********************************

With the included data and settings only six mitotic events with four frames
duration are selected.

To perform motif selection and error correction as presented in our paper more
timepoints are needed than the package contains. Larger data sets can be found
online at downloads.

You also might want to increase the length of the selected tracks, especially
after the pro-prometa onset. Increase therefore the values in
Tracking -> Timepoints [post] and Timepoints [pre].


R-project dependency
********************

Error correction requires the installation of the statistics project R.
See http://r-project.org

The R-packages hwriter, igraph and Cairo are needed as well. These packages can
be installed via the R's Package Installer or by running following commands from
the R command line:

install.packages('hwriter')
install.packages('igraph')
install.packages('Cairo')

The R executable which needs to be specified is NOT the R-GUI and should be
found automatically for MacOSX and Windows. Otherwise try

MacOSX

/Library/Frameworks/R.framework/Versions/Current/Resources/bin/R32

or

/Library/Frameworks/R.framework/Versions/Current/Resources/bin/R

Windows

C:\Program Files\R\R-2.10.0\bin\R.exe
