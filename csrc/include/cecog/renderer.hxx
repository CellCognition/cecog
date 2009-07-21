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

#ifndef CECOG_RENDERER_HXX_
#define CECOG_RENDERER_HXX_

#include "vigra/basicimageview.hxx"
#include "vigra/basicimage.hxx"
#include "vigra/rgbvalue.hxx"
#include "vigra/array_vector.hxx"

namespace cecog
{

  /**
   * Creates a new RGB image from a list of scalar images, a list of colors
   * (RGB values) and a list of alpha values by maximum-intensity blending.
   */
  template <class T>
  inline void
  makeImageOverlay(
    vigra::ArrayVector< vigra::BasicImage<T> > const & imageVector,
    vigra::ArrayVector< vigra::RGBValue<T> > const & channelVector,
    vigra::ArrayVector< float > const & alphaVector,
    vigra::BasicImage< vigra::RGBValue<T> > & rgb_image)
  {
    for (unsigned int c=0; c < imageVector.size(); c++)
    {
      vigra::RGBValue<T> rgb = channelVector[c];
      float alpha = alphaVector[c];

      vigra::BasicImage<T> view = imageVector[c];

      // we could probably also do a combineTwoImages here
      typename vigra::BasicImage<T>::const_iterator it_view = view.begin();
      typename vigra::BasicImage<vigra::RGBValue<T> >::ScanOrderIterator
        it_img = rgb_image.begin();
      for (; it_view != view.end() && it_img != rgb_image.end();
           it_view++, it_img++)
        // loop over r,g,b: do the RGB-blending
        for (int m=0; m < 3; m++)
        {
          // scale the current pixel by means of its channel component
          // FIXME: scaling is limited to uint8,
          //        so template generalization is broken here
          T value = *it_view / 255.0 * rgb[m] * alpha;
          // do a max-blending with any value already assigned to this pixel
          (*it_img)[m] = std::max((*it_img)[m], value);
        }
    }
  }

  /**
   * Creates a new RGB image from a list of scalar images and a list of colors
   * (RGB values) by maximum-intensity blending.
   *
   * For the pure sake of performance in a browser application this code is
   * a mere duplication of the above.
   */
  template <class T>
  inline void
  makeImageOverlay(
    vigra::ArrayVector< vigra::BasicImage<T> > const & imageVector,
    vigra::ArrayVector< vigra::RGBValue<T> > const & channelVector,
    vigra::BasicImage< vigra::RGBValue<T> > & rgb_image)
  {
    for (unsigned int c=0; c < imageVector.size(); c++)
    {
      vigra::RGBValue<T> rgb = channelVector[c];
      vigra::BasicImage<T> view = imageVector[c];

      // we could probably also do a combineTwoImages here
      typename vigra::BasicImage<T>::const_iterator it_view = view.begin();
      typename vigra::BasicImage<vigra::RGBValue<T> >::ScanOrderIterator
        it_img = rgb_image.begin();
      for (; it_view != view.end() && it_img != rgb_image.end();
           it_view++, it_img++)
        // loop over r,g,b: do the RGB-blending
        for (int m=0; m < 3; m++)
        {
          // scale the current pixel by means of its channel component
          // FIXME: scaling is limited to uint8,
          //        so template generalization is broken here
          T value = *it_view / 255.0 * rgb[m];
          // do a max-blending with any value already assigned to this pixel
          (*it_img)[m] = std::max((*it_img)[m], value);
        }
    }
  }

  /**
   * Creates a new RGB image from a list of scalar images, a list of colors
   * (RGB values) and a list of alpha values by maximum-intensity blending.
   */
  template <class T>
  inline void
  applyBlending(
    vigra::ArrayVector< vigra::BasicImage< vigra::RGBValue<T> > > const & imageVector,
    vigra::ArrayVector< float > const & alphaVector,
    vigra::BasicImage< vigra::RGBValue<T> > & rgb_image)
  {
    for (unsigned int c=0; c < imageVector.size(); c++)
    {
      float alpha = alphaVector[c];
      // we could probably also do a combineTwoImages here
      typename vigra::BasicImage<vigra::RGBValue<T> >::const_iterator it_image = imageVector[c].begin();
      typename vigra::BasicImage<vigra::RGBValue<T> >::iterator it_rgb = rgb_image.begin();
      for (; it_image != imageVector[c].end() && it_rgb != rgb_image.end();
           it_image++, it_rgb++)
        // loop over r,g,b: do the RGB-blending
        for (int m=0; m < 3; m++)
          // do a max-blending with any value already assigned to this pixel
          (*it_rgb)[m] = std::max((*it_rgb)[m], static_cast<vigra::UInt8>((*it_image)[m] * alpha));
    }
  }

}

#endif /* CECOG_RENDERER_HXX_ */
