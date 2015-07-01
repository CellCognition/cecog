/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held, Thomas Walter
// $Date$
// $Rev$
// $URL$


#ifndef CECOG_FEATURES
#define CECOG_FEATURES

#include <iostream>
#include <map>
#include <vector>
#include <string>
#include <algorithm>

#include <boost/numeric/ublas/symmetric.hpp>
#include <boost/numeric/ublas/io.hpp>

#include "vigra/transformimage.hxx"
#include "vigra/labelimage.hxx"
#include "vigra/inspectimage.hxx"
#include "vigra/basicimage.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/functorexpression.hxx"

#include "cecog/shared_objects.hxx"
#include "cecog/math.hxx"
#include "cecog/transforms.hxx"
#include "cecog/inspectors.hxx"
#include "cecog/polygon.hxx"
#include "cecog/utilities.hxx"

#include "cecog/basic/functors.hxx"
#include "cecog/basic/borderset.hxx"

#include "cecog/morpho/structuring_elements.hxx"
#include "cecog/morpho/label.hxx"
#include "cecog/morpho/dynamic.hxx"
#include "cecog/morpho/granulometries.hxx"

namespace cecog
{
  using namespace boost::numeric::ublas;
  using namespace vigra::functor;

  inline
  double feature_circularity(double perimeter, double roisize)
  {
    return perimeter /  (2.0 * sqrt(M_PI * roisize));
  }

  inline
  double feature_irregularity(double centerdist, double roisize)
  {
    return (1.0 + SQRT_PI * centerdist) / sqrt(roisize) - 1.0;
  }



  template <class SIMAGE, class MIMAGE>
  class TextureFeatureBase
  {
  public:
    typedef typename SIMAGE::Iterator SrcIterator;
    typedef typename SIMAGE::Accessor SrcAccessor;
    typedef typename MIMAGE::Iterator MaskIterator;
    typedef typename MIMAGE::Accessor MaskAccessor;
    typedef typename SrcAccessor::value_type value_type;
    typedef typename MaskAccessor::value_type mask_type;

    TextureFeatureBase(SIMAGE const & simg, MIMAGE const & mimg,
                       ROIObject const & o,
                       unsigned label,
                       unsigned greylevels,
                       value_type max_value = 0)
      : simg_roi(o.roi.width, o.roi.height),
        mimg_roi(o.roi.width, o.roi.height),
        greylevels(greylevels)
    {
      // crop the object from the image (label area only!)
      copyImageIfLabel(simg.upperLeft()+o.roi.upperLeft,
                      simg.upperLeft()+o.roi.lowerRight,
                      simg.accessor(),
                      mimg.upperLeft()+o.roi.upperLeft,
                      mimg.accessor(),
                      simg_roi.upperLeft(),
                      simg_roi.accessor(),
                      label);
      copyImageIfLabel(mimg.upperLeft()+o.roi.upperLeft,
                      mimg.upperLeft()+o.roi.lowerRight,
                      mimg.accessor(),
                      mimg.upperLeft()+o.roi.upperLeft,
                      mimg.accessor(),
                      mimg_roi.upperLeft(),
                      mimg_roi.accessor(),
                      label);

      // FIXME: this can be implemented more intuitively

      // maxv and minv are the maximal/minimal LUT-INPUT values
      if (max_value == 0)
      {
        // if max_value == 0, maxv and minv are calculated from the image.
        // in this case, we have a linear contrast stretching as normalization
          vigra::FindMinMax<value_type> minmax;
          inspectImageIf(srcImageRange(simg_roi), maskImage(mimg_roi), minmax);
          maxv = minmax.max;
          minv = minmax.min;
      } else
      {
        // in this case maxv is set by the user, minv is set to 0.
        // if max_value is greylevels - 1, nothing happens
        // if max_value is smaller than greylevels - 1,
        // the contrast, there is a stretching about greylevels - 1 - maxv
          maxv = max_value;
          minv = 0;
      }

      //if (!(minv == 0 and (greylevels - 1) == maxv))
      transformImage(srcImageRange(simg_roi),
                     destImage(simg_roi),
                     vigra::linearIntensityTransform(
                       (greylevels - 1) / double(maxv - minv), -minv)
                     );
    }

  protected:
    SIMAGE simg_roi;        // source image
    MIMAGE mimg_roi;        // mask image
    value_type minv, maxv;  // min and max
    unsigned greylevels;    // number of greylevels
  };



  template <class SIMAGE, class MIMAGE>
  class Levelset : public TextureFeatureBase<SIMAGE, MIMAGE>
  {

  public:
    typedef TextureFeatureBase<SIMAGE, MIMAGE> BaseType;
    typedef vigra::IImage IIMAGE;
    typedef IIMAGE::value_type label_type;
    typedef std::vector<double> d_vector;
    typedef FeatureMap::iterator value_iterator;

