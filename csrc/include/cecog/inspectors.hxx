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


#ifndef CECOG_INSPECTORS
#define CECOG_INSPECTORS

#include <vector>
#include <list>

#include "vigra/numerictraits.hxx"

#include "cecog/math.hxx"
#include "cecog/fdiff2d.hxx"


namespace cecog
{

  static const vigra::Diff2D NEIGHBORS[] =
    {
      vigra::Diff2D(-1,0),  // left
      vigra::Diff2D(1,0),   // right
      vigra::Diff2D(0,-1),  // top
      vigra::Diff2D(0,1),   // bottom
      vigra::Diff2D(-1,-1), // topleft
      vigra::Diff2D(1,-1),  // topright
      vigra::Diff2D(-1,1),  // bottomleft
      vigra::Diff2D(1,1)    // bottomright
    };


  static const int N_LEFT = 0, N_RIGHT = 1, N_TOP = 2, N_BOTTOM = 3,
    N_TOPLEFT = 4, N_TOPRIGHT = 5, N_BOTTOMLEFT = 6, N_BOTTOMRIGHT = 7;



  struct GradientSquaredMagnitudeFunctor
  {
    float operator()(float const & g1, float const & g2) const
    {
      return g1 * g1 + g2 * g2;
    }

    float operator()(vigra::RGBValue<float> const & rg1, vigra::RGBValue<float> const & rg2) const
    {
      float g1 = rg1.squaredMagnitude();
      float g2 = rg2.squaredMagnitude();

      return g1 + g2;
    }
  };


  template <class SrcValueType, class DestValueType>
  class RGBChannelFunctor
  {
  public:
    typedef SrcValueType argument_type;
    typedef DestValueType result_type;

    RGBChannelFunctor(int channel=0) : channel(channel)
    {};

    result_type operator()(argument_type s) const
    {
      switch (channel)
      {
        case 0: return (result_type)s.red();
        case 1: return (result_type)s.green();
        case 2: return (result_type)s.blue();
      }
    }

  private:
    argument_type condition;
    result_type value;
    int channel;
  };



  /**
   * Functor to calculate the average and standard deviation of pixel values
   */
  template <class VALUETYPE>
  class FindStdDev
  {
  public:
    typedef VALUETYPE argument_type;
    typedef typename vigra::NumericTraits<VALUETYPE>::RealPromote result_type;

    FindStdDev()
      : count(0),
        sum(vigra::NumericTraits<result_type>::zero()),
        square_sum(vigra::NumericTraits<result_type>::zero())
    {};

    void reset()
    {
      count = 0;
      sum = vigra::NumericTraits<result_type>::zero();
      square_sum = vigra::NumericTraits<result_type>::zero();
    }

    inline
    void operator()(argument_type const & v)
    {
      sum += v;
      square_sum += v * v;
      ++count;
    }

    inline
    result_type average() const
    {
      return sum / result_type(count);
    }

    inline
    result_type stddev() const
    {
      return sqrt((square_sum - sum * sum / result_type(count)) / result_type(count-1));
    }

    inline
    result_type operator()() const
    {
      return stddev();
    }

  private:
    result_type sum, square_sum;
    unsigned long int count;
  };


  /**
   * Functor to calculate the object center (x,y) by averaging over pixel
   * x,y-coordinates
   */
  class FindAVGCenter
  {
  public:

    typedef vigra::Diff2D argument_type;
    typedef vigra::Diff2D result_type;

    unsigned sumx, sumy, count;

    FindAVGCenter()
      : sumx(0), sumy(0), count(0)
    {}

    void reset()
    {
      count = 0;
      sumx = 0;
      sumy = 0;
    }

    inline
    void operator()(argument_type const & coord)
    {
      sumx += coord.x;
      sumy += coord.y;
      count++;
    }

    inline
    void operator()(FindAVGCenter const & otherRegion)
    {
      count += otherRegion.count;
      sumx  += otherRegion.sumx;
      sumy  += otherRegion.sumy;
    }

    inline
    result_type operator()() const
    {
      return result_type(sumx / count, sumy / count);
    }
  };


  /**
   * Functor to calculate the object center (x,y) by averaging over pixel
   * x,y-coordinates weighted by the pixel gray level (subpixel resolution)
   */
  template <class VALUETYPE>
  class FindGravityCenter
  {
  public:

    typedef FDiff2D argument_type;
    typedef FDiff2D result_type;
    typedef VALUETYPE value_type;

    float sumx, sumy, count, cvalue;

    FindGravityCenter()
        : sumx(0), sumy(0), count(0), cvalue(0)
    {}

    void reset()
    {
      count  = 0;
      cvalue = 0;
      sumx   = 0;
      sumy   = 0;
    }

    void operator()(argument_type const & coord, value_type const & value)
    {
      sumx += value*coord.x;
      sumy += value*coord.y;
      count++;
      cvalue += value;
    }

    void operator()(FindGravityCenter const & otherRegion)
    {
      count  += otherRegion.count;
      cvalue += otherRegion.cvalue;
      sumx   += otherRegion.sumx;
      sumy   += otherRegion.sumy;
    }

    result_type operator()() const
    {
      return result_type(sumx / count / cvalue,
                         sumy / count / cvalue);
    }
  };


  /**
   * Functor to calculate the histogram of an image or region
   */
  template <class VALUETYPE>
  class FindHistogram
  {
  public:
    typedef VALUETYPE argument_type;
    typedef std::vector<unsigned int> result_type;

    FindHistogram(unsigned int const value_count)
        : count(0),
        value_count(value_count),
        histogram(value_count)
    {};

    void reset()
    {
      count = 0;
      histogram = result_type(value_count);
    }

    inline
    void operator()(argument_type const & v)
    {
      histogram[v]++;
      count++;
    }

    inline
    result_type operator()() const
    {
      return histogram;
    }

    inline
    result_type::value_type operator[](int idx) const
    {
      return histogram[idx];
    }

    inline
    unsigned int max()
    {
      unsigned int maxv = 0;
      result_type::iterator s = histogram.begin();
      for(; s != histogram.end(); ++s)
        maxv = std::max(maxv, *s);
      return maxv;
    }

    inline
    VALUETYPE argmax()
    {
      unsigned int maxv = 0;
      VALUETYPE maxi = 0;
      for(int i=0; i<value_count; ++i)
        if (histogram[i] > maxv)
        {
          maxv = histogram[i];
          maxi = i;
        }
      return maxi;
    }

    inline
    unsigned int size()
    {
      return value_count;
    }

    inline
    std::vector<double> probabilities()
    {
      std::vector<double> prob(value_count);
      for(int i=0; i<value_count; ++i)
        prob[i] = (double)histogram[i] / (double)count;
      return prob;
    }

  private:
    unsigned int count, value_count;
    result_type histogram;
  };


  /**
   * Applies a functor to the image, which takes as arguments:
   * Iterator, Accessor, x and y.
   * return value is the functor (and the stored values).
   * FIXME: Should be redesigned to VIGRA's design!
   */
  template <template <typename, typename> class Functor,
            class SrcIterator, class SrcAccessor>
  inline
  typename Functor<SrcIterator, SrcAccessor>::result_type
  blockInspector(SrcIterator const & upperleft,
                 SrcIterator const & lowerright,
                 SrcAccessor const & sa,
                 typename SrcAccessor::value_type const & label)
  {
    SrcIterator xs(upperleft);
    int w = lowerright.x - upperleft.x;
    int h = lowerright.y - upperleft.y;
    int x, y;
    Functor<SrcIterator, SrcAccessor> functor;

    for(y = 0; y != h; ++y, ++xs.y)
    {
      xs.x = upperleft.x;
      for(x=0; x != w; ++x, ++xs.x)
        functor(xs, sa, label, x, y);
    }
    return functor();
  }


  /**
   * Base class offering methods to check if the pixel is on the border (etc.)
   * FIXME: Should be redesigned to match VIGRA.
   */
  template <class SrcIterator, class SrcAccessor, int NEIGHBORHOOD=8>
  class BlockFunctorBase
  {
  public:
    typedef double result_type;
    typedef SrcIterator Iterator;
    typedef SrcAccessor Accessor;

