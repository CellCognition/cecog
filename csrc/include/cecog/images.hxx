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


#ifndef CECOG_IMAGE
#define CECOG_IMAGE

#include "cecog/thresholds.hxx"
#include "cecog/inspectors.hxx"
#include "cecog/transforms.hxx"

namespace cecog
{
  struct Error_Trait_Type {};

  template <int>
  struct PixelTypeTraits
  {
    typedef Error_Trait_Type RequiredPixelType;
    typedef Error_Trait_Type greylevels;
    typedef Error_Trait_Type offset;
  };

  template<>
  struct PixelTypeTraits<8>
  {
    typedef unsigned char RequiredPixelType;
    static const unsigned greylevels = 256;
    static const int offset = 0;
  };

  template<>
  struct PixelTypeTraits<12>
  {
    typedef signed short RequiredPixelType;
    static const unsigned greylevels = 4096;
    static const int offset = 32768;
  };

  template<>
  struct PixelTypeTraits<120>
  {
    typedef signed short RequiredPixelType;
    static const unsigned greylevels = 4096;
    static const int offset = 0;
  };

  template<>
  struct PixelTypeTraits<16>
  {
    typedef unsigned short RequiredPixelType;
    static const unsigned greylevels = 65536;
    static const int offset = 0;
  };

  template<>
  struct PixelTypeTraits<32>
  {
    typedef unsigned long RequiredPixelType;
    // attention: this is not the number of greyleves, but the
    // maximal grey level.
    static const unsigned long greylevels = 4294967295UL;
    static const long offset = 0;
  };


  /**
   * the class Image is a template; BIT_DEPTH is the template parameter
   * i.e. the type of image.
   * Image inherits from the vigra-class BasicImage (also a template);
   * the type is:
   * PixelTypeTraits<BIT_DEPTH>::RequiredPixelType
   * which is defined above.
   */
  template <int BIT_DEPTH>
  class Image : public vigra::BasicImage<typename PixelTypeTraits<BIT_DEPTH>::RequiredPixelType>
  {
  public:

    // PixelTypesTraits is a structure containing:
    // - RequiredPixelType (the type of the pixels)
    // - greyLevels (the number of grey levels for the given type)
    // - offset (the difference to 0 for the given type)
    typedef PixelTypeTraits<BIT_DEPTH> PixelTypeTraits;

    // BaseType: abbreviation for the image type.
    typedef vigra::BasicImage<typename PixelTypeTraits::RequiredPixelType> BaseType;

    // Histogram
    typedef FindHistogram<typename PixelTypeTraits::RequiredPixelType> Histogram;

    // Constructor 1
    Image(int width, int height, typename BaseType::const_pointer p)
      : BaseType(width, height, p)
    {};

    // Constructor 2
    Image(int width, int height)
      : BaseType(width, height)
    {};

    // Constructor 3
    Image(vigra::Diff2D size)
      : BaseType(size)
    {};

    // Constructor 4
    Image(Image const & rhs)
      : BaseType(rhs)
    {};

    // Constructor 4
    Image()
      : BaseType()
    {};


    Histogram histogram()
    {
      return histogram(vigra::Diff2D(0,0),
                       vigra::Diff2D(this->width()-1, this->height()-1));
    }

    Histogram histogram(vigra::Diff2D ul, vigra::Diff2D lr)
    {
      Histogram histogram(PixelTypeTraits::greylevels);
      vigra::inspectImage(this->upperLeft() + ul,
                          this->upperLeft() + lr,
                          this->accessor(),
                          histogram);
      return histogram;
    }

    vigra::BImage histogramImage()
    {
      Histogram hist = histogram();
      const unsigned int size = hist.size();
      vigra::BImage histImg(size, size);
      histImg = size - 1;
      vigra::BImage::traverser ul = histImg.upperLeft();
      std::vector<double> probs = hist.probabilities();
      for (int i = 0; i < size; ++i, ++ul.x)
      {
        int v = int(size * (1 - probs[i]));
        drawHVLine(ul.columnIterator(),
        ul.columnIterator() + v,
        histImg.accessor(), 0);
      }
      return histImg;
    }

  };

}

#endif // CECOG_IMAGE
