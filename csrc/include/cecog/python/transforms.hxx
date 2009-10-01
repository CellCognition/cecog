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

#ifndef CECOG_PYTHON_TRANSFORM_HXX_
#define CECOG_PYTHON_TRANSFORM_HXX_

#include <boost/python.hpp>
#include "vigra/transformimage.hxx"
#include "cecog/transforms.hxx"

using namespace boost::python;

namespace cecog
{
  namespace python
  {
    template <class IMAGE1, class IMAGE2>
    inline void
    pyProtectedLinearRangeMapping(IMAGE1 const &imgIn, IMAGE2 &imgOut,
                                  typename IMAGE1::value_type srcMin, typename IMAGE1::value_type srcMax,
                                  typename IMAGE2::value_type destMin, typename IMAGE2::value_type destMax)
    {
      vigra::transformImage(srcImageRange(imgIn), destImage(imgOut),
                            cecog::ProtectedLinearRangeMapping<typename IMAGE1::value_type, typename IMAGE2::value_type>(srcMin, srcMax, destMin, destMax));
    }

    template <class IMAGE1, class IMAGE2>
    inline
    std::auto_ptr< IMAGE2 >
    pyProtectedLinearRangeMapping_(IMAGE1 const &imgIn,
                                   typename IMAGE1::value_type srcMin, typename IMAGE1::value_type srcMax,
                                   typename IMAGE2::value_type destMin, typename IMAGE2::value_type destMax)
    {
      std::auto_ptr<IMAGE2> res(new IMAGE2(imgIn.size()));
      vigra::transformImage(srcImageRange(imgIn), destImage(*res),
                            cecog::ProtectedLinearRangeMapping<typename IMAGE1::value_type, typename IMAGE2::value_type>(srcMin, srcMax, destMin, destMax));
      return res;
    }
  }
}

#endif /* CECOG_PYTHON_TRANSFORM_HXX_ */