    Levelset(SIMAGE const & simg, MIMAGE const & mimg,
             ROIObject const & o,
             unsigned label,
             unsigned greylevels = 32,
             typename BaseType::value_type max_value = 0)
      : BaseType(simg, mimg, o, label, greylevels, max_value),
        lower(greylevels/2),
        obj_center(o.center),
        obj_roisize(o.roisize)
    {
      d_vector IRGL[2] = {d_vector(greylevels),
                          d_vector(greylevels)};
      d_vector DISP[2] = {d_vector(greylevels),
                          d_vector(greylevels)};
      d_vector INTERIA[2] = {d_vector(greylevels),
                             d_vector(greylevels)};
      d_vector TAREA[2] = {d_vector(greylevels),
                           d_vector(greylevels)};
      d_vector CAREA[2] = {d_vector(greylevels),
                           d_vector(greylevels)};
      d_vector NCA[2] = {d_vector(greylevels),
                         d_vector(greylevels)};

      double sqrt_roisize = sqrt(obj_roisize);

      for (unsigned t = 1; t < greylevels-1; t++) {
        unsigned count[2];
        MIMAGE level(o.roi.width, o.roi.height);
        IIMAGE label[2] = {IIMAGE(o.roi.width, o.roi.height),
                           IIMAGE(o.roi.width, o.roi.height)};

        // threshold image to given value t
        transformImageIf(srcImageRange(simg_roi),
                         maskImage(mimg_roi),
                         destImage(level),
                         vigra::Threshold<
                         typename BaseType::value_type,
                         typename BaseType::mask_type>
                         (t, greylevels-1, 0, greylevels-1));

        // without change: the regions above t
        count[1] =
          labelImageWithBackground(srcImageRange(level),
                                   destImage(label[1]),
                                   false, 0);

        // transform greylevels to label regions below t
        // STEP1: convert all '0' pixels to 'lower'
        transformImageIf(srcImageRange(level),
                         maskImage(mimg_roi),
                         destImage(level),
                         ifThenElse(Arg1() == Param(0),
                                    Param(lower),
                                    Arg1())
                         );
        // STEP2: convert all NOT 'lower' pixels to '0'
        transformImageIf(srcImageRange(level),
                         maskImage(mimg_roi),
                         destImage(level),
                         ifThenElse(Arg1() != Param(lower),
                                    Param(0),
                                    Arg1())
                         );
        // STEP3: Connected Component Analysis on pixels NOT '0'
        count[0] =
          labelImageWithBackground(srcImageRange(level),
                                   destImage(label[0]),
                                   false, 0);

        // gravity center of each region
        typedef vigra::ArrayOfRegionStatistics<FindAVGCenter>
            ars_center;
        ars_center center[2] = {ars_center(count[0]),
                                ars_center(count[1])};

        typedef vigra::ArrayOfRegionStatistics<
        vigra::FindROISize<label_type> > ars_roisize;
        ars_roisize roisize[2] = {ars_roisize(count[0]),
                                  ars_roisize(count[1])};

        typedef vigra::ArrayOfRegionStatistics<
        vigra::FindBoundingRectangle> ars_boundary;
        ars_boundary boundary[2] = {ars_boundary(count[0]),
                                    ars_boundary(count[1])};

        for (int i = 0; i < 2; ++i)
        {
          inspectTwoImages(srcIterRange(vigra::Diff2D(0,0),
                                        vigra::Diff2D(0,0) +
                                        label[i].size()),
                           srcImage(label[i]), center[i]);
          inspectTwoImages(srcImageRange(label[i]),
                           srcImage(label[i]), roisize[i]);
          inspectTwoImages(srcIterRange(
                               vigra::Diff2D(0,0),
                               vigra::Diff2D(0,0) + label[i].size()),
                           srcImage(label[i]), boundary[i]);
        }

        // IRGL -- Irregularity
        // NCA -- Normalised Number of Connected Regions
        // DISP -- Average Clump Displacement
        // INTERIA -- Average Clump Interia
        // CAREA -- Average Clump Area
        // TAREA -- Total Clump Area
        for (unsigned i = 0; i < 2; ++i) {
          double sum_rsize = 0.0, sum_irgl_rsize = 0.0;
          double dsum = 0.0, isum = 0.0;
          for (unsigned j = 1; j <= count[i]; ++j) {
            double rs = roisize[i][j]();
            if (rs > 1.0) {
              vigra::Diff2D c = center[i][j]() -
                boundary[i][j].upperLeft;

              axes_4tuple tuple =
                calculateAxes(label[i].upperLeft() +
                              boundary[i][j].upperLeft,
                              label[i].upperLeft() +
                              boundary[i][j].lowerRight,
                              label[i].accessor(), c, j);
              double dist_max = tuple.first;
              sum_irgl_rsize +=
                ((1 + SQRT_PI * dist_max)
                 / sqrt(rs) - 1) * rs;

              double d = (SQRT_PI * (obj_center - c).magnitude() /
                          sqrt_roisize);
              dsum += d;
              isum += d * rs;
              sum_rsize += rs;
            }
          }
          IRGL[i][t] = sum_irgl_rsize / (sum_rsize + 0.001);
          DISP[i][t] = dsum / count[i];
          INTERIA[i][t] = isum / count[i];
          CAREA[i][t] = sum_rsize / count[i];
          TAREA[i][t] = sum_rsize / obj_roisize;
          NCA[i][t] = count[i] / obj_roisize;
        }
      }
      // calculate final statistics for "0" and "1" regions
      for (unsigned i = 0; i < 2; ++i) {
        char dStr[10];
        sprintf(dStr, "ls%d_", i);
        statistics(values, DISP[i],    std::string(dStr) + "DISP");
        statistics(values, INTERIA[i], std::string(dStr) + "INTERIA");
        statistics(values, CAREA[i],   std::string(dStr) + "CAREA");
        statistics(values, TAREA[i],   std::string(dStr) + "TAREA");
        statistics(values, IRGL[i],    std::string(dStr) + "IRGL");
        statistics(values, NCA[i],     std::string(dStr) + "NCA");
      }
    }

    inline
    void statistics(FeatureMap &values, d_vector vec, std::string prefix)
    {
      double max_value = 0.0, v_sum = 0.0, v_wsum = 0.0;
      for (unsigned t = 0; t < vec.size(); ++t)
      {
        v_sum += vec[t];
        v_wsum += t * vec[t];
        max_value = std::max(max_value, vec[t]);
      }
      double avg_value = v_sum / (vec.size() - 1);
      double sample_mean = v_wsum / v_sum;

      double t_sum = 0.0;
      for (unsigned t = 0; t < vec.size(); ++t)
        t_sum += sqr((t - sample_mean)) * vec[t];
      double sample_sd = sqrt(t_sum / v_sum);

      values[std::string(prefix)+"_max_value"] = max_value;
      values[std::string(prefix)+"_avg_value"] = avg_value;
      values[std::string(prefix)+"_sample_mean"] = sample_mean;
      values[std::string(prefix)+"_sample_sd"] = sample_sd;
    }

    FeatureMap values;

  private:
    std::vector<IIMAGE> label_stack;
    unsigned lower;
    using BaseType::simg_roi;
    using BaseType::mimg_roi;
    vigra::Diff2D obj_center;
    double obj_roisize;
  };



  template <class SIMAGE, class MIMAGE>
  class Haralick : public TextureFeatureBase<SIMAGE, MIMAGE>
  {
  public:

    typedef TextureFeatureBase<SIMAGE, MIMAGE> BaseType;

    Haralick(SIMAGE const & simg, MIMAGE const & mimg,
             ROIObject const & o,
             unsigned label,
             unsigned greylevels = 32,
             typename BaseType::value_type max_value = 0,
             unsigned distance = 1)
      : BaseType(simg, mimg, o, label, greylevels, max_value),
        matrix(greylevels),
        count(0),
        distance(distance),
        size(greylevels)
    {
      matrix.clear();
      buildMatrix();
    }

    /**
     * Angular Second Moment (Energy)
     */
    inline
    double ASM()
    {
      double res = 0.0;
      for (unsigned j = 0; j < size; ++j)
      {
        res += sqr(matrix(j,j));
        for (unsigned i = j+1; i < size; ++i)
          res += 2 * sqr(matrix(j,i));
      }
      return res;
    }

    /**
     * Inverse Difference Moment (Homogeneity}
     */
    inline
    double IDM()
    {
      double res = 0.0;
      for (unsigned j = 0; j < size; ++j) {
        res += matrix(j,j);
        for (unsigned i = j+1; i < size; ++i)
          res += 2 * (matrix(j,i) / (1 + sqr((i - j))));
      }
      return res;
    }

    /**
     * Entropy
     */
    inline
    double ENT()
    {
      double res = 0.0;
      double shift = 0.0001;
      for (unsigned j = 0; j < size; ++j) {
        res += matrix(j,j) * log(matrix(j,j) + shift);
        for (unsigned i = j+1; i < size; ++i)
          res += 2 * matrix(j,i) * log(matrix(j,i) + shift);
      }
      return (-1) * res;
    }

    /**
     * Variance
     */
    inline
    double VAR()
    {
      double res = 0.0;
      for (unsigned j = 0; j < size; ++j) {
        res += matrix(j,j) * sqr((j - average));
        for (unsigned i = j+1; i < size; ++i)
          res += 2 * matrix(i,j) * sqr((j - average));
      }
      return res;
    }

    /**
     * Contrast (Interia)
     */
    inline
    double CON()
    {
      double res = 0.0;
      for (unsigned j = 0;  j < size; ++j)
        for (unsigned i = j+1; i < size; ++i)
          res += 2 * matrix(i,j) * sqr((i - j));
      return res;
    }


    // Correlation
    inline
    double COR()
    {
      double res = 0.0;
      for (unsigned j = 0; j < size; ++j) {
        res += sqr((j - average)) * matrix(j,j) / sqr(variance);
        for (unsigned i = j+1; i < size; ++i) {
          res += (2*(i - average)*(j - average)*matrix(i,j)/sqr(variance));
        }
      }
      return res;
    }

