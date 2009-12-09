
                          The CellCognition Project
           Copyright (c) 2006 - 2009 Michael Held & Daniel Gerlich
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

--------------------------------------------------------------------------------

The CecogAnalyzer package comes with batteries included: it contains a small
set of raw images (5 timepoints of H2b-aTubulin) and two classifiers to test
the software without haze.

The package contains a sub-folder 'Data' with

 - Cecog_settings
   |- demo_settings.conf      - the settings file which is loaded on startup
   |- graph_primary.txt       - an example for a graph definition file (H2b)
   |- graph_secondary.txt     - an example for a graph definition file (Tubulin)
   |- position_labels.txt     - position labels such as OligoID or GeneSymbol

 - Classifier                 - the class definition and sample annotations to
   |- aTubulin                  pick samples with the larger data set, feature
   |- H2b                       and SVM models to test (or train) the classifier

 - Demo_data                  - the input folder of the raw images

 - Demo_output                - the output folder where results are written to


*** Motif selection & error correction ***

To perform motif selection and error correction more timepoints are needed than
the package contains. Larger data sets can be found online at
http://www.cellcognition.org


*** R-project dependency ***

Error correction requires the installation of the statistics project R.
See http://stat.ethz.ch/CRAN/

The R-packages 'hwriter', 'igraph' and 'Cairo' are needed as well.
These packages can be installed via the R's 'Package Installer' or by running
following commands from the R command line:

install.packages('hwriter')
install.packages('igraph')
install.packages('Cairo')

The R executable which needs to be specified is NOT the R-GUI and should be
found automatically for MacOSX and Windows. Otherwise try

MacOS:
/Library/Frameworks/R.framework/Versions/Current/Resources/bin/R32
or
/Library/Frameworks/R.framework/Versions/Current/Resources/bin/R

Windows:
C:\Program Files\R\bin\R.exe