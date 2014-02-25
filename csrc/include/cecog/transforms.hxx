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


#ifndef CECOG_TRANSFORMS
#define CECOG_TRANSFORMS

#include <algorithm>
#include <iostream>

#include "vigra/multi_pointoperators.hxx"
#include "vigra/functorexpression.hxx"
#include "vigra/transformimage.hxx"

#include "cecog/shared_objects.hxx"
#include "cecog/inspectors.hxx"


namespace cecog
{

  template <class Point, class SrcIterator, class SrcAccessor>
  inline
  void drawLine(Point p1, Point p2,
                SrcIterator s, SrcAccessor src,
                typename SrcAccessor::value_type v,
                bool thick=false)
  {
    vigra::Diff2D ps, diff = p2 - p1;
    bool yLonger = false;
    int incVal, endVal;
    int shortLen = diff.y;
    int longLen = diff.x;

    if (abs(shortLen) > abs(longLen))
    {
      std::swap(shortLen, longLen);
      yLonger = true;
    }
    endVal = longLen;
    if (longLen < 0)
    {
      incVal = -1;
      longLen = -longLen;
    }
    else incVal = 1;
    int decInc;
    if (longLen == 0)
      decInc = 0;
    else
      decInc = (shortLen << 16) / longLen;
    if (yLonger)
    {
      for (int i=0, j=0; i!=endVal; i+=incVal, j+=decInc)
      {
        ps.x = p1.x + (j >> 16);
        ps.y = p1.y + i;
        src.set(v, s + ps);
        if (thick)
        {
          src.set(v, s + ps + vigra::Diff2D(1,0));
          src.set(v, s + ps + vigra::Diff2D(1,1));
          src.set(v, s + ps + vigra::Diff2D(0,1));
        }
      }
    } else
    {
      for (int i=0, j=0; i!=endVal; i+=incVal, j+=decInc)
      {
        ps.x = p1.x + i;
        ps.y = p1.y + (j >> 16);
        src.set(v, s + ps);
        if (thick)
        {
          src.set(v, s + ps + vigra::Diff2D(1,0));
          src.set(v, s + ps + vigra::Diff2D(1,1));
          src.set(v, s + ps + vigra::Diff2D(0,1));
        }
      }
    }
  }

  template <class Point, class SrcIterator, class SrcAccessor>
  inline
  void drawFilledCircle(Point p, int r,
                        SrcIterator si, SrcIterator send,
                        SrcAccessor src,
                        typename SrcAccessor::value_type v)
  {
      int w = send.x - si.x;
      int h = send.y - si.y;
      int r_sq = r * r;
      for (int y=-r; y <= r; ++y)
        for (int x=-r; x <= r; ++x)
        {
          Point p2 = p + vigra::Diff2D(x,y);
          if (x*x + y*y <= r_sq &&
              p2.x >= 0 && p2.x < w &&
              p2.y >= 0 && p2.y < h)
              src.set(v, si + p2);
        }
  }


  template <class SrcIterator, class SrcAccessor>
  inline
  void drawHVLine(SrcIterator s, SrcIterator send, SrcAccessor src,
                  typename SrcAccessor::value_type value,
                  bool thick=false)
  {
    for(; s != send; ++s)
    {
      src.set(value, s);
    }
  }


  template <class ImageIterator, class Accessor>
  inline
  void drawRectangle(ImageIterator upperleft, ImageIterator lowerright,
                     Accessor a, typename Accessor::value_type value,
                     bool thick=false)
  {
    int w = lowerright.x - upperleft.x;
    int h = lowerright.y - upperleft.y;

    ImageIterator ul = upperleft;
    for (int i=0; i<=1; i++)
    {
      if (i)
        ul.y = lowerright.y-1;
      drawHVLine(ul.rowIterator(), ul.rowIterator() + w, a, value, thick);
    }
    ul = upperleft;
    for (int i=0; i<=1; i++)
    {
      if (i)
        ul.x = lowerright.x-1;
      drawHVLine(ul.columnIterator(), ul.columnIterator() + h, a, value, thick);
    }
  }

