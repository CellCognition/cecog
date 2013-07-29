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

#include <boost/python.hpp>

#include <cecog/container_conversions.hxx>
#include <cecog/segmentation.hxx>

#include <cecog/wrapper/wrap_filters.hxx>
#include <cecog/wrapper/wrap_segmentation.hxx>
#include <cecog/wrapper/wrap_containers.hxx>
#include <cecog/wrapper/wrap_images.hxx>
#include <cecog/wrapper/wrap_shared_objects.hxx>
#include <cecog/wrapper/wrap_config.hxx>

extern "C"
{
#include <tiff.h>
#include <tiffio.h>
}

//void wrap_filters();
//void wrap_segmentation();
//void wrap_containers();

static void turn_off()
{
  TIFFSetWarningHandler(NULL);
}

static void turn_tiff_warnings_off()
{
  TIFFSetWarningHandler(0);
}

BOOST_PYTHON_MODULE(_cecog)
{
  def("turn_off", turn_off);
  def("turn_tiff_warnings_off", turn_tiff_warnings_off);

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

  wrap_filters();
  wrap_segmentation();
  wrap_containers();
  wrap_shared_objects();
  wrap_config();
  wrap_images();
}
