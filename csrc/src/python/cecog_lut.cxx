/*******************************************************************************

                          The CellCognition Project
                   Copyright (c) 2006 - 2009 Michael Held
                    Gerlich Lab, ETH Zurich, Switzerland

            CellCognition is distributed under the LGPL license.
                      See the LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL: https://svn.cellcognition.org/mito/trunk/include/mito/reader/wrap_lsm#$

#include <boost/python.hpp>
#include <boost/python/overloads.hpp>

#include "cecog/python/lut.hxx"

void wrap_lut()
{
  using namespace boost::python;
  using namespace cecog::python;

  def("read_lut", pyReadLut,
      (arg("filename")),
      "Read LUT from file.");

  def("apply_lut", pyApplyLut,
      (arg("image"), arg("lut")),
      "Apply a LUT to an UInt8 image and returns an UInt8 RGB image.");

  def("lut_from_single_color", pyLutFromSingleColor,
      (arg("color")),
      "Generates a 256 color LUT from one RGB color.");

}