  template <class SrcIterator, class SrcAccessor>
  inline
  void drawEllipse(int x, int y, int a, int b,
                   SrcIterator s, SrcAccessor src,
                   typename SrcAccessor::value_type v)
  {
    int lx = a;
    for(int i=0; i < b+1; i++)
    {
      int xx = int(sqrt((double)(a*a)*((b*b)-(i*i))) / b);
      drawLine(Point(x+xx,y+i), Point(lx+x+1,y+i), s, src, v);
      drawLine(Point(x+xx,y-i), Point(lx+x+1,y-i), s, src, v);
      drawLine(Point(x-xx,y+i), Point(-lx+x-1,y+i),s, src, v);
      drawLine(Point(x-xx,y-i), Point(-lx+x-1,y-i),s, src, v);
      lx = xx;
    }
  }


  template <class SrcIterator, class SrcAccessor,
            class DestIterator, class DestAccessor>
  inline
  void drawContour(SrcIterator si, SrcIterator send, SrcAccessor sa,
                   DestIterator di, DestAccessor da,
                   typename DestAccessor::value_type value,
                   bool quad=false)
  {
    SrcIterator xs(si);
    DestIterator xd(di);
    int w = send.x - si.x;
    int h = send.y - si.y;
    int x, y;
    BlockFunctorBase_NewSave<SrcIterator, SrcAccessor> functor(xs, sa, w, h, 8, 0);

    for (y=0; y < h; ++y, ++xd.y)
    {
      xd.x = di.x;
      for (x=0; x < w; ++x, ++xd.x)
        if (functor.hasLabelAround(x, y))
        {
          da.set(value, xd);
          if (quad)
          {
            static const vigra::Diff2D QUAD[] =
              {
                vigra::Diff2D(1,0),
                vigra::Diff2D(0,1),
                vigra::Diff2D(1,1),
              };
            for (int i=0; i<3; i++)
            {
              vigra::Diff2D p = vigra::Diff2D(x,y) + QUAD[i];
              if (p.x >= 0 && p.x < w &&
                  p.y >= 0 && p.y < h)
                da.set(value, xd + QUAD[i]);
            }
          }
        }
    }
  }

  template <class SrcImageIterator, class SrcAccessor,
            class DestImageIterator, class DestAccessor>
  inline
  void drawContour(vigra::triple<SrcImageIterator, SrcImageIterator, SrcAccessor> img1,
                   vigra::pair<DestImageIterator, DestAccessor> img2,
                   typename DestAccessor::value_type value,
                   bool quad=false)
  {
    drawContour(img1.first, img1.second, img1.third,
                img2.first, img2.second,
                value,
                quad);
  }


  template <class SrcIterator, class SrcAccessor,
            class DestIterator, class DestAccessor>
  inline
  void drawContourIfLabel(SrcIterator si, SrcIterator send, SrcAccessor sa,
                          DestIterator di, DestAccessor da,
                          typename SrcAccessor::value_type mask,
                          typename DestAccessor::value_type value,
                          bool quad=false)
  {
    SrcIterator xs(si);
    DestIterator xd(di);
    int w = send.x - si.x;
    int h = send.y - si.y;
    int x, y;
    BlockFunctorBase<SrcIterator, SrcAccessor> functor;

    for(y=0; y < h; ++y, ++xs.y, ++xd.y)
    {
      xs.x = si.x;
      xd.x = di.x;
      for(x=0; x < w; ++x, ++xs.x, ++xd.x)
        if (functor.is_border_fg(xs, sa, mask))
        {
          da.set(value, xd);
          if (quad)
          {
            da.set(value, xd + vigra::Diff2D(1,0));
            da.set(value, xd + vigra::Diff2D(0,1));
            da.set(value, xd + vigra::Diff2D(1,1));
          }
        }
    }
  }

  template <class SrcImageIterator, class SrcAccessor,
            class DestImageIterator, class DestAccessor>
  inline
  void drawContourIfLabel(vigra::triple<SrcImageIterator, SrcImageIterator, SrcAccessor> img1,
                          vigra::pair<DestImageIterator, DestAccessor> img2,
                          typename DestAccessor::value_type value,
                          typename SrcAccessor::value_type mask,
                          bool quad=false)
  {
    drawContourIfLabel(img1.first, img1.second, img1.third,
                       img2.first, img2.second,
                       value,
                       mask,
                       quad);
  }


