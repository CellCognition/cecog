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


#ifndef CECOG_SEEDEDREGION_HXX
#define CECOG_SEEDEDREGION_HXX

#include <vector>
#include <queue>
#include <list>
#include <vigra/utilities.hxx>
#include <vigra/stdimage.hxx>
#include <vigra/stdimagefunctions.hxx>

namespace cecog {

  namespace detail {

    template <class COST>
    class SeedRgPixel
    {
    public:
      vigra::Point2D location_, nearest_;
      COST cost_;
      int count_;
      int label_;
      int dist_;
      int max_dist_;
      double a_, b_;

      SeedRgPixel()
      : location_(0,0), nearest_(0,0), cost_(0), count_(0), label_(0)
      {}

      SeedRgPixel(vigra::Point2D const & location, vigra::Point2D const & nearest,
                  COST const & cost, int const & count, int const & label, int const & max_dist)
      : location_(location), nearest_(nearest),
        cost_(cost), count_(count), label_(label), max_dist_(max_dist)
      {
        int dx = location_.x - nearest_.x;
        int dy = location_.y - nearest_.y;
        dist_ = dx * dx + dy * dy;
        //a_ = 1.0/255;
        //b_ = 1.0/sqrt(max_dist_);
      }

      struct Compare
      {
        // must implement > since priority_queue looks for largest element
        bool operator()(SeedRgPixel const & l,
                        SeedRgPixel const & r) const
        {
          if (r.cost_ == l.cost_)
          {
            if (r.dist_ == l.dist_)
              return r.count_ < l.count_;
            else
              return r.dist_ < l.dist_;
          } else
            return r.cost_ < l.cost_;
          //return r.a_*r.cost_ + r.b_*r.dist_ < l.a_*l.cost_ + l.b_*l.dist_;
        }
      };
    };

    struct UnlabelWatersheds
    {
      int operator()(int label) const
      {
        return label < 0 ? 0 : label;
      }
    };

  } // namespace detail


  template <class Value>
  class ShrinkHalfSizeFunctor;


