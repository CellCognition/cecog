cmake_minimum_required(VERSION 2.6)

PROJECT(cecog_ccore)

IF (NOT CMAKE_BUILD_TYPE)
    MESSAGE(STATUS "Build type -> Release")
    SET(CMAKE_BUILD_TYPE "Release")
ENDIF()

SET(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/config)

########################################################################
# ADD DEPENDENCY_SEARCH_PREFIX TO CMAKES'FIND_PACKAGE PATH
########################################################################
########################################################################

FOREACH(path ${DEPENDENCY_SEARCH_PREFIX})
    SET(CMAKE_INCLUDE_PATH ${path}/include;${CMAKE_INCLUDE_PATH})
    SET(CMAKE_LIBRARY_PATH ${path}/lib;${CMAKE_LIBRARY_PATH})
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
    FIND_PATH(VIGRA_INCLUDE_DIR vigra/impex.hxx)
    IF (VIGRA_INCLUDE_DIR)
        MESSAGE(STATUS "Found vigra in " ${VIGRA_INCLUDE_DIR})
    ELSE()
        MESSAGE(SEND_ERROR "VIGRA_INCLUDE_DIR not found. Try -DVIGRA_INCLUDE_DIR=<path-to-vigra-include>")
    ENDIF()
ENDIF()

IF(NOT VIGRA_IMPEX_LIBRARY)
    FIND_LIBRARY(VIGRA_IMPEX_LIBRARY vigraimpex)
    IF (VIGRA_IMPEX_LIBRARY)
        MESSAGE(STATUS "Found vigra impex " ${VIGRA_IMPEX_LIBRARY})
    ELSE()
        MESSAGE(SEND_ERROR "VIGRA_IMPEX_LIBRARY not found. Try -DVIGRA_IMPEX_LIBRARY=<vigra-impex-library>")
    ENDIF()

ENDIF()


########################################################################
# CHECK FOR TIFF AND BOOST
########################################################################
########################################################################

FIND_PACKAGE(TIFF REQUIRED)
FIND_PACKAGE(ZLIB REQUIRED)
FIND_PACKAGE(LZMA REQUIRED)
FIND_PACKAGE(Boost COMPONENTS python REQUIRED)


MESSAGE(STATUS "")
MESSAGE(STATUS " ----------------------------------------")
MESSAGE(STATUS " --- cecog-ccore Summary   --------------")
MESSAGE(STATUS " ----------------------------------------")
MESSAGE(STATUS " running on " ${CMAKE_SYSTEM_NAME})
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
MESSAGE(STATUS " LZMA_INCLUDE ->" ${LZMA_INCLUDE_DIR})
MESSAGE(STATUS " LZMA_LIBRARY -> "${LZMA_LIBRARY})
MESSAGE(STATUS "")
MESSAGE(STATUS " ----------------------------------------")
MESSAGE(STATUS " ccore will be installed to " ${cecog_ccore_SOURCE_DIR}/../../../pysrc/cecog/ccore/)
MESSAGE(STATUS "")


IF(${CMAKE_SYSTEM_NAME} MATCHES "^Windows$")
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /bigobj")
ENDIF()

INCLUDE_DIRECTORIES(${cecog_ccore_SOURCE_DIR}/../../include ${VIGRA_INCLUDE_DIR} ${TIFF_INCLUDE_DIR} ${BOOST_INCLUDE_DIR} ${PYTHON_INCLUDE_DIR} ${NUMPY_INCLUDE_DIR})

ADD_LIBRARY(cecog-lib SHARED cecog.cxx)

TARGET_LINK_LIBRARIES(cecog-lib ${TIFF_LIBRARY} ${Boost_PYTHON_LIBRARY} ${VIGRA_IMPEX_LIBRARY} ${PYTHON_LIBRARY} ${ZLIB_LIBRARIES} ${LZMA_LIBRARY})

GET_TARGET_PROPERTY(LIB_NAME cecog-lib LOCATION)



IF(${CMAKE_SYSTEM_NAME} MATCHES "^Windows$")
    SET(PLATFORM_LIBRARY_POSTFIX ".pyd")
#ELSEIF(${CMAKE_SYSTEM_NAME} MATCHES "^Linux$")
ELSE()
    SET(PLATFORM_LIBRARY_POSTFIX ".so")
ENDIF()

SET(NEW_LIB_NAME _cecog${PLATFORM_LIBRARY_POSTFIX})

ADD_CUSTOM_COMMAND(
    TARGET cecog-lib
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy ${LIB_NAME} ../${NEW_LIB_NAME}
    COMMENT "copying ${LIB_NAME} ${NEW_LIB_NAME}"
)

# g++ specific options
IF(CMAKE_COMPILER_IS_GNUCC OR CMAKE_COMPILER_IS_GNUCXX)
#  SET(CMAKE_CXX_COMPILER "g++-4.7")
  SET(CMAKE_CXX_FLAGS "${CMAKE_C_FLAGS} -Wall")
ENDIF()

INSTALL(FILES ${NEW_LIB_NAME} DESTINATION ${cecog_ccore_SOURCE_DIR}/../../../pysrc/cecog/ccore/)