    inline
    bool is_border(SrcIterator si, SrcAccessor sa,
                   typename SrcAccessor::value_type background=0)
    {
      bool border = false;
      if (NEIGHBORHOOD == 4)
      {
        if (sa(si) != background &&
            (sa(si, NEIGHBORS[N_TOP]) == background ||
             sa(si, NEIGHBORS[N_LEFT]) == background ||
             sa(si, NEIGHBORS[N_BOTTOM]) == background ||
             sa(si, NEIGHBORS[N_RIGHT]) == background))
          border = true;
      } else
      {
        if (sa(si) != background &&
            (sa(si, NEIGHBORS[N_TOP]) == background ||
             sa(si, NEIGHBORS[N_LEFT]) == background ||
             sa(si, NEIGHBORS[N_BOTTOM]) == background ||
             sa(si, NEIGHBORS[N_RIGHT]) == background ||
             sa(si, NEIGHBORS[N_TOPLEFT]) == background ||
             sa(si, NEIGHBORS[N_TOPRIGHT]) == background ||
             sa(si, NEIGHBORS[N_BOTTOMLEFT]) == background ||
             sa(si, NEIGHBORS[N_BOTTOMRIGHT]) == background))
          border = true;
      }
      return border;
    }

    inline
    bool is_border_fg(SrcIterator si, SrcAccessor sa,
                      typename SrcAccessor::value_type foreground=0)
    {
      bool border = false;
      if (NEIGHBORHOOD == 4)
      {
        if (sa(si) == foreground &&
            (sa(si, NEIGHBORS[N_TOP]) != foreground ||
             sa(si, NEIGHBORS[N_LEFT]) != foreground ||
             sa(si, NEIGHBORS[N_BOTTOM]) != foreground ||
             sa(si, NEIGHBORS[N_RIGHT]) != foreground))
          border = true;
      } else
      {
        if (sa(si) == foreground &&
            (sa(si, NEIGHBORS[N_TOP]) != foreground ||
             sa(si, NEIGHBORS[N_LEFT]) != foreground ||
             sa(si, NEIGHBORS[N_BOTTOM]) != foreground ||
             sa(si, NEIGHBORS[N_RIGHT]) != foreground ||
             sa(si, NEIGHBORS[N_TOPLEFT]) != foreground ||
             sa(si, NEIGHBORS[N_TOPRIGHT]) != foreground ||
             sa(si, NEIGHBORS[N_BOTTOMLEFT]) != foreground ||
             sa(si, NEIGHBORS[N_BOTTOMRIGHT]) != foreground))
          border = true;
      }
      return border;
    }

    inline
    bool has_neighbor_bg(SrcIterator si, SrcAccessor sa,
                         typename SrcAccessor::value_type background=0)
    {
      bool neighbor = false;
      if (NEIGHBORHOOD == 4)
      {
        if (!(sa(si, NEIGHBORS[N_TOP]) == background &&
              sa(si, NEIGHBORS[N_LEFT]) == background &&
              sa(si, NEIGHBORS[N_BOTTOM]) == background &&
              sa(si, NEIGHBORS[N_RIGHT]) == background))
          neighbor = true;
      } else
      {
        if (!(sa(si, NEIGHBORS[N_TOP]) == background &&
              sa(si, NEIGHBORS[N_LEFT]) == background &&
              sa(si, NEIGHBORS[N_BOTTOM]) == background &&
              sa(si, NEIGHBORS[N_RIGHT]) == background &&
              sa(si, NEIGHBORS[N_TOPLEFT]) == background &&
              sa(si, NEIGHBORS[N_TOPRIGHT]) == background &&
              sa(si, NEIGHBORS[N_BOTTOMLEFT]) == background &&
              sa(si, NEIGHBORS[N_BOTTOMRIGHT]) == background))
          neighbor = true;
      }
      return neighbor;
    }

    inline
    bool has_neighbor_fg(SrcIterator si, SrcAccessor sa,
                         typename SrcAccessor::value_type foreground=0)
    {
      bool neighbor = false;
      if (NEIGHBORHOOD == 4)
      {
        if (sa(si, NEIGHBORS[N_TOP]) == foreground ||
            sa(si, NEIGHBORS[N_LEFT]) == foreground ||
            sa(si, NEIGHBORS[N_BOTTOM]) == foreground ||
            sa(si, NEIGHBORS[N_RIGHT]) == foreground)
          neighbor = true;
      } else
      {
        if (sa(si, NEIGHBORS[N_TOP]) == foreground ||
            sa(si, NEIGHBORS[N_LEFT]) == foreground ||
            sa(si, NEIGHBORS[N_BOTTOM]) == foreground ||
            sa(si, NEIGHBORS[N_RIGHT]) == foreground ||
            sa(si, NEIGHBORS[N_TOPLEFT]) == foreground ||
            sa(si, NEIGHBORS[N_TOPRIGHT]) == foreground ||
            sa(si, NEIGHBORS[N_BOTTOMLEFT]) == foreground ||
            sa(si, NEIGHBORS[N_BOTTOMRIGHT]) == foreground)
          neighbor = true;
      }
      return neighbor;
    }