  enum SRGType { KeepContours, KeepContoursPlus, CompleteGrow };
  enum SRGLabel { SRGWatershedLabel = -1, SRGFreeLabel = 0, SRGListedLabel = -2, SRGBackgroundLabel = 0 };

  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  void seededRegionGrowing(SrcImageIterator srcul,
                           SrcImageIterator srclr, SrcAccessor as,
                           SeedImageIterator seedsul, SeedAccessor aseeds,
                           DestImageIterator destul, DestAccessor ad,
                           RegionStatisticsArray & stats,
                           const SRGType srgType)
  {
    int w = srclr.x - srcul.x;
    int h = srclr.y - srcul.y;
    int count = 0;

    SrcImageIterator isy = srcul, isx = srcul;  // iterators for the src image

    typedef typename RegionStatisticsArray::value_type RegionStatistics;
    typedef typename RegionStatistics::cost_type CostType;
    typedef detail::SeedRgPixel<CostType> Pixel;

    typedef std::priority_queue<Pixel, std::vector<Pixel>, typename Pixel::Compare>  SeedRgPixelHeap;

    // initial costs regions based on their seeds
    inspectTwoImages(srcul, srclr, as, seedsul, aseeds, stats);

    //for (int i=1; i<stats.size(); i++)
      //printf("init: %d  %.1f\n", i, stats[i]());

    // copy seed image in an image with border
    vigra::IImage regions(w+2, h+2);
    vigra::IImage::Iterator ir = regions.upperLeft() + vigra::Diff2D(1,1);
    vigra::IImage::Iterator iry, irx;

    initImageBorder(destImageRange(regions), 1, SRGWatershedLabel);
    copyImage(seedsul, seedsul+vigra::Diff2D(w,h), aseeds, ir, regions.accessor());

    // allocate and init memory for the results

    SeedRgPixelHeap pheap;
    int cneighbor;
    int max_dist = w*w + h*h;

    static const vigra::Diff2D dist4[] = { vigra::Diff2D(-1,0), vigra::Diff2D(0,-1),
                                           vigra::Diff2D(1,0),  vigra::Diff2D(0,1) };
    static const vigra::Diff2D dist8[] = { vigra::Diff2D(-1,0), vigra::Diff2D(0,-1),
                                           vigra::Diff2D(1,0),  vigra::Diff2D(0,1),
                                           vigra::Diff2D(-1,1), vigra::Diff2D(1,-1),
                                           vigra::Diff2D(1,1),  vigra::Diff2D(-1,-1) };

    vigra::Point2D pos(0,0);
    for (isy=srcul, iry=ir, pos.y=0; pos.y<h; ++pos.y, ++isy.y, ++iry.y)
      for (isx=isy, irx=iry, pos.x=0; pos.x<w; ++pos.x, ++isx.x, ++irx.x)
      {
        int label = *irx;
        if (label > 0)
        {
          //printf("- (%3d,%3d) %d\n", pos.x, pos.y, label);
          // find candidate pixels for growing and fill heap
          for (int i=0; i<8; ++i)
          {
            if (irx[dist8[i]] == SRGFreeLabel)
            {
              CostType cost = stats[label].cost(as(isx, dist8[i]));
              //printf("  %d - %.1f\n", label, cost);

              Pixel pixel(pos+dist8[i], pos, cost, count++, label, max_dist);
              pheap.push(pixel);
              // mark pixels which are added to the SSL (sequentially sorted list)
              irx[dist8[i]] = SRGListedLabel;
            }
          }
        }
      }

    // perform region growing
    while (pheap.size() != 0)
    {
      Pixel pixel = pheap.top();
      pheap.pop();

      vigra::Point2D pos = pixel.location_;
      vigra::Point2D nearest = pixel.nearest_;
      int lab = pixel.label_;

      //printf("%d  - %.1f %d\n", lab, pixel.cost_, pixel.dist_);

      irx = ir + pos;
      isx = srcul + pos;

      if (srgType == KeepContours)
        for (int i = 0; i < 8; ++i)
        {
          cneighbor = irx[dist8[i]];
          if (cneighbor > 0 && cneighbor != lab)
          {
            lab = SRGWatershedLabel;
            //printf("border\n");
            break;
          }
        }

      *irx = lab;

      if (lab > 0)
      {
        // update statistics
        stats[lab](as(isx));

        // search neighborhood
        // second pass: find new candidate pixels
        for (int i = 0; i < 8; ++i)
        {
          // only add pixels which are neither already labeled nor already in the SSL
          if (irx[dist8[i]] == SRGFreeLabel)
          {
            CostType cost = stats[lab].cost(as(isx, dist8[i]));
            //printf("  %d - %.1f\n", lab, cost);

            Pixel new_pixel(pos+dist8[i], nearest, cost, count++, lab, max_dist);
            pheap.push(new_pixel);
            irx[dist8[i]] = SRGListedLabel;
          }
        }
      }
    }

    // write result
    transformImage(ir, ir + vigra::Point2D(w,h), regions.accessor(), destul, ad,
                   detail::UnlabelWatersheds());
  }

  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  inline void
  seededRegionGrowing(SrcImageIterator srcul,
                      SrcImageIterator srclr, SrcAccessor as,
                      SeedImageIterator seedsul, SeedAccessor aseeds,
                      DestImageIterator destul, DestAccessor ad,
                      RegionStatisticsArray & stats)
  {
      seededRegionGrowing(srcul, srclr, as,
                          seedsul, aseeds,
                          destul, ad,
                          stats, CompleteGrow);
  }

  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  inline void
  seededRegionGrowing(vigra::triple<SrcImageIterator, SrcImageIterator, SrcAccessor> img1,
                      vigra::pair<SeedImageIterator, SeedAccessor> img3,
                      vigra::pair<DestImageIterator, DestAccessor> img4,
                      RegionStatisticsArray & stats,
                      SRGType srgType)
  {
      seededRegionGrowing(img1.first, img1.second, img1.third,
                          img3.first, img3.second,
                          img4.first, img4.second,
                          stats, srgType);
  }

  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  inline void
  seededRegionGrowing(vigra::triple<SrcImageIterator, SrcImageIterator, SrcAccessor> img1,
                      vigra::pair<SeedImageIterator, SeedAccessor> img3,
                      vigra::pair<DestImageIterator, DestAccessor> img4,
                      RegionStatisticsArray & stats)
  {
      seededRegionGrowing(img1.first, img1.second, img1.third,
                          img3.first, img3.second,
                          img4.first, img4.second,
                          stats, CompleteGrow);
  }


//  template <class Iterator>
//  inline
//  bool
//  isInsideImage(Iterator &it, vigra::Diff2D const &p, int w, int h)
//  {
//    return ((it.x + p.x >= 0) and (it.y + p.y >= 0) and
//            (it.x + p.x < w)  and ());
//  }

  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  void seededRegionExpansion(SrcImageIterator srcul,
                             SrcImageIterator srclr, SrcAccessor as,
                             SeedImageIterator seedsul, SeedAccessor aseeds,
                             DestImageIterator dexpandul, DestAccessor ade,
                             const SRGType srgType,
                             RegionStatisticsArray stats,
                             typename RegionStatisticsArray::value_type::cost_type cost_threshold,
                             int expansion_rounds,
                             int sep_expand_rounds)
  {
    assert (expansion_rounds >= sep_expand_rounds);

    int w = srclr.x - srcul.x;
    int h = srclr.y - srcul.y;

    SrcImageIterator isy = srcul, isx = srcul;  // iterators for the src image

    typedef typename RegionStatisticsArray::value_type RegionStatistics;
    typedef typename RegionStatistics::cost_type CostType;
    typedef detail::SeedRgPixel<CostType> Pixel;

    const int border = expansion_rounds + 10;

    // copy seed image in an image with border
    vigra::IImage expanded_seeds(w+border*2, h+border*2);
    vigra::IImage::Iterator ies = expanded_seeds.upperLeft() + vigra::Diff2D(border, border);
    vigra::IImage::Iterator ies_y, ies_x;

    initImageBorder(destImageRange(expanded_seeds), 1, SRGWatershedLabel);
    copyImage(seedsul, seedsul+vigra::Diff2D(w,h), aseeds, ies, expanded_seeds.accessor());

    typedef std::queue<Pixel> PixelQueue;
    typedef std::vector<vigra::Point2D> PointVector;

    PixelQueue pqueue;
    PointVector pvector;
    int cneighbor;
    int max_dist = w*w + h*h;

    enum NeigborhoodType { fourNBH = 0, eightNBH = 1 };

    const int neighborhoodA[] = {4, 8};

    const vigra::Diff2D dist8A[] = { vigra::Diff2D(-1,0), vigra::Diff2D(0,-1),
                                     vigra::Diff2D(1,0),  vigra::Diff2D(0,1),
                                     vigra::Diff2D(-1,1), vigra::Diff2D(1,-1),
                                     vigra::Diff2D(1,1),  vigra::Diff2D(-1,-1)
                                   };

    vigra::Point2D pos(0,0);
    unsigned round_cnt = 0;

    for (isy=srcul, ies_y=ies, pos.y=0; pos.y<h; ++pos.y, ++isy.y, ++ies_y.y)
      for (isx=isy, ies_x=ies_y, pos.x=0; pos.x<w; ++pos.x, ++isx.x, ++ies_x.x)
      {
        int label = *ies_x;
        if (label > 0)
        {
          //printf("- (%3d,%3d) %d\n", pos.x, pos.y, label);
          // find candidate pixels for growing and fill heap
          for (int i = 0; i < neighborhoodA[eightNBH]; ++i)
          {
            if (ies_x[dist8A[i]] == SRGFreeLabel)
            {
              Pixel pixel(pos+dist8A[i], pos, 0, 0, label, max_dist);
              pqueue.push(pixel);
              // mark pixels which are added to the SSL (sequentially sorted list)
              ies_x[dist8A[i]] = SRGListedLabel;
              if (sep_expand_rounds > 0)
                pvector.push_back(pos+dist8A[i]);
            }
          }
        }
      }
    round_cnt = pqueue.size();

    //printf("SRG moo1\n");

    // perform region expansion
    int round = 0;
    int sep_expand_cnt = sep_expand_rounds - 1;
    int nh = fourNBH;

    bool is_stats_active = false;

    while (pqueue.size() != 0 && round < expansion_rounds)
    {
      Pixel pixel = pqueue.front();
      pqueue.pop();
      round_cnt--;

      vigra::Point2D pos = pixel.location_;
      int lab = pixel.label_;

      //printf(" %d - %u - %u\n", round, round_cnt, pqueue.size());

      ies_x = ies + pos;
      isx = srcul + pos;

      bool accept_point = true;
      bool valid_source_point = (pos.x >= 0 && pos.x < w && pos.y >= 0 && pos.y < h);

      //printf("SRG moo2\n");

      if (is_stats_active && valid_source_point)
      {
        CostType cost = stats[lab].cost(as(isx));
        //printf("%d %d - %.1f %.1f - %d\n", round, lab, stats[lab](), cost, as(isx));
        if (cost > cost_threshold)
          accept_point = false;
      }

      //printf("SRG moo3\n");

      if (accept_point)
      {

        if (srgType == KeepContours)
          for (int i = 0; i < neighborhoodA[eightNBH]; i++)
          {
            cneighbor = ies_x[dist8A[i]];
            if (cneighbor > 0 && cneighbor != lab)
            {
              lab = SRGWatershedLabel;
              //printf("border\n");
              break;
            }
          }

        //printf("SRG moo4\n");

        if (sep_expand_cnt > 0)
          pvector.push_back(pos);

        *ies_x = lab;

        //printf("SRG moo5\n");

        if (lab > 0)
        {
          // update statistics
          if (valid_source_point)
            stats[lab](as(isx));

          // search neighborhood
          // second pass: find new candidate pixels
          for (int i = 0; i < neighborhoodA[nh]; ++i)
          {
            // only add pixels which are neither already labeled nor already in the SSL
            if (ies_x[dist8A[i]] == SRGFreeLabel)
            {
              Pixel new_pixel(pos+dist8A[i], pos, 0, 0, lab, max_dist);
              pqueue.push(new_pixel);
              ies_x[dist8A[i]] = SRGListedLabel;
            }
          }
        }
      } // if accept_point
      //printf("SRG moo6\n");

      if (round_cnt == 0)
      {
        if (round > 0 && !is_stats_active)
        {
          // initial costs regions based on their seeds
          is_stats_active = true;
        }


        round++;
        round_cnt = pqueue.size();
        // switch between 4- and 8-neighborhood every round
        nh = (nh + 1) % 2;
        //printf("*** new round ***\n");
        sep_expand_cnt--;
      }
    }
    //printf("SRG moo7\n");

    PointVector::iterator pl_it = pvector.begin();
    for (; pl_it != pvector.end(); ++pl_it)
      ies[*pl_it] = SRGBackgroundLabel;

    // write result
    transformImage(ies, ies + vigra::Point2D(w,h), expanded_seeds.accessor(), dexpandul, ade,
                   detail::UnlabelWatersheds());
    //printf("SRG moo8\n");

  }

  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  inline void
  seededRegionExpansion(vigra::triple<SrcImageIterator, SrcImageIterator, SrcAccessor> img1,
                        vigra::pair<SeedImageIterator, SeedAccessor> img3,
                        vigra::pair<DestImageIterator, DestAccessor> img4,
                        const SRGType srgType,
                        RegionStatisticsArray stats,
                        typename RegionStatisticsArray::value_type::cost_type cost_threshold,
                        int expansion_rounds,
                        int sep_expand_rounds)
  {
      seededRegionExpansion(img1.first, img1.second, img1.third,
                            img3.first, img3.second,
                            img4.first, img4.second,
                            srgType,
                            stats, cost_threshold,
                            expansion_rounds, sep_expand_rounds);
      //printf("SRG moo9\n");
 }

