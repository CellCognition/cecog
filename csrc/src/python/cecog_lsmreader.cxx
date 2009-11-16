/******************************************************************************
 *                                                                            *
 *                          The Mito-Imaging Project                          *
 *                                                                            *
 *                   Copyright (c) 2004-2006 by Michael Held                  *
 *                                                                            *
 *                       This is a Boost.Python wrapper.                      *
 *                                                                            *
 ******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL: https://svn.cellcognition.org/mito/trunk/include/mito/reader/wrap_lsm#$

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/tuple.hpp>
#include <boost/python/str.hpp>
#include <boost/shared_ptr.hpp>

#include "cecog/python/lsmreader.hxx"

void wrap_lsmreader()
{
  using namespace boost::python;
  using namespace cecog::python;

  wrap_lsm_reader();
  wrap_lsm_metadata();
}
