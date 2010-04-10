/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL$


#ifndef CECOG_WRAP_SHARED_OBJECTS
#define CECOG_WRAP_SHARED_OBJECTS

#include <memory>

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/str.hpp>
#include <boost/shared_ptr.hpp>

#include "cecog/shared_objects.hxx"


using namespace boost::python;


dict feature_wrapper(cecog::ROIObject & c)
{
  dict result;
  cecog::FeatureMap::iterator it;
  for (it = c.features.begin(); it != c.features.end(); ++it){
    result[(*it).first] = (*it).second;
  }
  return result;
}

dict measurement_wrapper(cecog::ROIObject & c)
{
  dict result;
  cecog::FeatureMap::iterator it;
  for (it = c.measurements.begin(); it != c.measurements.end(); ++it){
    result[(*it).first] = (*it).second;
  }
  return result;
}

static void wrap_shared_objects()
{

  class_< cecog::Region >("Region", init< const cecog::Region& >())
    .def(init< int, int, int, int >())
    .def(init< vigra::Diff2D, vigra::Diff2D >())
    .def_readwrite("upperLeft", &cecog::Region::upperLeft)
    .def_readwrite("lowerRight", &cecog::Region::lowerRight)
    .def_readwrite("size", &cecog::Region::size)
    .def_readwrite("x", &cecog::Region::x)
    .def_readwrite("y", &cecog::Region::y)
    .def_readwrite("width", &cecog::Region::width)
    .def_readwrite("height", &cecog::Region::height)
    .def_readwrite("area", &cecog::Region::area)
    //.def_readwrite("center", &cecog::Region::center)
    //.def_readwrite("rCenter", &cecog::Region::rCenter)
  ;
  register_ptr_to_python< std::auto_ptr<cecog::Region> >();


  class_< cecog::ROIObject >("ROIObject", init< const cecog::ROIObject& >())
    .def(init< vigra::Diff2D, vigra::Diff2D, vigra::Diff2D >())
    .def(init< vigra::Diff2D, vigra::Diff2D, vigra::Diff2D, vigra::Diff2D, vigra::Diff2D, double>())
    .def_readwrite("oRoi", &cecog::ROIObject::roi)
    .def_readwrite("oCenter", &cecog::ROIObject::center)
    .def_readwrite("oCenterAbs", &cecog::ROIObject::oCenterAbs)
    .def_readwrite("crackStart", &cecog::ROIObject::crack_start)
    .def_readwrite("crackStart2", &cecog::ROIObject::crack_start2)
    .def_readwrite("iSize", &cecog::ROIObject::roisize)
    .def("getFeatures", &feature_wrapper)
    .def("getMeasurements", &measurement_wrapper)
  ;
  register_ptr_to_python< std::auto_ptr<cecog::ROIObject> >();

}


#endif // CECOG_WRAP_SHARED_OBJECTS