  template <class Image1, class Image2, class Image3, class RegionStatisticsArray>
  inline void
  seededRegionExpansion(Image1 const &imgIn,
                        Image2 const &imgSeeds,
                        Image3 &imgOut,
                        const SRGType srgType,
                        RegionStatisticsArray stats,
                        typename RegionStatisticsArray::value_type::cost_type cost_threshold,
                        int expansion_rounds,
                        int sep_expand_rounds)
  {
    seededRegionExpansion(srcImageRange(imgIn),
                          maskImage(imgSeeds),
                          destImage(imgOut),
                          srgType,
                          stats, cost_threshold,
                          expansion_rounds, sep_expand_rounds);
    //printf("SRG moo10\n");
  }



  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  void seededRegionShrinking(SrcImageIterator srcul,
                             SrcImageIterator srclr, SrcAccessor as,
                             SeedImageIterator seedsul, SeedAccessor aseeds,
                             DestImageIterator dseedul, DestAccessor ads,
                             RegionStatisticsArray & stats,
                             //typename RegionStatisticsArray::value_type::cost_type cost_threshold,
                             int sep_seed_rounds)
  {
    int w = srclr.x - srcul.x;
    int h = srclr.y - srcul.y;

    if (sep_seed_rounds > 0)
    {
      // iterators for the src image
      SrcImageIterator is, is_x = srcul;

      typedef typename RegionStatisticsArray::value_type RegionStatistics;
      typedef typename RegionStatistics::cost_type CostType;
      typedef detail::SeedRgPixel<CostType> Pixel;

      const int border = 1;

      // copy seed image in an image with border
      vigra::IImage shrinked_seeds(w+border*2, h+border*2);
      vigra::IImage::Iterator iss = shrinked_seeds.upperLeft() + vigra::Diff2D(border, border);
      vigra::IImage::Iterator iss_y, iss_x;

      //initImageBorder(destImageRange(shrinked_seeds), 1, SRGWatershedLabel);
      copyImage(seedsul, seedsul+vigra::Diff2D(w,h), aseeds, iss, shrinked_seeds.accessor());

      // init stats
      inspectTwoImages(srcImageRange(shrinked_seeds), srcImage(shrinked_seeds), stats);

      typedef vigra::pair<vigra::Point2D, int> PointLabelPair;
      typedef std::list<PointLabelPair> PointList;

      PointList pslist;
      int cneighbor;
      int max_dist = w*w + h*h;

      enum NeigborhoodType { fourNBH = 0, eightNBH = 1 };

      const int neighborhoodA[] = {4, 8};

      const vigra::Diff2D dist8A[] = { vigra::Diff2D(-1,0), vigra::Diff2D(0,-1),
                                       vigra::Diff2D(1,0),  vigra::Diff2D(0,1),
                                       vigra::Diff2D(-1,1), vigra::Diff2D(1,-1),
                                       vigra::Diff2D(1,1),  vigra::Diff2D(-1,-1)
                                     };

      // collect candidates
      // performs already one round of shrinking

      vigra::Point2D pos(0,0);
      for (iss_y=iss, pos.y=0; pos.y<h; ++pos.y, ++iss_y.y)
        for (iss_x=iss_y, pos.x=0; pos.x<w; ++pos.x, ++iss_x.x)
        {
          int &label = *iss_x;
          if (label > SRGBackgroundLabel)
          {
            for (int i = 0; i < neighborhoodA[eightNBH]; ++i)
              if (iss_x[dist8A[i]] == SRGBackgroundLabel)
              {
                  pslist.push_back(PointLabelPair(pos, label));
                  label = SRGListedLabel;
                  break;
              }
          }
        }


      // perform region shrinking
      int nh = fourNBH;
      int sep_seed_cnt = sep_seed_rounds - 1;
      while (sep_seed_cnt > 0 && pslist.size() > 0)
      {
        int psl_size = pslist.size();
        //printf("*** shrink round: %d, %d\n", sep_seed_cnt, psl_size);
        for (; psl_size > 0; --psl_size)
        {
          PointLabelPair plp = pslist.front();
          pslist.pop_front();
          vigra::Point2D pos = plp.first;
          int label = plp.second;

          assert(label != 0);

          iss_x = iss + pos;
          is_x = is + pos;

          // update stats
          //stats[label](as(is_x), *iss_x);

          // check if removal of point is accepted by stats
          if (!(stats[label]()))
          {
            *iss_x = SRGBackgroundLabel;

            // find new candidates
            for (int i = 0; i < neighborhoodA[nh]; ++i)
            {
              //int &label = iss_x[dist8A[i]];
              if (iss_x[dist8A[i]] == label)
              {
                pslist.push_back(PointLabelPair(pos + dist8A[i], label));
                iss_x[dist8A[i]] = SRGListedLabel;
              }
            }
          }
        }
        sep_seed_cnt--;
        nh = (nh + 1) % 2;
      }
      // write result
      transformImage(iss, iss + vigra::Diff2D(w,h), shrinked_seeds.accessor(), dseedul, ads,
                     detail::UnlabelWatersheds());
    } else
      copyImage(seedsul, seedsul + vigra::Diff2D(w,h), aseeds,
                dseedul, ads);
  }