    /**
     * Prominence
     */
    inline
    double PRO()
    {
      double res = 0.0;
      for (unsigned j = 0; j < size; ++j) {
        res += pow((2 * j - 2 * average),4) * matrix(j,j);
        for (unsigned i = j+1; i < size; ++i) {
          res += 2 * pow((i + j - 2 * average),4) * matrix(i,j);
        }
      }
      return res;
    }

    /**
     * Shade
     */
    inline
    double SHA()
    {
      double res = 0.0;
      for (unsigned j = 0; j < size; ++j)
      {
        res += pow((2 * j - 2 * average),3) * matrix(j,j);
        for (unsigned i = j+1; i < size; ++i)
          res += 2 * pow((i + j - 2 * average),3) * matrix(i,j);
      }
      return res;
    }

    /**
     * Sum Average
     */
    inline
    double SAV()
    {
      double res = 0.0;
      for (unsigned n=2; n <= 2*size; ++n)
        res += n * condAddSum(n);
      return res;
    }

    /**
     * Sum Variance
     */
    inline
    double SVA()
    {
      double res = 0.0;
      double sav = SAV();
      for (unsigned n = 2; n <= 2*size; ++n)
        res += sqr((n - sav)) * condAddSum(n);
      return res;
    }

    /**
     * Sum Entropy
     */
    inline
    double SET()
    {
      double res = 0.0;
      double shift = 0.0001;
      for (unsigned n=2; n <= 2*size; ++n)
      {
        double cas = condAddSum(n) + shift;
        res += cas * log(cas);
      }
      return (-1) * res;
    }

    /**
     * Difference Average
     */
    inline
    double DAV()
    {
      double res = 0.0;
      for (unsigned n = 0; n < size; ++n)
        res += n * condSubSum(n);
      return res;
    }

    /**
     * Coefficient of Variation
     */
    inline
    double COV()
    {
      return variance / average;
    }

    inline
    double avg()
    {
      return average;
    }

    inline
    double var()
    {
      return variance;
    }

  private:

    /**
     * sum over all matrix elements where (i,j), where i+j == n
     */
    inline
    double condAddSum(unsigned n)
    {
      double s = 0.0;
      for (unsigned j=0; j<size; ++j)
      {
        if (2*j == n)
          s += matrix(j,j);
        for (unsigned i=j+1; i<size; ++i)
          if (i + j == n)
            s += 2 * matrix(i,j);
      }
      return s;
    }

    /**
     * sum over all matrix elements where (i,j), where i-j == n
     */
    inline
    double condSubSum(unsigned n)
    {
      double s = (n == 0) ? matrix(0,0) : 0.0;
      for (unsigned j = 0; j < size; ++j)
        for (unsigned i = j+1; i < size; ++i)
          if (abs(i - j) == n)
            s += 2 * matrix(i,j);
      return s;
    }

    /**
     * Build a Grey Level Co-occurence Matrix (GLCM)
     * - only pixel-pairs within the given region and mask values != 0 are used
     * - the matrix is rotation invariant! (uses average over all four directions)
     */
    inline
    void buildMatrix()
    {
      unsigned d = distance;
      const vigra::Diff2D neighbors[] =
        {
          vigra::Diff2D(+d,0),  // right         -> horizontal
          vigra::Diff2D(0,+d),  // bottom        -> vertical
          vigra::Diff2D(+d,+d), // bottom-right  -> antidiagonal
          vigra::Diff2D(-d,+d)  // bottom-left   -> diagonal
        };
      static const int directions = 4;

      typename BaseType::SrcIterator  s(simg_roi.upperLeft());
      typename BaseType::SrcIterator  send(simg_roi.lowerRight());
      typename BaseType::MaskIterator m(mimg_roi.upperLeft());
      typename BaseType::SrcIterator  si(s);
      typename BaseType::MaskIterator mi(m);
      typename BaseType::SrcAccessor  const & src  = simg_roi.accessor();
      typename BaseType::MaskAccessor const & mask = mimg_roi.accessor();

      int w = send.x - s.x;
      int h = send.y - s.y;
      int x, y;

      for(y=0; y < h; ++y, ++si.y, ++mi.y)
        for (x=0, si.x=s.x, mi.x=m.x; x < w; ++x, ++si.x, ++mi.x)
          if (mask(mi))
            for (int i=0; i < directions; ++i)
            {
              int xn = x + neighbors[i].x;
              int yn = y + neighbors[i].y;

              // is pair-pixel still in region?
              if (xn >= 0 && xn < w &&
                  yn >= 0 && yn < h)
                if (mask(mi, neighbors[i]))
                {
                  typename BaseType::value_type v1 =
                    src(si);
                  typename BaseType::value_type v2 =
                    src(si, neighbors[i]);

                  // count twice on main-diagonal
                  if (v1 != v2)
                    matrix(v1, v2)++;
                  else
                    matrix(v1, v2) += 2;
                  count ++;
                }
            }
      count *= 2;

      // normalize
      for (unsigned j = 0; j < size; ++j)
        for (unsigned i = j; i<size; ++i)
          matrix(i,j) /= double(count);

      // calculate the mean (average)
      average = 0.0;
      for (unsigned j = 0; j < size; ++j) {
        average += j*matrix(j,j);
        for (unsigned i = j+1; i < size; ++i)
          average += 2*j*matrix(i,j);
      }

      // calculate the variance
      variance = 0.0;
      for (unsigned j = 0; j < size; ++j) {
        double var_i = matrix(j,j);
        for (unsigned  i = j+1; i < size; ++i)
          var_i += 2 * matrix(i,j);
        variance += var_i * sqr((j - average));
      }
    }

    symmetric_matrix<double, upper> matrix;
    double average, variance;
    unsigned count, distance, size;

    using BaseType::simg_roi;
    using BaseType::mimg_roi;
  };



  template <class SIMAGE, class MIMAGE>
  class Normbase : public TextureFeatureBase<SIMAGE, MIMAGE>
  {
  public:
    typedef TextureFeatureBase<SIMAGE, MIMAGE> BaseType;

    Normbase(SIMAGE const & simg, MIMAGE const & mimg,
             ROIObject const & o,
             unsigned label,
             unsigned greylevels = 256,
             typename BaseType::value_type max_value = 0)
      : BaseType(simg, mimg, o, label, greylevels, max_value),
        center(o.center)
    {};

    inline
    double stddev()
    {
      FindStdDev<typename BaseType::value_type> f;
      inspectImageIf(srcImageRange(simg_roi), maskImage(mimg_roi), f);
      return (double)f();
    }

    inline
    double avg()
    {
      vigra::FindAverage<typename BaseType::value_type> f;
      inspectImageIf(srcImageRange(simg_roi), maskImage(mimg_roi), f);
      return (double)f();
    }

