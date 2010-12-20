#SRC_PATH     = $(HOME)/src
#VIGRA_PATH   = /usr/local/src/vigra1.4.0
#BOOST_PATH   = /usr/local/src/boost
#MITO_PATH    = $(HOME)/workspace/mito_svn/trunk
#INSTALL_PATH = $(MITO_PATH)/mito/ccore
#PYTHON_PATH  = /usr/local/include/python2.5
#LIB_PATH     = /usr/local/lib

SRC_PATH     = $(HOME)/src
VIGRA_PATH   = $(SRC_PATH)/vigra1.6.0_micha
BOOST_PATH   = $(SRC_PATH)/boost
MITO_PATH    = $(SRC_PATH)/cecog_trunk/csrc
#NUMPY_PATH   = /Library/Python/2.5/site-packages/numpy-1.3.0-py2.5-macosx-10.5-i386.egg/numpy/core/include/
#PYTHON_PATH  = /System/Library/Frameworks/Python.framework/Versions/2.5/include/python2.5
#NUMPY_PATH   = /Library/Frameworks/Python.framework/Versions/2.5/lib/python2.5/site-packages/numpy-1.3.0-py2.5-macosx-10.3-i386.egg/numpy/core/include/
PYTHON_PATH  = $(HOME)/include/python2.7
NUMPY_PATH   = $(HOME)/lib/python2.7/site-packages/numpy-1.5.0-py2.7-linux-x86_64.egg/numpy/core/include/ 
INSTALL_PATH_CECOG = $(SRC_PATH)/cecog_trunk/pysrc/cecog/ccore
LIB_PATH     = $(INSTALL_PATH)/lib
LIB_PATH2    = $(VIGRA_PATH)/src/impex/.libs
LIB_PATH3    = $(BOOST_PATH)/bin.v2/libs/python/build/darwin-4.0.1/release/link-static/threading-multi/
SW_PATH      = $(HOME)

CXX = g++ 

# Mac OS X - Intel Core (2) Duo optimization:

# NOTE: CXXFLAGS are optimized for compilation under Mac OS 10.6 (gcc 4.2) to run simuataneously 10.5 and 10.6
# NOTE: -march=nocona reduces runtime by >50% compared to default 
#       -march=core2 is supposed to give better results but reduced runtime only by ~25% (compared to default)           

CXXFLAGS = -O3 -march=nocona -ansi -fno-operator-names -fPIC -DPIC
#CXXFLAGS = -fast -march=nocona -mmacosx-version-min=10.4 -ansi -fPIC -DPIC
#CXXFLAGS =  -fast -mtune=pentium4m -fPIC -DPIC
#CXXFLAGS = -O2 -g3 -gdwarf-2 -ansi -fPIC -DPIC   
#CXXFLAGS = -fPIC -DPIC

CXXINCLUDES = -I$(MITO_PATH)/include -I$(SW_PATH)/include -I$(PYTHON_PATH) -I$(NUMPY_PATH)
#CXXINCLUDES = -I$(MITO_PATH)/include -I$(VIGRA_PATH)/include -I$(BOOST_PATH) -I$(PYTHON_PATH)
SONAME = so

#LDSHARED = $(CXX) -bundle -flat_namespace -undefined warning -arch i386 -isysroot /Developer/SDKs/MacOSX10.5.sdk -mmacosx-version-min=10.5
LDSHARED = $(CXX) -shared

LIB = -lz -lm
#OBJ = $(LIB_PATH2)/libvigraimpex.a $(LIB_PATH3)/libboost_python-xgcc40-mt-1_37.a $(SW_PATH)/lib/libtiff.a $(SW_PATH)/lib/libpng.a $(SW_PATH)/lib/libjpeg.a $(SW_PATH)/lib/libfftw3.a

LIB = -L$(HOME)/lib -lboost_python -lvigraimpex -ltiff -lz -lm
OBJ = 

LIB_TSP = -lboost_python  

#LIB = -L$(LIB_PATH) -lboost_python `vigra-config --libs` -lavcodec -lavformat -lavutil
#LIB = -L$(LIB_PATH) -lboost_python -L/home/twalter/src/lib -lvigraimpex -L/usr/lib/ -L/usr/lib/  -lpng -lz  -L/usr/lib/  -ljpeg  -L/usr/lib/  -ltiff -lm

#OBJS = \
#    mito.o
    
TARGETS = \
	mito \
	morpho \

.SUFFIXES: .cxx

.SUFFIXES.o:
	$(CXX) $(CXXFLAGS) $(CXXINCLUDES) -c $*.cxx

all: $(TARGETS) 

mito: mito.o
	$(LDSHARED) -o _mito.$(SONAME) mito.o $(OBJ) $(LIB)

cecog: cecog.o
	$(LDSHARED) -o _cecog.$(SONAME) cecog.o $(OBJ) $(LIB)

tsp: tsp.o
	$(LDSHARED) -o _tsp.$(SONAME) tsp.o $(LIB_TSP)

morpho: morpho.o
	$(LDSHARED) -o _morpho.$(SONAME) morpho.o $(LIB)

install:
	cp _cecog.$(SONAME) $(INSTALL_PATH_CECOG)

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