  template <class SrcImageIterator, class SrcAccessor,
            class SeedImageIterator, class SeedAccessor,
            class DestImageIterator, class DestAccessor,
            class RegionStatisticsArray>
  inline void
  seededRegionShrinking(vigra::triple<SrcImageIterator, SrcImageIterator, SrcAccessor> img1,
                        vigra::pair<SeedImageIterator, SeedAccessor> img3,
                        vigra::pair<DestImageIterator, DestAccessor> img4,
                        RegionStatisticsArray & stats,
                        //typename RegionStatisticsArray::value_type::cost_type cost_threshold,
                        int sep_seed_rounds)
  {
      seededRegionShrinking(img1.first, img1.second, img1.third,
                            img3.first, img3.second,
                            img4.first, img4.second,
                            stats,
                            //cost_threshold,
                            sep_seed_rounds);
  }




  template <class Value, int Scale=1>
  class SRGDirectValueFunctor
  {
    public:
      typedef Value argument_type;
      typedef Value result_type;
      typedef Value value_type;
      typedef Value cost_type;

      inline
      void operator()(argument_type const & v) const
      {}

      inline
      cost_type cost(argument_type const & v) const
      {
        return v * Scale;
      }
  };

  template <class Value>
  class SrgMeanValueFunctor
  {
    public:
      typedef Value argument_type;
      typedef Value result_type;
      typedef Value value_type;
      typedef Value cost_type;

