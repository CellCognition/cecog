cmake_minimum_required(VERSION 2.6)

PROJECT(cecog_ccore)


IF (NOT CMAKE_BUILD_TYPE)
    MESSAGE(STATUS "Build type -> Release")
    SET(CMAKE_BUILD_TYPE "Release")
ENDIF()


########################################################################
# ADD DEPENDENCY_SEARCH_PREFIX TO CMAKES'FIND_PACKAGE PATH
########################################################################
########################################################################

FOREACH(path ${DEPENDENCY_SEARCH_PREFIX})  
    SET(CMAKE_INCLUDE_PATH ${path}/include)
    SET(CMAKE_LIBRARY_PATH ${path}/lib)       
ENDFOREACH(path)


########################################################################
# SEARCH FOR PYTHON AND NUMPY
########################################################################
########################################################################

FIND_PACKAGE(PythonInterp REQUIRED)
FIND_PACKAGE(PythonLibs)
IF(NOT PYTHONLIBS_FOUND)
    MESSAGE(STATUS " activate fallback when standard search does not work...")
    execute_process(COMMAND ${PYTHON_EXECUTABLE} -c 
                     "import sys; skip = 2 if sys.platform.startswith('win') else 1; print 'python' + sys.version[0:3:skip]"
                      OUTPUT_VARIABLE PYTHON_LIBRARY_NAME OUTPUT_STRIP_TRAILING_WHITESPACE)
    execute_process(COMMAND ${PYTHON_EXECUTABLE} -c 
                     "import sys; print sys.exec_prefix"
                      OUTPUT_VARIABLE PYTHON_PREFIX OUTPUT_STRIP_TRAILING_WHITESPACE)
    FIND_LIBRARY(PYTHON_LIBRARY ${PYTHON_LIBRARY_NAME} "${PYTHON_PREFIX}/libs")
    execute_process(COMMAND ${PYTHON_EXECUTABLE} -c
                    "from distutils.sysconfig import *; print get_python_inc()"
                     OUTPUT_VARIABLE PYTHON_INCLUDE OUTPUT_STRIP_TRAILING_WHITESPACE)
    SET(PYTHON_INCLUDE_DIR ${PYTHON_INCLUDE}
        CACHE PATH "Path to Python include files"
        FORCE)
    IF(PYTHON_LIBRARY AND PYTHON_INCLUDE_DIR)
       MESSAGE(STATUS " success")
       SET(PYTHONLIBS_FOUND TRUE)
    ELSE()
       MESSAGE(STATUS " failed")
    ENDIF()
ENDIF()


IF(PYTHONINTERP_FOUND)
    IF(NOT NUMPY_INCLUDE_DIR)
        # Note: we must suppress possible output of the 'from numpy... import *' command,
        #       because the output cannot be interpreted correctly otherwise
        execute_process(COMMAND ${PYTHON_EXECUTABLE} -c 
                         "import sys, os; sys.stdout = open(os.devnull, 'w'); from numpy.distutils.misc_util import *; sys.__stdout__.write(' '.join(get_numpy_include_dirs()))"
                          RESULT_VARIABLE PYTHON_NUMPY_NOT_FOUND
                          OUTPUT_VARIABLE NUMPY_INCLUDE_DIR 
                          OUTPUT_STRIP_TRAILING_WHITESPACE)
        IF(NOT PYTHON_NUMPY_NOT_FOUND)
            FILE(TO_CMAKE_PATH ${NUMPY_INCLUDE_DIR} NUMPY_INCLUDE_DIR)
        ELSE()
            SET(NUMPY_INCLUDE_DIR "NUMPY_INCLUDE_DIR-NOTFOUND")
        ENDIF()
    ENDIF()

    SET(NUMPY_INCLUDE_DIR ${NUMPY_INCLUDE_DIR}
        CACHE PATH "Path to numpy include files" FORCE)
    IF(NUMPY_INCLUDE_DIR)
        MESSAGE(STATUS "Searching for Python numpy: ok")
    ELSE()
        MESSAGE(SEND_ERROR "Could NOT find Python numpy ('import numpy.distutils.misc_util' failed)")
    ENDIF()
ENDIF()

########################################################################
# CHECK FOR VIGRA
########################################################################
########################################################################

IF(NOT VIGRA_INCLUDE_DIR)
    MESSAGE(SEND_ERROR "VIGRA_INCLUDE_DIR not given. Use -DVIGRA_INCLUDE_DIR=<path-to-vigra-include>")