  /**
   * transforms a whole BImage to BRGBImage and sets the greyvalues to
   * the given channels.
   * channels settings: 0 - gray, 1 - red, 2 - green, 4 - blue
   * and mixtures (AND): 3 - red+green, 5 - green+blue, etc...
   * alpha: perform a MAX-blending with values
   *        between 0.0 (transparent) and 1.0 (opaque)
   */
  template <class IMAGE_IN>
  inline
  vigra::BRGBImage mergeRGB(IMAGE_IN const & in,
                            vigra::BRGBImage out,
                            int channel,
                            float alpha=1.0)
  {
    typedef typename IMAGE_IN::value_type image_value_type;
    typename IMAGE_IN::const_iterator inIt = in.begin();
    vigra::BRGBImage::iterator outIt = out.begin();
    for(; inIt != in.end(); ++inIt, ++outIt)
    {
      // channel == 0 --> NO channel, do nothing
      // channel == 1 --> write to red channel a linear composition in and red.
      // channel == 2 --> write to green channel a linear composition in and green.
      // channel == 4 --> write to blue channel a linear composition in and blue.
      // channel == 7, all color channels are set to the image channel (->grey)
      // for all other channels, write mixtures
      vigra::BRGBImage::value_type &out = *outIt;
      image_value_type inp = image_value_type((*inIt) * alpha);
      if (channel & 1)
        out.setRed(std::max<image_value_type>(out.red(), inp));
      if (channel & 2)
        out.setGreen(std::max<image_value_type>(out.green(), inp));
      if (channel & 4)
        out.setBlue(std::max<image_value_type>(out.blue(), inp));
    }
    return out;
  }



  template <class SrcIterator, class SrcAccessor,
            class MaskIterator, class MaskAccessor,
            class DestIterator, class DestAccessor>
  void
  copyLineIfLabel(SrcIterator s,
                  SrcIterator send, SrcAccessor src,
                  MaskIterator m, MaskAccessor mask,
                  DestIterator d, DestAccessor dest,
                  typename MaskAccessor::value_type label)
  {
    for(; s != send; ++s, ++d, ++m)
      if(mask(m) == label)
        dest.set(src(s), d);
  }

  template <class SrcImageIterator, class SrcAccessor,
            class MaskImageIterator, class MaskAccessor,
            class DestImageIterator, class DestAccessor>
  void
  copyImageIfLabel(SrcImageIterator src_upperleft,
                   SrcImageIterator src_lowerright, SrcAccessor sa,
                   MaskImageIterator mask_upperleft, MaskAccessor ma,
                   DestImageIterator dest_upperleft, DestAccessor da,
                   typename MaskAccessor::value_type label)
  {
    int w = src_lowerright.x - src_upperleft.x;

    for(; src_upperleft.y<src_lowerright.y;
        ++src_upperleft.y, ++mask_upperleft.y, ++dest_upperleft.y)
    {
      copyLineIfLabel(src_upperleft.rowIterator(),
                      src_upperleft.rowIterator() + w, sa,
                      mask_upperleft.rowIterator(), ma,
                      dest_upperleft.rowIterator(), da,
                      label);
    }
  }

  template <class SrcImageIterator, class SrcAccessor,
            class MaskImageIterator, class MaskAccessor,
            class DestImageIterator, class DestAccessor>
  inline
  void
  copyImageIfLabel(vigra::triple<SrcImageIterator, SrcImageIterator,
                   SrcAccessor> src,
                   vigra::pair<MaskImageIterator, MaskAccessor> mask,
                   vigra::pair<DestImageIterator, DestAccessor> dest,
                   typename MaskAccessor::value_type label)
  {
    copyImageIfLabel(src.first, src.second, src.third,
                     mask.first, mask.second,
                     dest.first, dest.second,
                     label);
  }


  template <class SrcIterator, class SrcAccessor,
            class MaskIterator, class MaskAccessor,
            class DestIterator, class DestAccessor,
            class Functor>
  void
  transformLineIfLabel(SrcIterator s,
                       SrcIterator send, SrcAccessor src,
                       MaskIterator m, MaskAccessor mask,
                       DestIterator d, DestAccessor dest,
                       typename MaskAccessor::value_type label,
                       Functor const & f)
  {
    for(; s != send; ++s, ++d, ++m)
      if(mask(m) == label)
        dest.set(f(src(s)), d);
  }