      SrgMeanValueFunctor()
      : sum(0.0), n(0)
      {}

      inline
      void operator()(argument_type const &v)
      {
        sum += v;
        n++;
      }

      inline
      result_type operator()() const
      {
        return sum / cost_type(n);
      }

      inline
      cost_type cost(argument_type const &v)
      {
        return std::abs(v - sum/cost_type(n));
      }

    private:
      cost_type sum;
      long int n;
  };

  template <class Value>
  class SrgNormMeanValueFunctor
  {
    public:
      typedef Value argument_type;
      typedef Value result_type;
      typedef Value value_type;
      typedef Value cost_type;

      SrgNormMeanValueFunctor()
      : sum(0.0), n(0.0), ssum(0.0)
      {}

      inline
      void operator()(argument_type const & v)
      {
        sum += v;
        ssum += v * v;
        n++;
      }

      inline
      result_type operator()() const
      {
        return sum / n;
      }

      inline
      cost_type const cost(argument_type const & v)
      {
        cost_type sd = sqrt((ssum - sum * sum / n) / (n-1));
        return (sum/n - v) / sd;
      }

    private:
      cost_type sum, ssum, n;
  };


  template <class Value>
  class SrgConstValueFunctor
  {
    public:
      typedef Value argument_type;
      typedef Value result_type;
      typedef Value value_type;
      typedef Value cost_type;