ENDIF()

IF(NOT VIGRA_IMPEX_LIBRARY)
    MESSAGE(SEND_ERROR "VIGRA_IMPEX_LIBRARY not given. Use -DVIGRA_IMPEX_LIBRARY=<vigra-impex-library>")
ENDIF()

########################################################################
# CHECK FOR TIFF AND BOOST 
########################################################################
########################################################################

FIND_PACKAGE(TIFF REQUIRED)
FIND_PACKAGE(Boost COMPONENTS python REQUIRED)


MESSAGE(STATUS "")
MESSAGE(STATUS " ----------------------------------------")
MESSAGE(STATUS " --- cecog-ccore Summary      -----------")
MESSAGE(STATUS " ----------------------------------------")
MESSAGE(STATUS "")
MESSAGE(STATUS " VIGRA_INCLUDE_DIR -> " ${VIGRA_INCLUDE_DIR})
MESSAGE(STATUS " VIGRA_IMPEX_LIBRARY -> " ${VIGRA_IMPEX_LIBRARY})
MESSAGE(STATUS " TIFF_INCLUDE_DIR -> " ${TIFF_INCLUDE_DIR})
MESSAGE(STATUS " TIFF_LIBRARY -> " ${TIFF_LIBRARY})
MESSAGE(STATUS " Boost_INCLUDE_DIR -> " ${Boost_INCLUDE_DIR})
MESSAGE(STATUS " Boost_PYTHON_LIBRARY -> " ${Boost_PYTHON_LIBRARY})
MESSAGE(STATUS " PYTHON_INCLUDE_DIR -> " ${PYTHON_INCLUDE_DIR})
MESSAGE(STATUS " PYTHON_LIBRARY -> " ${PYTHON_LIBRARY})
MESSAGE(STATUS " NUMPY_INCLUDE_DIR ->" ${NUMPY_INCLUDE_DIR})
MESSAGE(STATUS "")
MESSAGE(STATUS " ----------------------------------------")
MESSAGE(STATUS " ccore will be installed to " ${cecog_ccore_SOURCE_DIR}/../../../pysrc/cecog/ccore/_cecog.pyd)
MESSAGE(STATUS "")







# SET(VIGRA_INCLUDE_DIR "C:/Users/sommerc/src/vigra-hg/include")
# SET(TIFF_INCLUDE_DIR "c:/depend64/include")
# SET(BOOST_INCLUDE_DIR "c:/depend64/include")
# SET(PYTHON_INCLUDE_DIR "c:/Python27/include")
# SET(NUMPY_INCLUDE_DIR "C:/Python27/Lib/site-packages/numpy/core/include")

# SET(TIFF_LIBRARY "c:/depend64/lib/libtiff_i.lib")
# SET(Boost_PYTHON_LIBRARY "c:/depend64/lib/boost_python-vc100-mt-1_45.lib")
# SET(VIGRA_IMPEX_LIBRARY "C:/Program Files/vigra/lib/vigraimpex.lib")
# SET(PYTHON_LIBRARY "c:/Python27/libs/python27.lib")

SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /bigobj")

SET(CMAKE_BUILD_TYPE Release)

INCLUDE_DIRECTORIES(${cecog_ccore_SOURCE_DIR}/../../include ${VIGRA_INCLUDE_DIR} ${TIFF_INCLUDE_DIR} ${BOOST_INCLUDE_DIR} ${PYTHON_INCLUDE_DIR} ${NUMPY_INCLUDE_DIR})

ADD_LIBRARY(cecog-lib SHARED
    cecog.cxx) 
    
TARGET_LINK_LIBRARIES(cecog-lib ${TIFF_LIBRARY} ${Boost_PYTHON_LIBRARY} ${VIGRA_IMPEX_LIBRARY} ${PYTHON_LIBRARY})

ADD_CUSTOM_COMMAND(
    TARGET cecog-lib
    POST_BUILD
    IF(PYTHON_PLATFORM MATCHES "^windows$")
         COMMAND COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_BINARY_DIR}/${CMAKE_BUILD_TYPE}/cecog-lib.dll ${cecog_ccore_SOURCE_DIR}/../../../pysrc/cecog/ccore/_cecog.pyd
    ELSE()
         COMMAND COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_BINARY_DIR}/libcecog-lib.so ${cecog_ccore_SOURCE_DIR}/../../../pysrc/cecog/ccore/_cecog.so
    ENDIF()
   
)