    inline
    bool has_one_label_neighbor(SrcIterator si, SrcAccessor sa,
                                typename SrcAccessor::value_type &label,
                                typename SrcAccessor::value_type bg=0)
    {
      bool neighbor = false;
      bool has_candidate = false;
      typename SrcAccessor::value_type candidate = bg;

      for (int i=0; i<NEIGHBORHOOD; ++i)
      {
        typename SrcAccessor::value_type nb = sa(si, NEIGHBORS[i]);
        if (nb != bg)
        {
          if (candidate == bg)
          {
            candidate = nb;
            neighbor = true;
          }
          else if (nb != candidate)
          {
            neighbor = false;
            break;
          }
        }
      }
      if (neighbor)
        label = candidate;
      return neighbor;
    }

    result_type operator()()
    {
      return vigra::NumericTraits<result_type>::zero();
    }

  };

  template <class SrcIterator, class SrcAccessor>
  class BlockFunctorBase_NewSave
  {
  public:

    BlockFunctorBase_NewSave(SrcIterator si, SrcAccessor sa, int width, int height,
                             int nbh=8,
                             typename SrcAccessor::value_type label=0)
      : si(si), sa(sa), width(width), height(height), nbh(nbh), label(label)
    {}

    inline
    bool hasLabelAround(int x, int y)
    {
      bool found = false;
      if (sa(si, vigra::Diff2D(x,y)) != label)
        for (int i=0; i < nbh; ++i)
        {
          vigra::Diff2D p(vigra::Diff2D(x,y) + NEIGHBORS[i]);
          if (p.x >= 0 && p.x < width && p.y >= 0 && p.y < height && sa(si, p) == label)
          {
            found = true;
            break;
          }
        }
      return found;
    }

    inline
    bool hasNonLabelAround(int x, int y)
    {
      bool found = false;
      //printf("(%d,%d) -> %d\n", x, y, sa(si, vigra::Diff2D(x,y)));
      if (sa(si, vigra::Diff2D(x,y)) == label)
        for (int i=0; i < nbh; ++i)
        {
          vigra::Diff2D p(vigra::Diff2D(x,y) + NEIGHBORS[i]);
          if (p.x >= 0 && p.x < width && p.y >= 0 && p.y < height && sa(si, p) != label)
          {
            found = true;
            break;
          }
        }
      return found;
    }

  private:
    SrcIterator si;
    SrcAccessor sa;
    typename SrcAccessor::value_type label;
    int width, height, nbh;
  };

  /**
   * Find the start point of the crack contour
   * (the first point of the region border whose left neighbor is background)
   * FIXME: see VIGRA's neighborhood methods
   */
  template <class SrcIterator, class SrcAccessor>
  inline
  vigra::Diff2D findCrackStart(SrcIterator const & upperleft,
                               SrcIterator const & lowerright,
                               SrcAccessor const & sa,
                               typename SrcAccessor::value_type const & label)
  {
    SrcIterator xs(upperleft);
    int w = lowerright.x - upperleft.x;
    int h = lowerright.y - upperleft.y;
    int x, y;
    bool found = false;
    vigra::Diff2D start(0,0);

    for (int x=0; x < w && !found; ++x, ++xs.x)
    {
      xs.y = upperleft.y;
      for (int y=0; y < h && !found; ++y, ++xs.y)
      {
        if (sa(xs) == label)
        {
            start = vigra::Diff2D(x,y);
            found = true;
            break;
        }
      }
    }
    return start;
  }

//  template <class SrcIterator, class SrcAccessor>
//  inline
//  bool findCrackStartOld(SrcIterator const & upperleft,
//                         SrcIterator const & lowerright,
//                         SrcAccessor const & sa,
//                         typename SrcAccessor::value_type const & label,
//                         vigra::Diff2D & start)
//  {
//    SrcIterator xs(upperleft);
//    int w = lowerright.x - upperleft.x;
//    int h = lowerright.y - upperleft.y;
//    int x, y;
//    bool found = false;
////    BlockFunctorBase_NewSave<SrcIterator, SrcAccessor> functor(xs, sa, w, h, 8, label);
//    BlockFunctorBase<SrcIterator, SrcAccessor> functor;
//
//    //xs.y += 1;
//    //if (h < 1 or w < 1)
//    //  return false;
//
//
//    for (int y=0; y < h; ++y, ++xs.y)
//    {
//      xs.x = upperleft.x;
//      for (int x=0; x < w; ++x, ++xs.x)
//        if (functor.is_border_fg(xs, sa, label))
//        {
//          start = vigra::Diff2D(x,y);
//          found = true;
//          break;
//        }
//      if (found)
//        break;
//    }
//    return found;
//  }