    inline
    double wavg()
    {
      int w = simg_roi.lowerRight().x - simg_roi.upperLeft().x;
      int h = simg_roi.lowerRight().y - simg_roi.upperLeft().y;
      int x, y;

      typename BaseType::SrcIterator  s(simg_roi.upperLeft());
      typename BaseType::MaskIterator m(mimg_roi.upperLeft());
      typename BaseType::SrcIterator  si(s);
      typename BaseType::MaskIterator mi(m);
      typename BaseType::SrcAccessor  const & src = simg_roi.accessor();
      typename BaseType::MaskAccessor const & mask = mimg_roi.accessor();

      double sum = 0.0;
      unsigned count = 0;
      for(y=0; y < h; ++y, ++si.y, ++mi.y)
        for (x=0, si.x=s.x, mi.x=m.x; x < w; ++x, ++si.x, ++mi.x)
          if (mask(mi))
          {
            double d = (vigra::Diff2D(x,y) - center).squaredMagnitude();
            sum += d * src(si);
            count++;
          }
      return sum / count;
    }

    inline
    double wiavg()
    {
      int w = simg_roi.lowerRight().x - simg_roi.upperLeft().x;
      int h = simg_roi.lowerRight().y - simg_roi.upperLeft().y;
      int x, y;

      typename BaseType::SrcIterator  s(simg_roi.upperLeft());
      typename BaseType::MaskIterator m(mimg_roi.upperLeft());
      typename BaseType::SrcIterator  si(s);
      typename BaseType::MaskIterator mi(m);
      typename BaseType::SrcAccessor  const & src = simg_roi.accessor();
      typename BaseType::MaskAccessor const & mask = mimg_roi.accessor();

      double sum = 0.0;
      unsigned count = 0;
      for(y=0; y < h; ++y, ++si.y, ++mi.y)
        for (x=0, si.x=s.x, mi.x=m.x; x < w; ++x, ++si.x, ++mi.x)
          if (mask(mi))
          {
            double d = (vigra::Diff2D(x,y) - center).squaredMagnitude();
            sum += src(si) / (d + 1);
            count++;
          }
      return sum / count;
    }

    inline
    double wdist()
    {
      int w = simg_roi.lowerRight().x - simg_roi.upperLeft().x;
      int h = simg_roi.lowerRight().y - simg_roi.upperLeft().y;
      int x, y;

      typename BaseType::SrcIterator  s(simg_roi.upperLeft());
      typename BaseType::MaskIterator m(mimg_roi.upperLeft());
      typename BaseType::SrcIterator  si(s);
      typename BaseType::MaskIterator mi(m);
      typename BaseType::MaskAccessor const & mask = mimg_roi.accessor();

      double sum = 0.0;
      unsigned count = 0;
      for(y=0; y < h; ++y, ++si.y, ++mi.y)
        for (x=0, si.x=s.x, mi.x=m.x; x < w; ++x, ++si.x, ++mi.x)
          if (mask(mi))
          {
            double d = (vigra::Diff2D(x,y) - center).squaredMagnitude();
            sum += d;
            count++;
          }
      return sum / count;
    }

  private:
    vigra::Diff2D center;
    using BaseType::simg_roi;
    using BaseType::mimg_roi;
  };

    // CONVEX HULL
    template <class LIMAGE, class BIMAGE>
    class ConvexHull
    {
    public:
        typedef typename std::vector<unsigned> UnsignedVector;

        typedef typename LIMAGE::Iterator LabIterator;
        typedef typename LIMAGE::Accessor LabAccessor;
        typedef typename LabAccessor::value_type lab_type;

        typedef typename BIMAGE::Iterator BinIterator;
        typedef typename BIMAGE::Accessor BinAccessor;
        typedef typename BIMAGE::value_type value_type;

        typedef typename morpho::neighborhood2D::ITERATORTYPE neighbor_iterator;

        ConvexHull(LIMAGE & labin,
                   ROIObject const & o, lab_type label)
            : borderSize(1),
              imgSize(o.roi.width + 2 * borderSize, o.roi.height + 2 * borderSize),
              imBinRoi_(imgSize),
              imConvexHull_(imgSize),
              imDiff_(imgSize),
              imLabel_(imgSize),
              center_(o.center),
              areaCell_(o.roisize),
              nb(morpho::WITHOUTCENTER8, vigra::Diff2D(imgSize)),
              objId_(label)
        {
          const vigra::Point2D ul(o.roi.upperLeft);
          const vigra::Point2D lr(o.roi.lowerRight);
          vigra::Rect2D rec(ul, lr);

            vigra::Diff2D borderOffset(borderSize, borderSize);

            // first, we crop the object from the image.
            vigra::transformImage(labin.upperLeft() + o.roi.upperLeft,
                             labin.upperLeft() + o.roi.lowerRight,
                             labin.accessor(),
                             imBinRoi_.upperLeft() + borderOffset,
                             imBinRoi_.accessor(),
                             vigra::Threshold<lab_type, value_type>(label, label, 0, 255));

            vigra::Diff2D temp(imBinRoi_.lowerRight() - imBinRoi_.upperLeft());

            // calculate the convex hull
            ImConvexHull(srcImageRange(imBinRoi_), destImage(imConvexHull_), 255, nb);

            // difference of the convex hull
            ImCompare(imConvexHull_, imBinRoi_, imDiff_, 0, 255, IsEqual<value_type, value_type>());

            // labeling
            numberOfConnectedComponents_ = morpho::ImLabel(imDiff_, imLabel_, nb);

        }

        void ExportConvexHull(unsigned id, std::string filename)
        {
            using namespace cecog::morpho;

            //std::string fullFilename = "/home/twalter/images/output/" +
            //                           itos(id, 3) + filename + ".tif";
            //vigra::ImageExportInfo exportInfo(fullFilename.c_str());
            vigra::ImageExportInfo exportInfo(filename.c_str());
            vigra::exportImage(imConvexHull_.upperLeft(),
                               imConvexHull_.lowerRight(),
                               imConvexHull_.accessor(),
                               exportInfo);

        }

        void CalculateFeatures(ROIObject & o)
        {
            perimeterCell_ = o.features["perimeter"];

            // preliminaries
            std::string prefix = "ch";
            // attention: the label=0 is for the background
            for(unsigned i = 0; i <= numberOfConnectedComponents_; ++i)
              areaContainer_.push_back(0);

            double acd = 0.0;
            unsigned numberOfLargeConnectedComponents = 0;

            std::vector<double> maxVal(3);

            if(numberOfConnectedComponents_ > 0)
            {
                // area for connected components
                areaDiff_ = CalculateAreaConnectedComponents_();
                areaConvexHull_ = areaCell_ + areaDiff_;

                //areaMean_ = (double)areaDiff_/(double)numberOfConnectedComponents_;
                CalculateDistributionMoments_();

                perimeter_ = CalculatePerimeter_();

                // calculation of the centers
                vigra::ArrayOfRegionStatistics<FindAVGCenter> centers(numberOfConnectedComponents_);
                inspectTwoImages(srcIterRange(vigra::Diff2D(0,0), vigra::Diff2D(0,0) + imLabel_.size()),
                                 srcImage(imLabel_), centers);

                // average clump displacement: with weight of the area
                for(unsigned i = 1; i <= numberOfConnectedComponents_; ++i) {
                    acd += diffDistance(centers[i](), o.center) * areaContainer_[i];
                }
                acd *= SQRT_PI/(sqrt(areaCell_) * ( (double)numberOfConnectedComponents_ * areaDiff_));

                for(unsigned i = 1; i <= numberOfConnectedComponents_; ++i) {
                  if(areaContainer_[i] > areaSignificanceThresh_)
                    numberOfLargeConnectedComponents++;
                }

                std::sort(areaContainer_.begin(), areaContainer_.end());

                for(unsigned i = 1; i < 4; ++i) {
                  if(areaContainer_.size() >= i)
                    maxVal[i-1] = (double)(*(areaContainer_.end() - i)) / areaCell_ ;
                  else
                    maxVal[i-1] = 0.0;
                }
            }
            else
            {
              // area for connected components
              areaDiff_ = 0.0;
              areaConvexHull_ = areaCell_ + areaDiff_;

              perimeter_ = perimeterCell_;
              areaMean_ = 0.0;
              areaVariance_ = 0.0;
              areaSkewness_ = 0.0;
              areaKurtosis_ = 0.0;
              acd = 0.0;
              maxVal[0] = 0.0;
              maxVal[1] = 0.0;
              maxVal[2] = 0.0;
            }

            // assignment of features
            o.features[prefix + "_thresh_cc"] = (double)numberOfLargeConnectedComponents;
            o.features[prefix + "_area_ratio"] = areaCell_ / areaConvexHull_ ;
            o.features[prefix + "_rugosity"] = perimeter_ / perimeterCell_;

            o.features[prefix + "_max_val_0"] = maxVal[0];
            o.features[prefix + "_max_val_1"] = maxVal[1];
            o.features[prefix + "_max_val_2"] = maxVal[2];

            o.features[prefix + "_acd"] = acd;

            o.features[prefix + "_cc"] = (double)areaContainerClean_.size();
            o.features[prefix + "_mean_area"] = areaMean_;
            o.features[prefix + "_variance_area"] = areaVariance_;

            // I believe that skewness and kurtosis are not very informative,
            // as many cc does not have any particular meaning.

            //o.features[prefix + "_skewness_area"] = areaSkewness_;
            //o.features[prefix + "_kurtosis_area"] = areaKurtosis_;
        }

