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

#define WRAP_PAIR(first_type,second_type, name) \
  class_< std::pair<first_type,second_type>, boost::noncopyable >(name, no_init) \
    .def_readonly("first", &std::pair<first_type,second_type>::first) \
    .def_readonly("second", &std::pair<first_type,second_type>::second); \
  register_ptr_to_python< std::auto_ptr < std::pair <first_type, second_type> > >();


struct to_python_Diff2D
{
  static PyObject* convert(vigra::Diff2D const& d)
  {
    PyObject * t = PyTuple_New(2);
    PyTuple_SetItem(t, 0, PyInt_FromLong((long) d.x));
    PyTuple_SetItem(t, 1, PyInt_FromLong((long) d.y));
    return incref(t);
  }
};


list known_feature_wrapper()
{
  list result;
  for (unsigned i=0; i < cecog::FEATURE_COUNT; ++i) {
    result.append(cecog::FEATURES[i]);
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
    .def(init< vigra::Diff2D, vigra::Diff2D, vigra::Diff2D, vigra::Diff2D, double>())
    .def_readwrite("oRoi", &cecog::ROIObject::roi)
    .def_readwrite("oCenter", &cecog::ROIObject::center)
    .def_readwrite("oCenterAbs", &cecog::ROIObject::oCenterAbs)
    .def_readwrite("crackStart", &cecog::ROIObject::crack_start)
    .def_readwrite("iSize", &cecog::ROIObject::roisize)
    .def("getFeatures", &feature_wrapper)
    .def("getMeasurements", &measurement_wrapper)
    .def_readwrite("orientation", &cecog::ROIObject::orientation)

  ;
  register_ptr_to_python< std::auto_ptr<cecog::ROIObject> >();


  def("FEATURES", &known_feature_wrapper);


  class_<vigra::Diff2D>("Diff2D", init<int, int>())
  .add_property("x", &vigra::Diff2D::x)
  .add_property("y", &vigra::Diff2D::y)
  .def("magnitude", &vigra::Diff2D::magnitude)
  .def("squaredMagnitude", &vigra::Diff2D::squaredMagnitude)
  .def(self + self)           // __add__
  .def(self - self)           // __sub__
  .def(self += self)          // __iadd__
  .def(self -= self)          // __isub__
  ;
  register_ptr_to_python< std::auto_ptr<vigra::Diff2D> >();

}


#endif // CECOG_WRAP_SHARED_OBJECTS
