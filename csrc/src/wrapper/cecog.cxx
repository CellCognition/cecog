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

// Main boost.Python wrapper file. Definition of _cecog module.

// Boost Includes =============================================================

#include <boost/python.hpp>
#include <boost/cstdint.hpp>
#include <boost/python/overloads.hpp>
#include <boost/python/args.hpp>
#include <boost/python/str.hpp>

// Includes ===================================================================

extern "C"
{
#include <tiff.h>
#include <tiffio.h>
}


#include "vigra/stdimage.hxx"

//#include "cecog/cecog_python.hxx"
#include "cecog/container_conversions.hxx"

#include "cecog/readout.hxx"
#include "cecog/segmentation.hxx"
#include "cecog/shared_objects.hxx"


#include "cecog/wrap_images.hxx"
#include "cecog/wrap_multiarray.hxx"
#include "cecog/wrap_containers.hxx"
#include "cecog/wrap_shared_objects.hxx"
#include "cecog/wrap_config.hxx"
#include "cecog/wrap_map.hxx"

// Using ======================================================================

using namespace boost::python;



// Container Wrappers =========================================================

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
  for (int i=0; i < cecog::FEATURE_COUNT; ++i)
    result.append(cecog::FEATURES[i]);
  return result;
}




// Macros =====================================================================

BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(get_container_overloads, getContainer_old, 1, 3)
BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(pyOverloads_ArrayStitcher_addImage, addImage, 3, 5)


// Module =====================================================================

static void turn_off()
{
  TIFFSetWarningHandler(NULL);
}

BOOST_PYTHON_MODULE(_cecog)
{

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

  //    to_python_converter<vigra::Diff2D, to_python_Diff2D>();

  // PYTHON - TO - C++ conversions

  conversions::from_python_sequence<std::vector<unsigned>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<int>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<double>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<float>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<std::string>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<std::pair<int, int> >,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<vigra::Diff2D>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<vigra::BImage>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<vigra::BRGBImage>,
  conversions::variable_capacity_policy>();

  conversions::from_python_sequence<std::vector<cecog::RGBValue>,
  conversions::variable_capacity_policy>();

  wrap_map<int, bool>("MapIntBool");
  wrap_map<int, cecog::RGBValue>("MapIntRGBValue");

  enum_<cecog::SegmentationType>("SegmentationType")
  .value("ShapeBased",     cecog::ShapeBasedSegmentation)
  .value("IntensityBased", cecog::IntensityBasedSegmentation)
  ;

  enum_<cecog::SRGType>("SrgType")
  .value("KeepContours",     cecog::KeepContours)
  .value("KeepContoursPlus", cecog::KeepContoursPlus)
  .value("CompleteGrow",     cecog::CompleteGrow)
  ;

  def("transformImageListToArray4D", cecog::transformImageListToArray4D);

  def("turn_off", turn_off);

  class_< cecog::ArrayStitcher >("ArrayStitcher", init<int, int, int, int, optional<float> >())
    .def("addImage", &cecog::ArrayStitcher::addImage,
         pyOverloads_ArrayStitcher_addImage(args("imgRGB", "iPosX", "iPosY", "iFrameSize", "oFrameColor")))
    .def("getStitchedImage", &cecog::ArrayStitcher::getStitchedImage)
    ;


  wrap_images();
  wrap_multiarray();

  wrap_containers();
  wrap_shared_objects();
  wrap_config();

}