    private:

        inline double CalculatePerimeter_()
        {
            unsigned perimeter = 0;

            BinIterator srcUpperLeft(imConvexHull_.upperLeft());
            BinIterator srcLowerRight(imConvexHull_.lowerRight());
            //BinIterator srcUpperLeft(imBinRoi_.upperLeft());
            //BinIterator srcLowerRight(imBinRoi_.lowerRight());

            BinAccessor srca;

            BinIterator origin(srcUpperLeft);

            for(; srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y)
            {
               BinIterator scurrent(srcUpperLeft);
               for(;scurrent.x < srcLowerRight.x; ++scurrent.x)
               {

                   // we do not check the border condition ...
                   // this requires an image with a 1 pixel margin
                   if (srca(scurrent) > 0)
                   {
                       for(neighbor_iterator iter = nb.begin();
                           iter != nb.end(); ++iter)
                       {
                           if(srca(scurrent, *iter) == 0)
                           {
                               perimeter++;
                               break;
                           }
                       }
                   }
               }  // end of x loop
            } // end of y -loop

            return (double)perimeter;
        }


        // claculates the area of the connected components
        // the result is stored in areaContainer_
        unsigned CalculateAreaConnectedComponents_()
        {
            unsigned area = 0;

            LabIterator srcUpperLeft(imLabel_.upperLeft());
            LabIterator srcLowerRight(imLabel_.lowerRight());
            LabAccessor srca;

            for(; srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y)
            {
               LabIterator scurrent(srcUpperLeft);
               for(;scurrent.x < srcLowerRight.x; ++scurrent.x)
               {
                if(srca(scurrent) > 0)
                {
                    ++(areaContainer_[srca(scurrent)]);
                }
               }
            }

            for(UnsignedVector::iterator iter = areaContainer_.begin() + 1;
                iter != areaContainer_.end();
                ++iter)
            {
                area += *iter;
                if(*iter > 1)
                    areaContainerClean_.push_back(*iter);
            }

            return area;
        }

        void CalculateDistributionMoments_()
        {
            areaMean_ = 0.0;
            areaVariance_ = 0.0;
            areaSkewness_ = 0.0;
            areaKurtosis_ = 0.0;
            double n = (double)areaContainerClean_.size();

            if(n==0.0)
            {
                areaMean_ = 0.0;
                areaVariance_ = 0.0;
                areaSkewness_ = 0.0;
                areaKurtosis_ = 0.0;
                return;
            }

            for(UnsignedVector::iterator iter = areaContainerClean_.begin();
                iter != areaContainerClean_.end();
                ++iter)
            {
                areaMean_ += *iter;
            }
            areaMean_ = areaMean_ / n;

            if(n == 1.0)
            {
                areaVariance_ = 0.0;
                areaSkewness_ = 0.0;
                areaKurtosis_ = 0.0;
                return;
            }

            for(UnsignedVector::iterator iter = areaContainerClean_.begin();
                iter != areaContainerClean_.end();
                ++iter)
            {
                 double temp = (*iter - areaMean_) * (*iter - areaMean_);
                 areaVariance_ += temp;
                 temp *= (*iter - areaMean_);
                 areaSkewness_ += temp;
                 temp *= (*iter - areaMean_);
                 areaKurtosis_ += temp;
            }
            if(areaVariance_ == 0)
            {
                areaSkewness_ = 0;
                areaKurtosis_ = 0;
                return;
            }

            areaSkewness_ = sqrt(n) * areaSkewness_ / pow(areaVariance_, 1.5);
            areaKurtosis_ = n * areaKurtosis_ / (areaVariance_ * areaVariance_) - 3.0;
            areaVariance_ = areaVariance_/ n ;
        }

      const static unsigned areaSignificanceThresh_ = 16;
      const unsigned borderSize;
      vigra::Diff2D imgSize;
      BIMAGE imBinRoi_;
      BIMAGE imConvexHull_;
      BIMAGE imDiff_;
      LIMAGE imLabel_;
      vigra::Diff2D center_;
      double areaCell_;
      morpho::neighborhood2D nb;
      lab_type objId_;

      UnsignedVector areaContainerClean_;
      UnsignedVector areaContainer_;
      double areaConvexHull_;
      double areaDiff_;
      double areaMean_;
      double areaVariance_;
      double areaSkewness_;
      double areaKurtosis_;
      double perimeter_, perimeterCell_;
      unsigned numberOfConnectedComponents_;
    };


    // Dynamic Features
    template <class SIMAGE, class LIMAGE>
    class DynamicFeatures
    {
    public:

        typedef typename LIMAGE::Iterator LabIterator;
        typedef typename LIMAGE::Accessor LabAccessor;
        typedef typename LabAccessor::value_type lab_type;

        typedef typename SIMAGE::Iterator SrcIterator;
        typedef typename SIMAGE::Accessor SrcAccessor;
        typedef typename SIMAGE::value_type value_type;

        typedef typename std::vector<value_type> DynamicsVector;
        typedef typename DynamicsVector::iterator iterator_type;

        typedef typename morpho::neighborhood2D::ITERATORTYPE neighbor_iterator;