  template <class SrcImageIterator, class SrcAccessor,
            class MaskImageIterator, class MaskAccessor,
            class DestImageIterator, class DestAccessor,
            class Functor>
  void
  transformImageIfLabel(SrcImageIterator src_upperleft,
                        SrcImageIterator src_lowerright, SrcAccessor sa,
                        MaskImageIterator mask_upperleft, MaskAccessor ma,
                        DestImageIterator dest_upperleft, DestAccessor da,
                        typename MaskAccessor::value_type label,
                        Functor const & f)
  {
    int w = src_lowerright.x - src_upperleft.x;

    for(; src_upperleft.y < src_lowerright.y;
        ++src_upperleft.y, ++mask_upperleft.y, ++dest_upperleft.y)
    {
      transformLineIfLabel(src_upperleft.rowIterator(),
                           src_upperleft.rowIterator() + w, sa,
                           mask_upperleft.rowIterator(), ma,
                           dest_upperleft.rowIterator(), da,
                           label, f);
    }
  }

  template <class SrcImageIterator, class SrcAccessor,
            class MaskImageIterator, class MaskAccessor,
            class DestImageIterator, class DestAccessor,
            class Functor>
  inline
  void
  transformImageIfLabel(vigra::triple<SrcImageIterator, SrcImageIterator,
                        SrcAccessor> src,
                        vigra::pair<MaskImageIterator, MaskAccessor> mask,
                        vigra::pair<DestImageIterator, DestAccessor> dest,
                        typename MaskAccessor::value_type label,
                        Functor const & f)
  {
    transformImageIfLabel(src.first, src.second, src.third,
                          mask.first, mask.second,
                          dest.first, dest.second,
                          label, f);
  }


  template <class SrcIterator, class SrcAccessor,
            class MaskIterator, class MaskAccessor,
            class Functor>
  void
  inspectLineIfLabel(SrcIterator s,
                     SrcIterator send, SrcAccessor src,
                     MaskIterator m, MaskAccessor mask,
                     typename MaskAccessor::value_type label,
                     Functor & f)
  {
    for(; s != send; ++s, ++m)
      if(mask(m) == label)
        f(src(s));
  }

  template <class ImageIterator, class Accessor,
            class MaskImageIterator, class MaskAccessor, class Functor>
  void
  inspectImageIfLabel(ImageIterator upperleft,
                      ImageIterator lowerright, Accessor a,
                      MaskImageIterator mask_upperleft, MaskAccessor ma,
                      typename MaskAccessor::value_type label,
                      Functor & f)
  {
    int w = lowerright.x - upperleft.x;

    for(; upperleft.y<lowerright.y; ++upperleft.y, ++mask_upperleft.y)
    {
      inspectLineIfLabel(upperleft.rowIterator(),
                         upperleft.rowIterator() + w, a,
                         mask_upperleft.rowIterator(), ma,
                         label, f);
    }
  }

  template <class ImageIterator, class Accessor,
            class MaskImageIterator, class MaskAccessor, class Functor>
  inline
  void
  inspectImageIfLabel(vigra::triple<ImageIterator, ImageIterator, Accessor>
                      img,
                      vigra::pair<MaskImageIterator, MaskAccessor> mask,
                      typename MaskAccessor::value_type label,
                      Functor & f)
  {
    inspectImageIfLabel(img.first, img.second, img.third,
                        mask.first, mask.second, label, f);
  }

  enum ProjectionType {MaxProjection, MinProjection, MeanProjection};

  template <class VALUETYPE>
  class MaxReduceFunctor
  {
    typedef VALUETYPE value_type;
    public:
      value_type operator()(value_type const &a, value_type const &b)
      {
        return std::max<value_type>(a, b);
      }
  };

  template <class VALUETYPE>
  class MinReduceFunctor
  {
    typedef VALUETYPE value_type;
    public:
      value_type operator()(value_type const &a, value_type const &b)
      {
        return std::min<value_type>(a, b);
      }
  };

  template <class SrcValueType>
  class HistogramEqualization
  {
  public:
    typedef SrcValueType argument_type;
    typedef SrcValueType result_type;
    typedef std::vector<double> Vector;

