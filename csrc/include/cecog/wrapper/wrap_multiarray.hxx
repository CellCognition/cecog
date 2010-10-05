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


#ifndef CECOG_WRAP_MULTIARRAY
#define CECOG_WRAP_MULTIARRAY

#include <memory>

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/str.hpp>
#include <boost/shared_ptr.hpp>

#include "vigra/multi_array.hxx"
#include "vigra/tinyvector.hxx"

#include "cecog/shared_objects.hxx"

using namespace boost::python;


template <unsigned int N, class T>
static void wrapMultiArray(const char * name, const char * name2)
{
  typedef vigra::MultiArray<N, T> MultiArray;
  class_< MultiArray >(name, init<>())
    ;
  register_ptr_to_python< std::auto_ptr< MultiArray > >();

  typedef typename MultiArray::difference_type difference_type;
  class_< difference_type >(name2, init<>())
    ;
  register_ptr_to_python< std::auto_ptr< difference_type > >();
}

template <unsigned int N, class T>
static void wrapMultiArrayView(const char * name)
{
  typedef vigra::MultiArrayView<N, T> MultiArrayView;
  class_< MultiArrayView >(name, init<>())
    ;
  register_ptr_to_python< std::auto_ptr< MultiArrayView > >();
}


static void wrap_multiarray()
{
//  pyWrapMultiArrayView<2, uint8>("View2D");
//  pyWrapMultiArrayView<3, uint8>("View3D");
//  pyWrapMultiArrayView<4, uint8>("View4D");
//  pyWrapMultiArrayView<5, uint8>("View5D");

//  wrapMultiArray<2, uint8>("Array2D", "moo2");
//  wrapMultiArray<3, uint8>("Array3D", "moo3");
//  wrapMultiArray<4, uint8>("Array4D", "moo4");
//  wrapMultiArray<5, uint8>("Array5D", "moo5");
//  pyWrapMultiArray<6, uint8>("Array6D", "moo6");

}

#endif // CECOG_WRAP_MULTIARRAY
