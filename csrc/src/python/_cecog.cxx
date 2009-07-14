/*******************************************************************************

                          The CellCognition Project
                   Copyright (c) 2006 - 2009 Michael Held
                    Gerlich Lab, ETH Zurich, Switzerland

            CellCognition is distributed under the LGPL license.
                      See the LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

#include <boost/python.hpp>

#include "cecog/python/cecog.hxx"

using namespace boost::python;

BOOST_PYTHON_MODULE(_cecog)
{
  using namespace cecog::python;

  wrap_cecog();
}