        DynamicFeatures(SIMAGE &imin, LIMAGE &labin,
                        ROIObject const & o, lab_type label,
                        int minOrMax = 0,
                        value_type dynThresh = 10,
                        std::string prefix = "dyn_minima_",
                        unsigned borderSize = 0)
            : borderSize_(borderSize),
              imgSize_(o.roi.width + 2 * borderSize, o.roi.height + 2 * borderSize),
              imSrcRoi_(imgSize_),
              nb_(morpho::WITHOUTCENTER8, vigra::Diff2D(imgSize_)),
              objId_(label),
              dynThresh_(dynThresh),
              prefix_(prefix),
              dynMean_(0),
              dynVariance_(0),
              dynSkewness_(0),
              dynKurtosis_(0),
              dynMaxVal_(0),
              dynLowCount_(0),
              dynHighCount_(0),
              NB_HIGH_VALUES_(3),
              calcMaximumValues__(false)
        {

            vigra::Diff2D borderOffset(borderSize_, borderSize_);

            if(minOrMax == 0)
            {
                copyImageIfLabel(imin.upperLeft() + o.roi.upperLeft,
                             imin.upperLeft() + o.roi.lowerRight,
                             imin.accessor(),
                             labin.upperLeft() + o.roi.upperLeft,
                             labin.accessor(),
                             imSrcRoi_.upperLeft() + borderOffset,
                             imSrcRoi_.accessor(),
                             objId_);
            }
            else
            {
                transformImageIfLabel(imin.upperLeft() + o.roi.upperLeft,
                                  imin.upperLeft() + o.roi.lowerRight,
                                  imin.accessor(),
                                  labin.upperLeft() + o.roi.upperLeft,
                                  labin.accessor(),
                                  imSrcRoi_.upperLeft() + borderOffset,
                                  imSrcRoi_.accessor(),
                                  objId_,
                                  vigra::linearIntensityTransform(-1, -255) );
                //morpho::ImBorderSet(vigra::destImageRange(imSrcRoi_), borderSize_, 255);
            };

            DynamicsVector dummy;
            // old: ImDynMinima(srcImageRange(imSrcRoi_), dynVec_, nb_);
            ImDynMinima(imSrcRoi_.upperLeft() + borderOffset,
                        imSrcRoi_.lowerRight() - borderOffset,
                        imSrcRoi_.accessor(),
                        labin.upperLeft() + o.roi.upperLeft,
                        labin.accessor(),
                        dynVec_, dummy, nb_, objId_);

            dynVec_.erase(dynVec_.begin());

            dynLength_ = dynVec_.size();

        }

        void CalculateFeatures(ROIObject & o)
        {

            CalculateMean_();
            CalculateNumberOfHighDynamics_();
            CalculateHighDynamicValues_();

            for(unsigned i = 0; i < NB_HIGH_VALUES_; ++i)
            {
                std::string featureName = prefix_ + itos(i, 0);
                o.features[featureName] = maxVal[i];
            }
            o.features[prefix_ + "_mean"] = dynMean_;
            //o.features[prefix_ + "_var"] = dynVariance_;
            //o.features[prefix_ + "_skew"] = dynSkewness_;
            //o.features[prefix_ + "_kurt"] = dynKurtosis_;
            o.features[prefix_ + "_number_high"] = dynHighCount_;
            o.features[prefix_ + "_number"] = (double)dynLength_;


        }

        void CalcMaximumValues()
        {
            dynMaxVal_ = 0;

            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                if(*iter > dynMaxVal_)
                    dynMaxVal_ = *iter;
            }
            calcMaximumValues__ = true;

        }

        void EraseMaximalValues()
        {
            if(!calcMaximumValues__)
                CalcMaximumValues();

            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                if(*iter == dynMaxVal_)
                {
                    dynVec_.erase(iter);
                    break;
                }
            }

