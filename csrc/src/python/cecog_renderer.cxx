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
#include <boost/python/args.hpp>

#include "cecog/python/renderer.hxx"

using namespace boost::python;
using namespace cecog::python;

void wrap_renderer()
{
  def("make_image_overlay", pyMakeImageOverlay1<vigra::UInt8>,
      args("images", "colors", "alphas"),
      "Creates an overlay image from a list of UInt8 images and a list of RGB colors."
      );

  def("make_image_overlay", pyMakeImageOverlay2<vigra::UInt8>,
      args("images", "colors"),
      "Creates an overlay image from a list of UInt8 images and a list of RGB colors."
      );

  def("apply_blending", pyApplyBlending<vigra::UInt8>,
      args("images", "alphas"),
      "Combines a list of RGB images and alpha values to one RGB image by maximum-blending."
      );
}
