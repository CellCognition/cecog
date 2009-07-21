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

#ifndef CECOG_PYTHON_RENDERER_HXX_
#define CECOG_PYTHON_RENDERER_HXX_

#include "Python.h"

#include <boost/python.hpp>
#include <boost/python/list.hpp>

#include "vigra/basicimageview.hxx"
#include "vigra/basicimage.hxx"
#include "vigra/rgbvalue.hxx"
#include "vigra/array_vector.hxx"

#include "cecog/renderer.hxx"

using namespace boost::python;

namespace cecog
{
  namespace python
  {

    template <class T>
    std::auto_ptr< vigra::BasicImage< vigra::RGBValue<T> > >
    pyMakeImageOverlay1(list & images, list & colors, list & alphas)
    {
      if (len(images) <= 0)
      {
        PyErr_SetString(PyExc_IndexError,
          "List of images must contain at least one image.");
        throw_error_already_set();
      }
      if (len(images) != len(colors) || len(images) != len(alphas))
      {
        PyErr_SetString(PyExc_AssertionError,
          "List of images, colors and alphas must have same size.");
        throw_error_already_set();
      }

      typedef vigra::ArrayVector< vigra::BasicImage<T> > ImageVector;
      ImageVector imageVector = extract<ImageVector>(images)();

      typedef vigra::ArrayVector< vigra::RGBValue<T> > RGBValueVector;
      RGBValueVector colorVector = extract<RGBValueVector>(colors)();

      typedef vigra::ArrayVector< float > FloatVector;
      FloatVector alphaVector = extract<FloatVector>(alphas)();

      typedef vigra::BasicImage< vigra::RGBValue<T> > RGBImage2d;
      std::auto_ptr<RGBImage2d> res(new RGBImage2d(imageVector[0].size()));
      cecog::makeImageOverlay(imageVector, colorVector, alphaVector, *res);
      return res;
    }

    template <class T>
    std::auto_ptr< vigra::BasicImage< vigra::RGBValue<T> > >
    pyMakeImageOverlay2(list & images, list & colors)
    {
      if (len(images) <= 0)
      {
        PyErr_SetString(PyExc_IndexError,
          "List of images must contain at least one image.");
        throw_error_already_set();
      }
      if (len(images) != len(colors))
      {
        PyErr_SetString(PyExc_AssertionError,
          "List of images and colors must have same size.");
        throw_error_already_set();
      }

      typedef vigra::ArrayVector< vigra::BasicImage<T> > ImageVector;
      ImageVector imageVector = extract<ImageVector>(images)();

      typedef vigra::ArrayVector< vigra::RGBValue<T> > RGBValueVector;
      RGBValueVector colorVector = extract<RGBValueVector>(colors)();

      typedef vigra::BasicImage< vigra::RGBValue<T> > RGBImage2d;
      std::auto_ptr<RGBImage2d> res(new RGBImage2d(imageVector[0].size()));
      cecog::makeImageOverlay(imageVector, colorVector, *res);
      return res;
    }

    template <class T>
    std::auto_ptr< vigra::BasicImage< vigra::RGBValue<T> > >
    pyApplyBlending(list & images, list & alphas)
    {
      if (len(images) <= 0)
      {
        PyErr_SetString(PyExc_IndexError,
          "List of images must contain at least one image.");
        throw_error_already_set();
      }
      if (len(images) != len(alphas))
      {
        PyErr_SetString(PyExc_AssertionError,
          "List of images and colors must have same size.");
        throw_error_already_set();
      }

      typedef vigra::BasicImage< vigra::RGBValue<T> > RGBImage2d;
      typedef vigra::ArrayVector< RGBImage2d > ImageVector;
      ImageVector imageVector = extract<ImageVector>(images)();

      typedef vigra::ArrayVector< float > FloatVector;
      FloatVector alphaVector = extract<FloatVector>(alphas)();

      std::auto_ptr<RGBImage2d> res(new RGBImage2d(imageVector[0].size()));
      cecog::applyBlending(imageVector, alphaVector, *res);
      return res;
    }

  }
}

#endif /* CECOG_PYTHON_RENDERER_HXX_ */
