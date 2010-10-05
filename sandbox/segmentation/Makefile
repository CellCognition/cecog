
SRC_PATH     = $(HOME)/src
DEP_PATH     = $(HOME)/cecog_dependencies
CECOG_PATH    = $(SRC_PATH)/cecog_svn/trunk
#NUMPY_PATH   = /Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/numpy/core/include/
#PYTHON_PATH  = /Library/Frameworks/Python.framework/Versions/2.7/include/python2.7
#INSTALL_PATH = $(CECOG_PATH)/pysrc/cecog/ccore

MACOS_VERSION = 10.5
MACOS_SDK = /Developer/SDKs/MacOSX10.5.sdk

CXX = ccache g++ 

CXXFLAGS = -isysroot $(MACOS_SDK) -mmacosx-version-min=$(MACOS_VERSION) -ansi -fno-operator-names -fPIC -DPIC -fast -march=nocona 

CXXINCLUDES = -I$(CECOG_PATH)/csrc/include -I$(DEP_PATH)/include  

LDFLAGS = -isysroot $(MACOS_SDK) -mmacosx-version-min=$(MACOS_VERSION) 

LIBS = -L$(DEP_PATH)/lib -lvigraimpex #-ltiff -ljpeg -lpng -lfftw3 -lz -lm
OBJS = 


%.o: %.cxx
	$(CXX) $(CXXFLAGS) $(CXXINCLUDES) -c $*.cxx

segmentation_propagate: segmentation_propagate.o
	$(CXX) -o segmentation_propagate segmentation_propagate.o $(LIBS)
	install_name_tool -change libvigraimpex.3.dylib $(DEP_PATH)/lib/libvigraimpex.3.dylib segmentation_propagate 
	
clean::
	rm -f *.o *.d *.$(SONAME)