            dynLength_ = dynVec_.size();
        }



    protected:

        void CalculateCentralMoments_()
        {

            double n = (double)dynVec_.size();
            if(n==0.0)
            {
                dynMean_ = 0.0;
                dynVariance_ = 0.0;
                dynSkewness_ = 0.0;
                dynKurtosis_ = 0.0;
                return;
            }

            // mean
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
                dynMean_ += *iter;
            dynMean_ = dynMean_ / (double)dynVec_.size();

            if(n == 1)
            {
                dynVariance_ = 0.0;
                dynSkewness_ = 0.0;
                dynKurtosis_ = 0.0;
                return;
            }

            // central moments
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                int temp = (*iter - dynMean_) * (*iter - dynMean_);
                dynVariance_ += temp;
                dynSkewness_ += (temp * (*iter - dynMean_));
                dynKurtosis_ += (temp * temp);
            }
            if(dynVariance_ == 0)
            {
                dynSkewness_ = 0.0;
                dynKurtosis_ = 0.0;
                return;
            }
            dynSkewness_ = sqrt(n) * dynSkewness_ / pow(dynVariance_, 1.5);
            dynKurtosis_ = n * dynKurtosis_ / ( dynVariance_ * dynVariance_) ;
            dynVariance_ = dynVariance_ / n;

        }

        void CalculateMoments_()
        {

            double n = (double)dynVec_.size();
            dynMean_ = 0.0;
            dynVariance_ = 0.0;
            dynSkewness_ = 0.0;
            dynKurtosis_ = 0.0;

            if(n==0.0)
                return;

            // mean
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                int temp = *iter;
                dynMean_ += temp;
                temp *= (*iter);
                dynVariance_ += temp;
                temp *= (*iter);
                dynSkewness_ += temp;
                temp *= (*iter);
                dynKurtosis_ += temp;
            }

            dynMean_ = dynMean_ / (double)dynVec_.size();

            if(n == 1)
            {
                dynVariance_ = 0.0;
                dynSkewness_ = 0.0;
                dynKurtosis_ = 0.0;
                return;
            }

            if(dynVariance_ == 0)
            {
                dynSkewness_ = 0.0;
                dynKurtosis_ = 0.0;
                return;
            }
            dynSkewness_ = sqrt(n) * dynSkewness_ / pow(dynVariance_, 1.5);
            dynKurtosis_ = n * dynKurtosis_ / ( dynVariance_ * dynVariance_) ;
            dynVariance_ = dynVariance_ / n;

        }

        void CalculateMeanAndVar_()
        {

            double n = (double)dynVec_.size();

            dynMean_ = 0.0;
            dynVariance_ = 0.0;

            if(n==0.0)
                return;

            // mean
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                int temp = *iter;
                dynMean_ += temp;
                temp *= (*iter);
                dynVariance_ += temp;
            }

            dynMean_ = dynMean_ / (double)dynVec_.size();

            if(n == 1)
            {
                dynVariance_ = 0.0;
                return;
            }
            dynVariance_ = dynVariance_ / (n - 1);
            return;
        }

        void CalculateMean_()
        {
            double n = (double)dynVec_.size();
            dynMean_ = 0.0;

            if(n==0.0)
                return;

            // mean
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
                dynMean_ += (*iter);

            dynMean_ = dynMean_ / n;
        }

        void CalculateNumberOfLowDynamics_()
        {
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                if(*iter < dynThresh_)
                    dynLowCount_++;
            }
        }

        void CalculateNumberOfHighDynamics_()
        {
            for(iterator_type iter = dynVec_.begin();
                iter != dynVec_.end(); ++iter)
            {
                if(*iter >= dynThresh_)
                    dynHighCount_++;
            }
        }

        void CalculateHighDynamicValues_()
        {
            std::sort(dynVec_.begin(), dynVec_.end());

            for(unsigned i = 1; i <= NB_HIGH_VALUES_; ++i) {
                if(dynVec_.size() >= i)
                  maxVal.push_back((double)(*(dynVec_.end() - i)) );
                else
                  maxVal.push_back(0.0);
            }
        }

      unsigned borderSize_;
      vigra::Diff2D imgSize_;
      SIMAGE imSrcRoi_;
      morpho::neighborhood2D nb_;
      lab_type objId_;
      value_type dynThresh_;
      std::string prefix_;
      double dynMean_;
      double dynVariance_;
      double dynSkewness_;
      double dynKurtosis_;
      value_type dynMaxVal_;
      unsigned dynLowCount_;
      unsigned dynHighCount_;
      const unsigned NB_HIGH_VALUES_;
      bool calcMaximumValues__;

      std::vector<double> maxVal;
      DynamicsVector dynVec_;
      unsigned dynLength_;
    };

    template <class SIMAGE, class LIMAGE>
    class Granulometry
    {

    public:

        typedef typename LIMAGE::Iterator LabIterator;
        typedef typename LIMAGE::Accessor LabAccessor;
        typedef typename LabAccessor::value_type lab_type;

        typedef typename SIMAGE::Iterator SrcIterator;
        typedef typename SIMAGE::Accessor SrcAccessor;
        typedef typename SIMAGE::value_type value_type;

        typedef typename std::vector<unsigned> se_size_vec;
        typedef typename std::vector<double> result_vec;

        Granulometry(SIMAGE &imin, LIMAGE &labin,
                     ROIObject const & o, lab_type label,
                     se_size_vec & seSizeVec,
                     std::string prefix = "granulometry",
                     unsigned operatorFlag = 0)
            : borderSize_((unsigned)*(seSizeVec.end() - 1) + 1),
              imgSize_(o.roi.width + 2 * (*(seSizeVec.end() - 1) + 1), o.roi.height + 2 * (*(seSizeVec.end() - 1) + 1)),
              imSrcRoi_(imgSize_),
              objId_(label),
              operatorFlag_(operatorFlag),
              prefix_(prefix)
        {

            vigra::Diff2D borderOffset(borderSize_, borderSize_);

            copyImageIfLabel(imin.upperLeft() + o.roi.upperLeft,
                             imin.upperLeft() + o.roi.lowerRight,
                             imin.accessor(),
                             labin.upperLeft() + o.roi.upperLeft,
                             labin.accessor(),
                             imSrcRoi_.upperLeft() + borderOffset,
                             imSrcRoi_.accessor(),
                             objId_);
             seSizeVec_ = seSizeVec;

        }

        void CalculateFeatures(ROIObject & o)
        {
            if(operatorFlag_ == 0)
                morpho::ImOpenGranulometry(imSrcRoi_, seSizeVec_, areaVec_, volVec_, objId_);
            else
                morpho::ImCloseGranulometry(imSrcRoi_, seSizeVec_, areaVec_, volVec_, objId_);

            o.features[prefix_ + "_area_" + itos(seSizeVec_[0], 0)] = areaVec_[0];
            o.features[prefix_ + "_volume_" + itos(seSizeVec_[0], 0)] = volVec_[0];

            for(se_size_vec::size_type i = 1; i != seSizeVec_.size(); ++i)
            {
                o.features[prefix_ + "_area_" + itos(seSizeVec_[i], 0)] = areaVec_[i] - areaVec_[i-1] ;
                o.features[prefix_ + "_volume_" + itos(seSizeVec_[i], 0)] = volVec_[i] - volVec_[i-1] ;
            }
        }


    protected:
      unsigned borderSize_;
      vigra::Diff2D imgSize_;
      SIMAGE imSrcRoi_;
      unsigned objId_;
      unsigned operatorFlag_;
      std::string prefix_;
      se_size_vec seSizeVec_;
      result_vec areaVec_;
      result_vec volVec_;

    };

    template <class SIMAGE, class LIMAGE>
    class SpotFeatures
    {

    public:

        typedef typename LIMAGE::Iterator LabIterator;
        typedef typename LIMAGE::Accessor LabAccessor;
        typedef typename LabAccessor::value_type lab_type;

        typedef typename SIMAGE::Iterator SrcIterator;
        typedef typename SIMAGE::Accessor SrcAccessor;
        typedef typename SIMAGE::value_type value_type;

        typedef typename std::vector<double> result_vec;

        SpotFeatures(SIMAGE &imin, LIMAGE &labin,
                     ROIObject const & o, lab_type label,
                     unsigned diameter,
                     value_type threshold,
                     bool debug = false,
                     std::string debug_folder = "",
                     std::string debug_prefix = "",
                     std::string prefix = "spotfeature")
            : diam_(diameter),
              thresh_(threshold),
              borderSize_(1),
              imgSize_(o.roi.width + 2, o.roi.height + 2),
              imSrcRoi_(imgSize_),
              imDiamOpen_(imgSize_),
              imTemp_(imgSize_),
              imThresh_(imgSize_),
              imLabSpots_(imgSize_),
              objId_(label),
              prefix_(prefix),
              debug_(debug),
              debug_folder_(debug_folder),
              debug_prefix_(debug_prefix),
              nb_(morpho::WITHOUTCENTER8, vigra::Diff2D(imgSize_))
        {

            vigra::Diff2D borderOffset(borderSize_, borderSize_);

            copyImageIfLabel(imin.upperLeft() + o.roi.upperLeft,
                             imin.upperLeft() + o.roi.lowerRight,
                             imin.accessor(),
                             labin.upperLeft() + o.roi.upperLeft,
                             labin.accessor(),
                             imSrcRoi_.upperLeft() + borderOffset,
                             imSrcRoi_.accessor(),
                             objId_);
        }

        void CalculateFeatures(ROIObject & o)
        {
          // diameter opening
          morpho::ImDiameterOpen(imSrcRoi_, imDiamOpen_, diam_, nb_);

          // difference
          vigra::combineTwoImages(srcImageRange(imSrcRoi_),
                                  srcImage(imDiamOpen_),
                                  destImage(imTemp_),
                                  std::minus<value_type>());

          // threshold image
          vigra::transformImage(srcImageRange(imTemp_),
                                destImage(imThresh_),
                                ifThenElse(Arg1() >= Param(thresh_), Param(255), Param(0)));

          // label --> gives also the number of spots
          // 3rd argument: eight-neighborhood, 4th argument: value to be ignored (no label)
          unsigned count = labelImageWithBackground(srcImageRange(imThresh_),
                                                    destImage(imLabSpots_),
                                                    false, 0);

          // average intensities of the spots.
          vigra::ArrayOfRegionStatistics<vigra::FindAverageAndVariance<value_type> > average(count);
          //vigra::FindAverageAndVariance<value_type> average;
          vigra::inspectTwoImages(srcImageRange(imTemp_), srcImage(imLabSpots_), average);

          // average intensity
          double average_intensity = 0.0;
          for(int i=1; i<count; i++) {
            average_intensity += (double)average[i].average();
          }
          if(count > 0) {
            average_intensity = average_intensity / (double)count;
          }

          // variance
          double var_intensity = 0.0;
          for(int i=1; i<count; i++) {
            var_intensity += ((double)average[i].average() - average_intensity)*((double)average[i].average() - average_intensity);
          }
          if(count>0) {
            var_intensity = var_intensity / (double)count;
          }

          // Assignments of features
          o.features[prefix_ + "count"] = (float)count;
          o.features[prefix_ + "avgintensity"] = average_intensity;
          o.features[prefix_ + "varintensity"] = var_intensity;

          // for debug
          if(debug_) {
            std::cout << "count = " << count << std::endl;
            std::cout << "average intensity = " << average_intensity << std::endl;
            std::cout << "variance intensity = " << var_intensity << std::endl;
            for(int i=0; i<count; i++) {
              std::cout << "average[" << i << "] = " << average[i].average() << std::endl;
            }

            //std::string DEBUG_PREFIX="/Users/twalter/temp/spotfeatures/image";
            std::string filepath_base = debug_folder_ + "/" + debug_prefix_ + "__" + std::to_string(objId_);

            std::string filepath_export_original = filepath_base + "__00original.tiff";
            std::cout << "writing " << filepath_export_original << std::endl;
            exportImage(filepath_export_original, imSrcRoi_);

            std::string filepath_export_diamopen = filepath_base + "__01diam_open.tiff";
            std::cout << "writing " << filepath_export_diamopen << std::endl;
            exportImage(filepath_export_diamopen, imDiamOpen_);

            std::string filepath_export_residue = filepath_base + "__02residue.tiff";
            std::cout << "writing " << filepath_export_residue << std::endl;
            exportImage(filepath_export_residue, imTemp_);

            std::string filepath_export_thresh = filepath_base + "__03thresh.tiff";
            std::cout << "writing " << filepath_export_thresh << std::endl;
            exportImage(filepath_export_thresh, imThresh_);

            std::string filepath_export_overlay = filepath_base + "__04overlay.tiff";
            std::cout << "writing " << filepath_export_overlay << std::endl;
            cecog::drawContour(srcImageRange(imThresh_), destImage(imSrcRoi_), 255);
            exportImage(filepath_export_overlay, imSrcRoi_);

            // transforms.hxx --> draw contour

          }
        }

    void exportImage(std::string filepath,
                     vigra::BImage img,
                     std::string compression = "100")
        {

          vigra::ImageExportInfo exp_info(filepath.c_str());
          exp_info.setCompression(compression.c_str());
          vigra::exportImage(srcImageRange(img), exp_info);
        }

    protected:
      bool debug_;
      std::string debug_folder_;
      std::string debug_prefix_;
      unsigned diam_;
      value_type thresh_;
      unsigned borderSize_;
      vigra::Diff2D imgSize_;
      SIMAGE imSrcRoi_;
      SIMAGE imDiamOpen_;
      SIMAGE imTemp_;
      SIMAGE imThresh_;
      SIMAGE imBinSpots_;
      LIMAGE imLabSpots_;
      unsigned objId_;
      std::string prefix_;
      morpho::neighborhood2D nb_;
    };

    // Distance Features
    template <class LIMAGE>
    class DynamicDistanceFeatures
    {

    public:
        typedef typename LIMAGE::value_type lab_type;
        typedef typename LIMAGE::Iterator LabIterator;
        typedef typename LIMAGE::Accessor LabAccessor;

        typedef typename std::vector<lab_type> DynamicsVector;
        typedef typename DynamicsVector::iterator iterator_type;

        DynamicDistanceFeatures(LIMAGE &labin,
                        ROIObject const & o,
                        lab_type label,
                        lab_type dynThresh = 2,
                        std::string prefix = "dyn_distance",
                        unsigned borderSize = 0)
            : borderSize_(borderSize),
              imgSize_(o.roi.width + 2 * borderSize, o.roi.height + 2 * borderSize),
              nb_(morpho::WITHOUTCENTER8, vigra::Diff2D(imgSize_)),
              objId_(label),
              dynThresh_(dynThresh),
              prefix_(prefix),
              NB_HIGH_VALUES_(4),
              imDist_(vigra::Diff2D(o.roi.width + 2 * borderSize, o.roi.height + 2 * borderSize)),
              imDistInv_(vigra::Diff2D(o.roi.width + 2 * borderSize, o.roi.height + 2 * borderSize))
        {
            vigra::Diff2D borderOffset(borderSize_, borderSize_);

            vigra::distanceTransform(labin.upperLeft() + o.roi.upperLeft,
                             labin.upperLeft() + o.roi.lowerRight,
                             labin.accessor(),
                             imDist_.upperLeft() + borderOffset,
                             imDist_.accessor(),
                             label, 1);

            vigra::FindMinMax<lab_type> minmax;

            vigra::inspectImage(srcImageRange(imDist_), minmax);

            transformImageIfLabel(imDist_.upperLeft(),
                                  imDist_.lowerRight(),
                                  imDist_.accessor(),
                                  labin.upperLeft() + o.roi.upperLeft,
                                  labin.accessor(),
                                  imDistInv_.upperLeft(),
                                  imDistInv_.accessor(),
                                  objId_,
                                  vigra::linearIntensityTransform(-1, -minmax.max) );

            // old: ImDynMinima(srcImageRange(imSrcRoi_), dynVec_, nb_);
            ImDynMinima(imDistInv_.upperLeft() + borderOffset,
                        imDistInv_.lowerRight() - borderOffset,
                        imDistInv_.accessor(),
                        labin.upperLeft() + o.roi.upperLeft,
                        labin.accessor(),
                        dynVec_, valVec_, nb_, objId_);

            dynVec_.erase(dynVec_.begin());
            valVec_.erase(valVec_.begin());

            for(typename DynamicsVector::iterator iter = valVec_.begin();
                iter != valVec_.end(); ++iter)
            {
                *iter = minmax.max - (*iter);
            }

            dynLength_ = dynVec_.size();
        }

      void CalculateFeatures(ROIObject & o)
      {
        FilterLowValues_();
        o.features[prefix_ + "_nb_max"] = dynLength_;
        SortVectors_();

        std::string featureName = prefix_ + "_radius_0";
        o.features[featureName] = (double)maxVal_[0];

        for(unsigned i = 1; i < NB_HIGH_VALUES_; ++i) {
          std::string featureName = prefix_ + "_radius_" + itos(i, 0);
          o.features[featureName] = (double)maxVal_[i] / (double)maxVal_[0];
        }
      }


    private:
      void FilterLowValues_()
      {
        iterator_type dyniter = dynVec_.begin();
        iterator_type valiter = valVec_.begin();

        while(dyniter != dynVec_.end())
          {
            if(*dyniter < dynThresh_) {
              dyniter = dynVec_.erase(dyniter);
              valiter = valVec_.erase(valiter);
            }
            else {
              ++dyniter;
              ++valiter;
            }
          }
        dynLength_ = dynVec_.size();
      }

      void SortVectors_()
      {
        iterator_type a_iter = dynVec_.begin();
        iterator_type b_iter = valVec_.begin();

        while(a_iter != dynVec_.end())
          {
            iterator_type a_current(a_iter);
            iterator_type b_current(b_iter);
            while(a_current != dynVec_.end())
              {
                if( *a_current > *a_iter)
                  {
                    std::iter_swap(a_current, a_iter);
                    std::iter_swap(b_current, b_iter);
                  }
                a_current++; b_current++;
              }
            a_iter++; b_iter++;
          }

        for(unsigned i = 0; i < NB_HIGH_VALUES_; ++i) {
          if(i < valVec_.size())
            maxVal_.push_back(valVec_[i]);
          else
            maxVal_.push_back(0);
        }
      }


      unsigned borderSize_;
      vigra::Diff2D imgSize_;
      morpho::neighborhood2D nb_;
      lab_type objId_;
      lab_type dynThresh_;
      std::string prefix_;
      const unsigned NB_HIGH_VALUES_;
      LIMAGE imDist_;
      LIMAGE imDistInv_;
      bool calcMaximumValues__;
      DynamicsVector dynVec_, valVec_, maxVal_;
      unsigned dynLength_;
    };
}

#endif // CECOG_FEATURES