    HistogramEqualization(Vector const &probs, argument_type minV,
                          argument_type maxV)
    {
      this->minV = minV;
      this->maxV = maxV;
      this->diffV = maxV - minV;
      for (size_t i = 0; i < probs.size(); i++) {
        probsCum.push_back(probs[i]);
        if (i > 0)
          probsCum[i] += probsCum[i-1];
      }
    }

    result_type operator()(argument_type s) const
    {
      return probsCum[s] * diffV + minV;
    }

  private:
    Vector probsCum;
    argument_type minV, maxV, diffV;
  };

  template <class SrcValueType1, class SrcValueType2, class DestValueType>
  class ImageSubstract2
  {
  public:
    typedef SrcValueType1 argument_type1;
    typedef SrcValueType2 argument_type2;
    typedef DestValueType result_type;

    ImageSubstract2(result_type minV, result_type maxV)
      : minV(minV), maxV(maxV)
    {}

    result_type operator()(argument_type1 s1, argument_type2 s2) const
    {
      double res = (double)s1 - (double)s2;
      if (res > maxV)
        return maxV;
      else if (res < minV)
        return minV;
      else
        return vigra::NumericTraits<result_type>::fromRealPromote(res);
    }
  private:
    result_type minV, maxV;
  };

  template <class SrcValueType, class DestValueType>
  class ImageLinearTransform
  {
  public:
    typedef SrcValueType argument_type;
    typedef DestValueType result_type;

    ImageLinearTransform(argument_type srcMin, argument_type srcMax, result_type destMin, result_type destMax, result_type minV, result_type maxV)
      : minV(minV), maxV(maxV)
    {
      ratio = double(destMax - destMin) / double(srcMax - srcMin);
      offset = destMin / ratio - srcMin;
    }

    result_type operator()(argument_type s) const
    {
      double res = ratio * (s + offset);
      if (res > maxV)
        return maxV;
      else if (res < minV)
        return minV;
      else
        return vigra::NumericTraits<result_type>::fromRealPromote(res);
    }
  private:
    result_type minV, maxV;
    double offset, ratio;
    };

  template <class IMAGE>
  inline
  void
  projectImage(vigra::ArrayVector< IMAGE > &lstImages, IMAGE &imgOut, ProjectionType pType)
  {
    if (lstImages.size() > 0)
      {
        typedef typename IMAGE::value_type PixelType;
        int iWidth = lstImages[0].width();
        int iHeight = lstImages[0].height();
        int iSize = lstImages.size();
        typedef vigra::MultiArray<3, PixelType> ImageArray;
        ImageArray imgArray(typename ImageArray::difference_type(iWidth, iHeight, iSize));
        for (int i=0; i < iSize; i++)
          {
            vigra::MultiArrayView<2, PixelType> arrayView(imgArray.bindOuter(i));
            vigra::BasicImageView<PixelType> imgView = makeBasicImageView(arrayView);
            copyImage(srcImageRange(lstImages[i]), destImage(imgView));
          }

        ImageArray imgArrayProj(typename ImageArray::difference_type(iWidth, iHeight, 1));

        if (pType == MaxProjection)
          {
            vigra::ReduceFunctor<MaxReduceFunctor<PixelType>, PixelType>
              oMaxReduceFunctor(MaxReduceFunctor<PixelType>(), 0);
            vigra::transformMultiArray(srcMultiArrayRange(imgArray),
                                       destMultiArrayRange(imgArrayProj),
                                       oMaxReduceFunctor);
          }
        else if (pType == MinProjection)
          {
            vigra::ReduceFunctor<MinReduceFunctor<PixelType>, PixelType>
              oMaxReduceFunctor(MinReduceFunctor<PixelType>(), 0);
            vigra::transformMultiArray(srcMultiArrayRange(imgArray),
                                       destMultiArrayRange(imgArrayProj),
                                       oMaxReduceFunctor);
          }
        else if (pType == MeanProjection)
          {
            vigra::transformMultiArray(srcMultiArrayRange(imgArray),
                                       destMultiArrayRange(imgArrayProj),
                                       vigra::FindAverage<PixelType>());
          }

        vigra::MultiArrayView<2, PixelType> arrayView = imgArrayProj.bindOuter(0);
        vigra::BasicImageView<PixelType> imgViewProj = makeBasicImageView(arrayView);
        copyImage(srcImageRange(imgViewProj), destImage(imgOut));
      }
  }
}
#endif // CECOG_TRANSFORMS