  template <class SrcIterator, class SrcAccessor>
  class BlockPerimeter : public BlockFunctorBase<SrcIterator, SrcAccessor>
  {
  public:

    typedef double result_type;
    typedef BlockFunctorBase<SrcIterator, SrcAccessor> base_type;

    BlockPerimeter()
        : perimeter(0.0)
    {};

    void reset()
    {
      perimeter = 0.0;
    }

    inline
    void operator()(SrcIterator si, SrcAccessor sa, typename SrcAccessor::value_type label, int x=0, int y=0)
    {
      if (this->is_border_fg(si, sa, label))
        perimeter++;
    }

    result_type operator()()
    {
      return perimeter;
    }

  private:
    result_type perimeter;
  };



  // calculate Perimeter calculates the perimeter of an object identified by
  // its label.
  // object pixels on the image border are supposed to be object border pixels.
  // upperleft, lowerright, sa refer to the label image
  // roi_ul, roi_lr define the roi containing the object with the label <label>
  // image_w, image_h are the image width and height.
  // nbh indicates the neighborhood; possible values are 8 and 4, default is 8.
  template <class SrcIterator, class SrcAccessor>
  inline
  unsigned int
  calculatePerimeter(SrcIterator upperleft,
                     SrcIterator lowerright,
                     SrcAccessor sa,
                     vigra::Diff2D roi_ul,
                     vigra::Diff2D roi_lr,
                     int label,
                     int image_w, int image_h,
                     int nbh=8)
  {
    SrcIterator xs(upperleft + roi_ul);
    //SrcIterator
    unsigned int perimeter = 0;

    for(int y = roi_ul.y; y != roi_lr.y; ++y, ++xs.y)
    {
      xs.x = upperleft.x + roi_ul.x;
      for(int x=roi_ul.x; x != roi_lr.x; ++x, ++xs.x)
      {
        // if xs is not an object pixel, it can be skipped.
        if (sa(xs) != label)
          continue;

        // if xs is on the image border, it is considered to be an object border pixel.
        if (x <=0 || x >= image_w-1 || y <= 0 || y >= image_h-1) {
          perimeter++;
          continue;
        }

        // if xs is not on the image border it is an object border pixel if
        // it has a background pixel in its neighborhood (default 8).
        for (int i=0; i<nbh; i++){
          if(sa(xs, NEIGHBORS[i]) != label) {
            perimeter++;
            break;
          }
        }
      } // end of x loop
    } // end of y loop
    return perimeter;
  }


  typedef vigra::tuple4<double, vigra::Diff2D, double, vigra::Diff2D> axes_4tuple;

