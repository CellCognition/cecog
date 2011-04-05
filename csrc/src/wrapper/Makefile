#
#                           The CellCognition Project
#                     Copyright (c) 2006 - 2010 Michael Held
#                      Gerlich Lab, ETH Zurich, Switzerland
#                              www.cellcognition.org
#
#              CellCognition is distributed under the LGPL License.
#                        See trunk/LICENSE.txt for details.
#                 See trunk/AUTHORS.txt for author contributions.
#
#
# Author(s): Michael Held
# $Date: $
# $Rev: $
# $URL: $
#
# Makefile for MacOS 10.5/10.6 compatible intel-only 64bit cecog extension for
# for Python 2.7 (build on MacOS 10.6 with gcc 4.2.1) 
# For Windows build see the VisualStudio project files.
#
# Todo: Migration towards cmake

SRC_PATH     = $(HOME)/src
DEP_PATH     = $(HOME)/cecog_dependencies
CECOG_PATH    = $(SRC_PATH)/cecog_git
NUMPY_PATH   = /Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/numpy/core/include/
PYTHON_PATH  = /Library/Frameworks/Python.framework/Versions/2.7/include/python2.7
INSTALL_PATH = $(CECOG_PATH)/pysrc/cecog/ccore

MACOS_VERSION = 10.5
MACOS_SDK = /Developer/SDKs/MacOSX10.5.sdk

CXX = ccache g++ 

# Mac OS X - Intel Core (2) Duo optimization:
# NOTE: CXXFLAGS are optimized for compilation on Mac OS 10.6 (gcc 4.2.1) supporting MacOS 10.5 and 10.6
# NOTE: -march=nocona reduces runtime by >50% compared to default 
#       -march=core2 is supposed to give better results but reduced runtime only by ~25% (compared to default)           

CXXFLAGS = -isysroot $(MACOS_SDK) -mmacosx-version-min=$(MACOS_VERSION) -ansi -fno-operator-names -fPIC -DPIC -fast -march=nocona 

CXXINCLUDES = -I$(CECOG_PATH)/csrc/include -I$(DEP_PATH)/include -I$(PYTHON_PATH) -I$(NUMPY_PATH) 

LDFLAGS = -headerpad_max_install_names -bundle -undefined dynamic_lookup -isysroot $(MACOS_SDK) -mmacosx-version-min=$(MACOS_VERSION) 

LIBS = -L$(DEP_PATH)/lib -lboost_python -lvigraimpex -ltiff #-ljpeg -lpng -lfftw3 -lz -lm
OBJS = cecog.o #wrap_filters.o wrap_segmentation.o wrap_containers.o
    
TARGET = cecog
	
LIB_NAME = _$(TARGET).so

%.o: %.cxx
	$(CXX) $(CXXFLAGS) $(CXXINCLUDES) -c $*.cxx
	
all: $(TARGET) 

$(TARGET): $(OBJS)
	$(CXX) $(LDFLAGS) -o $(LIB_NAME) $(OBJS) $(LIBS)
	install_name_tool -change libboost_python.dylib $(DEP_PATH)/lib/libboost_python.dylib $(LIB_NAME) 
	install_name_tool -change libvigraimpex.3.dylib $(DEP_PATH)/lib/libvigraimpex.3.dylib $(LIB_NAME) 

install:
	cp $(LIB_NAME) $(INSTALL_PATH)

clean:
	rm -f *.o *.d *.so
