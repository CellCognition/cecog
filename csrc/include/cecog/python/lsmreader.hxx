/******************************************************************************
 *                                                                            *
 *                          The Mito-Imaging Project                          *
 *                                                                            *
 *                   Copyright (c) 2004-2006 by Michael Held                  *
 *                                                                            *
 *                       This is a Boost.Python wrapper.                      *
 *                                                                            *
 ******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL: https://svn.cellcognition.org/mito/trunk/include/mito/reader/wrap_lsm#$

#ifndef CECOG_PYTHON_LSMREADER_HXX_
#define CECOG_PYTHON_LSMREADER_HXX_

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/tuple.hpp>
#include <boost/python/str.hpp>
#include <boost/shared_ptr.hpp>

#include "cecog/lsmreader.hxx"

using namespace boost::python;

namespace cecog {
  namespace python {

    list wrap_lsm_timestamp_data(cecog::LsmMetaData &oMetaData)
    {
      list lstData;
      cecog::LsmMetaData::t_TimestampData::iterator it;
      for (it = oMetaData.vTimestampData.begin();
           it != oMetaData.vTimestampData.end(); ++it)
        lstData.append(*it);
      return lstData;
    }

    list wrap_lsm_channel_data(cecog::LsmMetaData &oMetaData)
    {
      list lstData;
      cecog::LsmMetaData::t_ChannelData::iterator it;
      for (it = oMetaData.vChannelData.begin();
           it != oMetaData.vChannelData.end(); ++it)
        lstData.append(make_tuple(it->first, it->second));
      return lstData;
    }

    static void wrap_lsm_reader()
    {
      class_< cecog::LsmReader >("LsmReader", init< const std::string& >())
        .def("readMetadata", &cecog::LsmReader::readMetadata)
        .def_readonly("oMetaData", &cecog::LsmReader::metadata)
        .def_readonly("strFilepath", &cecog::LsmReader::sFilepath)
        .def("getXYImage", &cecog::LsmReader::getXYImage)
      ;
      register_ptr_to_python< std::auto_ptr < cecog::LsmReader > >();
    }

    static void wrap_lsm_metadata()
    {
      class_< cecog::LsmMetaData >("LsmMetaData")
        .def_readonly("iDimX", &cecog::LsmMetaData::iDimX)
        .def_readonly("iDimY", &cecog::LsmMetaData::iDimY)
        .def_readonly("iDimZ", &cecog::LsmMetaData::iDimZ)
        .def_readonly("iDimT", &cecog::LsmMetaData::iDimT)
        .def_readonly("iDimC", &cecog::LsmMetaData::iDimC)
        .def_readonly("strPixelType", &cecog::LsmMetaData::sPixelType)
        .def_readonly("strDimOrder", &cecog::LsmMetaData::sDimOrder)
        .def_readonly("dVoxelX", &cecog::LsmMetaData::dVoxelX)
        .def_readonly("dVoxelY", &cecog::LsmMetaData::dVoxelY)
        .def_readonly("dVoxelZ", &cecog::LsmMetaData::dVoxelZ)
        .def_readonly("dTimeInterval", &cecog::LsmMetaData::dTimeInterval)
        .def("getTimestampData", &wrap_lsm_timestamp_data)
        .def("getChannelData", &wrap_lsm_channel_data)
      ;
      register_ptr_to_python< std::auto_ptr < cecog::LsmMetaData > >();
    }
  }
}
#endif // CECOG_PYTHON_LSMREADER_HXX_
