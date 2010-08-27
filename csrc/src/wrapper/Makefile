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
# Makefile for MacOS 10.5/10.6 compatible intel-only 32bit cecog extension for
# for Python 2.6. For Windows build see the VisualStudio project files.
# Linking is performed static to reduce dependency issues.
#
# Todo: This build system will be replaced by setuptools in the close future.  


SRC_PATH     = $(HOME)/src
VIGRA_PATH   = $(SRC_PATH)/vigra1.6.0_micha
BOOST_PATH   = $(SRC_PATH)/boost_1_42_0
CECOG_PATH    = $(SRC_PATH)/cecog_svn/trunk
NUMPY_PATH   = /Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/numpy/core/include/
PYTHON_PATH  = /Library/Frameworks/Python.framework/Versions/2.6/include/python2.6
INSTALL_PATH = $(CECOG_PATH)/pysrc/cecog/ccore
LIB_VIGRA    = $(VIGRA_PATH)/src/impex/.libs/libvigraimpex.a
LIB_BOOST    = $(BOOST_PATH)/bin.v2/libs/python/build/darwin-4.2.1/release/address-model-32/architecture-x86/link-static/threading-multi/libboost_python.a
USR_PATH     = /sw

CXX = ccache g++ 

# Mac OS X - Intel Core (2) Duo optimization:

# NOTE: CXXFLAGS are optimized for compilation under Mac OS 10.6 (gcc 4.2) to run simuataneously 10.5 and 10.6
# NOTE: -march=nocona reduces runtime by >50% compared to default 
#       -march=core2 is supposed to give better results but reduced runtime only by ~25% (compared to default)           

CXXFLAGS = -fast -march=nocona -isysroot /Developer/SDKs/MacOSX10.5.sdk -mmacosx-version-min=10.5 -arch i386 -ansi -fno-operator-names -fPIC -DPIC

CXXINCLUDES = -I$(CECOG_PATH)/csrc/include -I$(VIGRA_PATH)/include -I$(BOOST_PATH) -I$(PYTHON_PATH) -I$(NUMPY_PATH) -I$(USR_PATH)/include
SONAME = so

LDSHARED = $(CXX) -bundle -flat_namespace -undefined warning -arch i386 -isysroot /Developer/SDKs/MacOSX10.5.sdk -mmacosx-version-min=10.5
#LDSHARED = $(CXX) -shared

LIB = -L/Users/miheld/src/pyvigra_svn/trunk/pysrc/pyvigra -lboost_python -lvigraimpex -ltiff.3 -ljpeg.8 -lpng12.0 -lfftw3.3 -lz.1 -lm
OBJ = #$(LIB_VIGRA) $(LIB_BOOST) $(USR_PATH)/lib/libtiff.a $(USR_PATH)/lib/libpng.a $(USR_PATH)/lib/libjpeg.a $(USR_PATH)/lib/libfftw3.a
    
TARGETS = \
	cecog
	
.SUFFIXES: .cxx

.SUFFIXES.o:
	$(CXX) $(CXXFLAGS) $(CXXINCLUDES) -c $*.cxx

all: $(TARGETS) 

cecog: cecog.o
	$(LDSHARED) -o _cecog.$(SONAME) cecog.o $(OBJ) $(LIB)

install:
	cp _cecog.$(SONAME) $(INSTALL_PATH)

clean:
	rm -f *.o *.d *.$(SONAME)

%.o: %.cxx
	$(CXX) $(CXXFLAGS) $(CXXINCLUDES) -c $*.cxx

#%.d: %.cxx
#        rm -f $*.d
#        $(CXX) -MD $(CXXFLAGS) $(CXXINCLUDES) -c $*.cxx

#ifneq "$(MAKECMDGOALS)" "clean"
#include $(patsubst %.o, %.d, $(OBJS))
#endif

