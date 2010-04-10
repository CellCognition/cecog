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


#ifndef CECOG_WRAP_CONFIG
#define CECOG_WRAP_CONFIG

#include <memory>

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/str.hpp>
#include <boost/shared_ptr.hpp>

#include "cecog/config.hxx"


using namespace boost::python;



static void wrap_config()
{
  class_< cecog::Config >("Config")
    .def_readwrite("strFontFilepath", &cecog::Config::strFontFilepath)
  ;
  register_ptr_to_python< std::auto_ptr<cecog::Config> >();
}


#endif // CECOG_WRAP_CONFIG