      inline
      void operator()(argument_type const &v) const
      {}

      inline
      const result_type operator()() const
      {
        return vigra::NumericTraits<result_type>::zero();
      }

      inline
      cost_type const cost(argument_type const &v) const
      {
        return vigra::NumericTraits<cost_type>::zero();
      }
  };


  template <class Value>
  class ShrinkHalfSizeFunctor
  {
    public:
      typedef Value argument_type;
      typedef int result_type;
      typedef Value value_type;
      typedef Value cost_type;

      ShrinkHalfSizeFunctor()
      : count(0), count_shrink(0)
      {}

      inline
      void operator()(argument_type const &)
      {
        count++;
      }

      inline
      result_type operator()() const
      {
        return count;
      }

      inline
      bool is_valid()
      {
        if ((count >> 1) > count_shrink)
        {
          count_shrink++;
          return true;
        } else
        return false;
      }

    private:
      result_type count, count_shrink;
  };



  // simplified functions to wrap
//
//
//
//
//  template <class IMAGE1, class IMAGE2, class IMAGE3>
//  IMAGE3 seededRegionExpansion(IMAGE1 const &imgIn, IMAGE2 const &imgInLabels,
//                             int iExpansionSize,
//                             int iExpansionSeparationSize,
//                             double dExpansionCostThreshold,
//                             int iLabelSize,
//                             bool bMeanValueFunctor=false)
//  {
//    IMAGE3 imgOutLabels(imgIn.size());
//    if (bMeanValueFunctor)
//    {
//      vigra::ArrayOfRegionStatistics<SRGNormMeanValueFunctor<double> >
//        oStatsExpand(iLabelSize);
//      seededRegionExpansion(srcImageRange(imgIn),
//                            srcImage(imgInLabels),
//                            destImage(imgOutLabels),
//                            KeepContours,
//                            oStatsExpand,
//                            dExpansionCostThreshold,
//                            iExpansionSize,
//                            iExpansionSeparationSize);
//    } else
//    {
//      vigra::ArrayOfRegionStatistics<SRGConstValueFunctor<double> >
//        oStatsExpand(iLabelSize);
//      seededRegionExpansion(srcImageRange(imgIn),
//                            srcImage(imgInLabels),
//                            destImage(imgOutLabels),
//                            KeepContours,
//                            oStatsExpand,
//                            dExpansionCostThreshold,
//                            iExpansionSize,
//                            iExpansionSeparationSize);
//    }
//    return imgOutLabels;
//  }
//
//
//
} // namespace cecog

#endif // CECOG_SEEDEDREGION_HXX
