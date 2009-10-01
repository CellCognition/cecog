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

#include "vigra/stdimage.hxx"
#include "cecog/python/transforms.hxx"

void wrap_transforms()
{
  using namespace cecog::python;
  def("protected_linear_range_mapping", pyProtectedLinearRangeMapping<vigra::UInt8Image, vigra::UInt8Image>);
  def("protected_linear_range_mapping", pyProtectedLinearRangeMapping_<vigra::UInt8Image, vigra::UInt8Image>);
}
