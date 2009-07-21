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

#ifndef CECOG_PYTHON_LUT_HXX_
#define CECOG_PYTHON_LUT_HXX_

#include <boost/python.hpp>
#include <boost/python/list.hpp>

#include "vigra/impex.hxx"
#include "vigra/basicimage.hxx"

#include "cecog/lut.hxx"

using namespace boost::python;

namespace cecog
{
  namespace python
  {

    list
    pyReadLut(std::string const & filename)
    {
      cecog::LutType lut;
      cecog::readLut(filename, lut);
      list lst;
      for (cecog::LutType::iterator it=lut.begin(); it != lut.end(); ++it)
        lst.append(*it);
      return lst;
    }

    std::auto_ptr< vigra::UInt8RGBImage >
    pyApplyLut(vigra::UInt8Image const & img, cecog::LutType const & lut)
    {
      typedef vigra::UInt8RGBImage RGBImage2d;
      std::auto_ptr<RGBImage2d> res(new RGBImage2d(img.size()));
      cecog::applyLut(img, *res, lut);
      return res;
    }

    list
    pyLutFromSingleColor(cecog::UInt8RGBValue const &color)
    {
      cecog::LutType lut;
      cecog::lutFromSingleColor(color, lut);
      list lst;
      for (cecog::LutType::iterator it=lut.begin(); it != lut.end(); ++it)
        lst.append(*it);
      return lst;
    }

  }
}

#endif /* CECOG_PYTHON_LUT_HXX_ */