  template <class SrcIterator, class SrcAccessor>
  inline
  axes_4tuple
  calculateAxes(SrcIterator const & upperleft,
                SrcIterator const & lowerright,
                SrcAccessor const & sa,
                vigra::Diff2D const & center,
                typename SrcAccessor::value_type const & label)
  {
    static const vigra::Diff2D neighbors[] =
    {
      vigra::Diff2D(-1,0),  // left
      vigra::Diff2D(1,0),   // right
      vigra::Diff2D(0,-1),  // top
      vigra::Diff2D(0,1)    // bottom
    };
    static const int left = 0, right = 1, top = 2, bottom = 3;

    SrcIterator xs(upperleft);
    double max_d = 0;
    double min_d = 1000000;

    vigra::Diff2D max_p, min_p;

    int w = lowerright.x - upperleft.x;
    int h = lowerright.y - upperleft.y;
    //int x0 = upperleft.x, y0 = upperleft.y;
    int x, y;

    for (y = 0; y < h; ++y, ++xs.y)
    {
      xs.x = upperleft.x;
      for (x = 0; x < w; ++x, ++xs.x)
        if (sa(xs) == label &&
            !((y > 0 && sa(xs, neighbors[top]) == label) &&
              (x > 0 && sa(xs, neighbors[left]) == label) &&
              (y < h-1 && sa(xs, neighbors[bottom]) == label) &&
              (x < w-1 && sa(xs, neighbors[right]) == label)))
        {
          vigra::Diff2D p(x, y);
          double d = (p - center).squaredMagnitude();
          if (d > max_d)
          {
            max_d = d;
            max_p = p;
          } else
            if (d < min_d)
            {
              min_d = d;
              min_p = p;
            }
        }
    }
    return axes_4tuple(sqrt(max_d), max_p, sqrt(min_d), min_p);
  }


  template <class SrcIterator, class SrcAccessor>
  inline
  void averageCenterDistance(SrcIterator const & upperleft,
                               SrcIterator const & lowerright,
                               SrcAccessor const & sa,
                               vigra::Diff2D const & center,
                               typename SrcAccessor::value_type const & label,
                               double & average,
                               double & stddev)
  {
    static const vigra::Diff2D neighbors[] = {
          vigra::Diff2D(-1,0),  // left
          vigra::Diff2D(1,0),   // right
          vigra::Diff2D(0,-1),  // top
          vigra::Diff2D(0,1)    // bottom
        };
    static const int left = 0, right = 1, top = 2, bottom = 3;

    SrcIterator xs(upperleft);

    int w = lowerright.x - upperleft.x;
    int h = lowerright.y - upperleft.y;
    int x, y;
    unsigned count = 0;
    double sumd = 0.0, ssumd = 0.0;

    for(y = 0; y != h; ++y, ++xs.y)
    {
      xs.x = upperleft.x;
      for (x = 0; x != w; ++x, ++xs.x)
        if (sa(xs) == label &&
            !((y > 0 && sa(xs, neighbors[top]) == label) &&
              (x > 0 && sa(xs, neighbors[left]) == label) &&
              (y < h-1 && sa(xs, neighbors[bottom]) == label) &&
              (x < w-1 && sa(xs, neighbors[right]) == label)))
        {
          vigra::Diff2D p(x, y);
          double d = (p - center).magnitude();
          sumd += d;
          ssumd += d * d;
          count++;
        }
    }
    average = sumd / count;
    stddev = sqrt((ssumd - sumd * sumd / double(count)) / double(count-1));
  }

  template <class SrcIterator, class SrcAccessor>
  inline
  unsigned int
  //typename SrcAccessor::value_type
  findBestThreshold(SrcIterator upperleft,
                    SrcIterator lowerright,
                    SrcAccessor sa)
  {
    static const vigra::Diff2D neighbors[] = {
          vigra::Diff2D(-1,0),  // left
          vigra::Diff2D(1,0),   // right
          vigra::Diff2D(0,-1),  // top
          vigra::Diff2D(0,1)    // bottom
        };
    static const int left = 0, right = 1, top = 2, bottom = 3;

    typedef typename SrcAccessor::value_type value_type;

    unsigned long e_sum = 0, ep_sum = 0;

    upperleft.y++;
    SrcIterator xs(upperleft);
    int w = lowerright.x - upperleft.x - 2;
    int h = lowerright.y - upperleft.y - 2;
    int x, y;

    for(y = 0; y != h; ++y, ++xs.y)
    {
      xs.x = upperleft.x + 1;
      for(x=0; x != w; ++x, ++xs.x)
      {
        unsigned int vertical = abs(sa(xs, neighbors[top]) -
                                    sa(xs, neighbors[bottom]));
        unsigned int horizontal = abs(sa(xs, neighbors[left]) -
                                      sa(xs, neighbors[right]));
        //unsigned int e = std::max(horizontal, vertical);
        unsigned long e = vertical*vertical + horizontal*horizontal;
        ep_sum += e * sa(xs);
        e_sum += e;

      }
    }
    return ep_sum / e_sum;
  }



}

#endif // CECOG_INSPECTORS
