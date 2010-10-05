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


#ifndef CECOG_SEGMENTATION
#define CECOG_SEGMENTATION

#include <iostream>
#include <utility>
#include <algorithm>
#include <map>
#include <vector>
#include <list>
#include <queue>


#include "vigra/stdimage.hxx"
#include "vigra/impex.hxx"
#include "vigra/inspectimage.hxx"
#include "vigra/transformimage.hxx"
#include "vigra/flatmorphology.hxx"
#include "vigra/contourcirculator.hxx"
#include "vigra/pixelneighborhood.hxx"
#include "vigra/convolution.hxx"
#include "vigra/distancetransform.hxx"
#include "vigra/functorexpression.hxx"
#include "vigra/watersheds.hxx"
#include "vigra/resizeimage.hxx"


#include "boost/graph/graph_traits.hpp"
#include "boost/graph/adjacency_list.hpp"
#include "boost/tuple/tuple.hpp"


#include "cecog/inspectors.hxx"
#include "cecog/shared_objects.hxx"
#include "cecog/containers.hxx"
#include "cecog/transforms.hxx"
#include "cecog/dir.hxx"
#include "cecog/utilities.hxx"
#include "cecog/math.hxx"
#include "cecog/features.hxx"
#include "cecog/seededregion.hxx"


namespace cecog
{
  using namespace vigra::functor;


  /**
   * hole_filling
   *
   * fill holes in binary image by inverse labeling
   * ASSUMPTION: background has biggest roisize than any hole
   */
  template <class BIMAGE>
  void holeFilling(BIMAGE & img_bin, bool eightneigborhood=false,
                   typename BIMAGE::value_type background=0,
                   typename BIMAGE::value_type foreground=255)
  {
    vigra::IImage labels(img_bin.size());
    int max_background_label = labelImageWithBackground(srcImageRange(img_bin), destImage(labels), eightneigborhood, foreground);
    vigra::ArrayOfRegionStatistics<vigra::FindROISize<vigra::IImage::value_type> > background_roisize(max_background_label);
    inspectTwoImages(srcImageRange(labels), srcImage(labels), background_roisize);
    int background_id;
    unsigned max_region = 0;
    for (int i=1; i < background_roisize.size(); i++)
      if (background_roisize[i]() > max_region)
      {
        max_region = background_roisize[i]();
        background_id = i;
      }
    transformImageIf(srcImageRange(labels), maskImage(labels), destImage(img_bin),
                     ifThenElse(Arg1() == Param(background_id),
                                Param(background),
                                Param(foreground))
                    );
  }


  enum SegmentationType { ShapeBasedSegmentation, IntensityBasedSegmentation };


  typedef ImageMaskContainer<8> ImageMaskContainer8;


  //ImageMaskContainer8::label_type
  vigra::BImage
  splitMergeSegmentation(vigra::BImage const & img_in,
                         vigra::BImage const & bin_in,
                         std::string const & filepath_img,
                         int rsize,
                         int gauss_size, int maxima_size,
                         int iMinMergeSize,
                         std::string filepath_rgb="",
                         SegmentationType segmentation_type=ShapeBasedSegmentation
                        )
  {
    const int squaredRsize = 2*rsize;

    StopWatch oStopWatch, oStopWatchTotal;

    #ifdef __DEBUG_IMAGE_EXPORT__
      std::string filepath_base = filepath_img.substr(0, filepath_img.size()-4);
      std::string filepath_export_labels_original = filepath_base + "__00labels.png";
      std::string filepath_export_inv           = filepath_base + "__01inv.png";
      std::string filepath_export_binary        = filepath_base + "__02bin.png";
      std::string filepath_export_min           = filepath_base + "__03min.png";
      std::string filepath_export_voronoi       = filepath_base + "__04voronoi.png";
      std::string filepath_export_binws         = filepath_base + "__05binws.png";
      std::string filepath_export_final         = filepath_base + "__06final.png";
    #endif

    typedef ImageMaskContainer8::label_type::value_type label_value_type;
    typedef ImageMaskContainer8::image_type::value_type image_value_type;
    typedef ImageMaskContainer8::binary_type::value_type binary_value_type;

    binary_value_type background = 0;
    binary_value_type foreground = 255;

    //vigra::ImageImportInfo img_info(filepath_img.c_str());
    static const int mem_border = 10;
    int w = img_in.width();
    int h = img_in.height();
    int wx = w + 2*mem_border;
    int hx = h + 2*mem_border;

    ImageMaskContainer<8>::image_type img(wx, hx);

    copyImage(img_in.upperLeft(),
              img_in.lowerRight(),
              img_in.accessor(),
              img.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              img.accessor());

    ImageMaskContainer8::binary_type img_bin(wx, hx);
    copyImage(bin_in.upperLeft(),
              bin_in.lowerRight(),
              bin_in.accessor(),
              img_bin.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              img_bin.accessor());

    // do some hole-filling
    holeFilling(img_bin, false, background, foreground);

    ImageMaskContainer8::label_type labels_original(wx, hx);
    int number_original_labels =
      labelImageWithBackground(srcImageRange(img_bin), destImage(labels_original),
                               false, background);
    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels_original), vigra::ImageExportInfo(filepath_export_labels_original.c_str()));
    #endif


    #ifdef __DEBUG__
      printf("StopWatch: preamble %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();

    bool bScaleForSpeed = true;

    vigra::BImage bimg(wx, hx), timg(wx, hx);

    if (segmentation_type == ShapeBasedSegmentation)
    {
      #ifdef __DEBUG__
        printf("--- distance transform & gaussian smoothing\n");
      #endif
      vigra::FImage fimg(wx, hx);
      distanceTransform(srcImageRange(img_bin), destImage(fimg), foreground, 2);
      transformImage(srcImageRange(fimg), destImage(fimg),
                     Arg1() + Param(0.1 * rand() / (RAND_MAX + 1.0)));
      gaussianSmoothing(srcImageRange(fimg), destImage(bimg), gauss_size);
    } else
    {
      #ifdef __DEBUG__
        printf("--- gaussian smoothing\n");
      #endif
      gaussianSmoothing(srcImageRange(img), destImage(bimg), gauss_size);
    }

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(bimg), vigra::ImageExportInfo(filepath_export_inv.c_str()));
    #endif

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(img_bin), vigra::ImageExportInfo(filepath_export_binary.c_str()));
    #endif

    #ifdef __DEBUG__
      printf("StopWatch: transform+smoothing %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();


    #ifdef __DEBUG__
      printf("--- disc dilation, radius %d\n", maxima_size);
    #endif


    ImageMaskContainer8::label_type labels(wx, hx), labels2(wx, hx);
    if (bScaleForSpeed)
    {
      ImageMaskContainer8::label_type imgLabelsTmp(wx/2, hx/2);
      vigra::BImage imgBinTmp(wx/2, hx/2);
      resizeImageLinearInterpolation(srcImageRange(bimg), destImageRange(imgBinTmp));
      discDilation(srcImageRange(imgBinTmp), destImage(imgLabelsTmp), maxima_size/2);
      resizeImageLinearInterpolation(srcImageRange(imgLabelsTmp), destImageRange(labels));
    } else
    {
      discDilation(srcImageRange(bimg), destImage(labels), maxima_size);
    }
    combineTwoImagesIf(srcImageRange(bimg), srcImage(labels), maskImage(img_bin), destImage(labels2),
                     ifThenElse(Arg1() < Arg2(),
                                Param(background),
                                Arg2())
                    );


    #ifdef __DEBUG__
      printf("StopWatch: disc dilation %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();


    // label the minima just found
    int number_split_labels =
      labelImageWithBackground(srcImageRange(labels2), destImage(labels2),
                               false, background);
    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_min.c_str()));
    #endif

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_min.c_str()));
    #endif

    #ifdef __DEBUG__
      printf("--- seeded region growing\n");
    #endif

    vigra::ArrayOfRegionStatistics<SRGDirectValueFunctor<double, -1> > gradstat(number_split_labels);
    labels = 0;
    seededRegionGrowing(srcImageRange(bimg), srcImage(labels2),
                        destImage(labels), gradstat, KeepContours);

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels), vigra::ImageExportInfo(filepath_export_voronoi.c_str()));
    #endif

    transformImageIf(srcImageRange(labels), maskImage(img_bin), destImage(labels2),
                     ifThenElse(Arg1() == Param(background),
                                Param(background),
                                Arg1())
                     );

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_binws.c_str()));
    #endif

    vigra::ArrayOfRegionStatistics< vigra::FindBoundingRectangle > bounds_original(number_original_labels);
    inspectTwoImages(srcIterRange(vigra::Diff2D(0,0),
                                  vigra::Diff2D(0,0) + labels_original.size()),
                     srcImage(labels_original), bounds_original);

    vigra::ArrayOfRegionStatistics< vigra::FindROISize<label_value_type > > roisize_original(number_original_labels);
    inspectTwoImages(srcImageRange(labels_original),
                     srcImage(labels_original), roisize_original);

    vigra::ArrayOfRegionStatistics< vigra::FindROISize<label_value_type > > roisize_split(number_split_labels);
    inspectTwoImages(srcImageRange(labels2),
                     srcImage(labels2), roisize_split);

    std::map< label_value_type, label_value_type > label_map_test;
    typedef std::vector< label_value_type > label_vector_type;
    typedef std::map< label_value_type, label_vector_type > label_map_type;
    label_map_type label_map;
    for (int y = 0; y < hx; y++)
      for (int x = 0; x < wx; x++)
        if (labels2(x,y) > 0)
        {
          label_value_type l_org = labels_original(x,y);
          label_value_type l_new = labels2(x,y);
          if (label_map_test.count(l_new) == 0)
          {
            label_map_test[l_new] = 1;
            label_map[l_org].push_back(l_new);
          }
        }
    label_map_type::iterator it = label_map.begin();
    for (; it != label_map.end(); it++)
      if ((*it).second.size() > 1)
      {
        label_value_type label_orig = (*it).first;

        #ifdef __DEBUG__
          printf("%d\n", label_orig);
        #endif

        double perimeter_orig =
          blockInspector<BlockPerimeter>(labels_original.upperLeft() + bounds_original[label_orig].upperLeft,
                                         labels_original.upperLeft() + bounds_original[label_orig].lowerRight,
                                         labels_original.accessor(),
                                         label_orig);
        double circ_orig = feature_circularity(perimeter_orig, roisize_original[label_orig]());

        bool accept_split = true;
        label_vector_type::iterator it_split = (*it).second.begin();
        for (; it_split != (*it).second.end(); it_split++)
        {
          label_value_type label_split = *it_split;

          #ifdef __DEBUG__
            printf("  %d\n", label_split);
          #endif

          double perimeter_split =
            blockInspector<BlockPerimeter>(labels2.upperLeft() + bounds_original[label_orig].upperLeft,
                                           labels2.upperLeft() + bounds_original[label_orig].lowerRight,
                                           labels2.accessor(),
                                           label_split);
          double roisize = roisize_split[label_split]();
          double circ_split = feature_circularity(perimeter_split, roisize);

          #ifdef __DEBUG__
            printf("    %.2f %.2f, %.2f\n", circ_split, circ_orig, roisize);
          #endif

          if (accept_split && abs(1.0-circ_split) < abs(1.0-circ_orig) && roisize > iMinMergeSize)
            accept_split = true;
          else
            accept_split = false;
        }

        if (!accept_split)
        {
          copyImageIfLabel(labels_original.upperLeft() + bounds_original[label_orig].upperLeft,
                           labels_original.upperLeft() + bounds_original[label_orig].lowerRight,
                           labels_original.accessor(),
                           labels_original.upperLeft() + bounds_original[label_orig].upperLeft,
                           labels_original.accessor(),
                           labels2.upperLeft() + bounds_original[label_orig].upperLeft,
                           labels2.accessor(),
                           label_orig);
          #ifdef __DEBUG__
            printf("  NO\n");
          #endif
        }
        #ifdef __DEBUG__
          else
            printf("  YES\n");
        #endif
      }

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_final.c_str()));
    #endif

//    ImageMaskContainer8::label_type label_out(w,h);
//    copyImage(labels2.upperLeft() + vigra::Diff2D(mem_border, mem_border),
//              labels2.lowerRight() - vigra::Diff2D(mem_border, mem_border),
//              labels2.accessor(),
//              label_out.upperLeft(),
//              label_out.accessor());
    vigra::BImage bin_out(w,h);
    transformImageIf(labels2.upperLeft() + vigra::Diff2D(mem_border, mem_border),
                     labels2.lowerRight() - vigra::Diff2D(mem_border, mem_border),
                     labels2.accessor(),
                     labels2.upperLeft() + vigra::Diff2D(mem_border, mem_border),
                     labels2.accessor(),
                     bin_out.upperLeft(),
                     bin_out.accessor(),
                     Param(foreground)
                     );

    #ifdef __DEBUG__
      printf("StopWatch: final %.3fs\n", oStopWatchTotal.measure());
    #endif
    oStopWatch.reset();

    return bin_out;
  }






  void segmentationCorrection(vigra::BImage const & img_in,
                              vigra::BImage const & bin_in,
                              vigra::BImage & bin_out,
                              std::string const & filepath_img,
                              int rsize,
                              int gauss_size, int maxima_size,
                              int iMinMergeSize,
                              std::string filepath_rgb="",
                              SegmentationType segmentation_type=ShapeBasedSegmentation)

  {
    const int squaredRsize = 2*rsize;

    StopWatch oStopWatch, oStopWatchTotal;

    std::string filepath_base = filepath_img.substr(0, filepath_img.size()-4);
    std::string filepath_export_inv           = filepath_base + "__01inv.png";
    std::string filepath_export_binary        = filepath_base + "__02bin.png";
    std::string filepath_export_min           = filepath_base + "__03min.png";
    std::string filepath_export_voronoi       = filepath_base + "__04voronoi.png";
    std::string filepath_export_binws         = filepath_base + "__05binws.png";
    std::string filepath_export_rgb           = filepath_base + "__06seg.png";
    std::string filepath_export_rgb_merged    = filepath_base + "__07seg_merged.png";
    std::string filepath_export_binary_merged = filepath_base + "__08bin_merged.png";

    typedef ImageMaskContainer<8> ImageMaskContainer8;
    typedef ImageMaskContainer8::label_type::value_type label_value_type;
    typedef ImageMaskContainer8::image_type::value_type image_value_type;
    typedef ImageMaskContainer8::binary_type::value_type binary_value_type;

    binary_value_type background = 0;
    binary_value_type foreground = 255;

    //vigra::ImageImportInfo img_info(filepath_img.c_str());
    static const int mem_border = 10;
    int w = img_in.width();
    int h = img_in.height();
    int wx = w + 2*mem_border;
    int hx = h + 2*mem_border;

    ImageMaskContainer<8>::image_type img(wx, hx);

    copyImage(img_in.upperLeft(),
              img_in.lowerRight(),
              img_in.accessor(),
              img.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              img.accessor());

    ImageMaskContainer8::binary_type img_bin(wx, hx);
    copyImage(bin_in.upperLeft(),
              bin_in.lowerRight(),
              bin_in.accessor(),
              img_bin.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              img_bin.accessor());


//    ImageMaskContainer8::image_type img(wx, hx);
//    ImageMaskContainer8::rgb_type img_rgb(wx, hx);
//
//    if (img_info.isGrayscale())
//    {
//      importImage(img_info,
//                  img.upperLeft() + vigra::Diff2D(mem_border, mem_border),
//                  img.accessor());
//    } else
//    {
//      importImage(img_info,
//                  img_rgb.upperLeft() + vigra::Diff2D(mem_border, mem_border),
//                  img_rgb.accessor());
//      extractRGBChannel(img_rgb, img, rgb_channel);
//    }
//




    //printf("moo2\n");


    // do some hole-filling
    //holeFilling(img_bin, false, background, foreground);

    vigra::IImage labels(wx, hx), labels2(wx, hx);
    //printf("moo3\n");

    int object_label1 =
      labelImageWithBackground(srcImageRange(img_bin), destImage(labels),
                               false, background);
    //printf("moo4\n");

//    vigra::ArrayOfRegionStatistics<vigra::FindROISize<label_value_type> > roisize1(object_label1);
//    inspectTwoImagesIf(srcImageRange(labels),
//                       srcImage(labels),
//                       maskImage(labels),
//                       roisize1);
//
//    int min_roi_size = 5, max_roi_size = 12000;
//    int validObjects = 0;
//    for (int i=1; i<object_label1; i++)
//    {
//      #ifdef __DEBUG__
//        printf("object: %d, size: %d\n", i, roisize1[i]());
//      #endif
//      if (roisize1[i]() > max_roi_size or roisize1[i]() < min_roi_size)
//      {
//        combineTwoImages(srcImageRange(img_bin),
//                         srcImage(labels),
//                         destImage(img_bin),
//                         ifThenElse(Arg2() == Param(i), Param(0), Arg1()));
//        //transformImage(srcImageRange(labels),
//        //               destImage(img_bin),
//        //               ifThen(Arg1() == Param(i), Param(0)));
//      } else
//        validObjects++;
//    }
//
//    //FIXME!
//    if (validObjects == 0)
//    {
//      printf("moo5\n");
//      return bin_in;
//    }
//

//    exportImage(srcImageRange(img_bin), vigra::ImageExportInfo(filepath_export_binary.c_str()));

    #ifdef __DEBUG__
      printf("StopWatch: preamble %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();

    labels = 0;
    labels2 = 0;
    vigra::BImage bimg(wx, hx), timg(wx, hx);

    if (segmentation_type == ShapeBasedSegmentation)
    {
      #ifdef __DEBUG__
        printf("--- distance transform & gaussian smoothing\n");
      #endif
      vigra::FImage fimg(wx, hx);
      distanceTransform(srcImageRange(img_bin), destImage(fimg), foreground, 2);
      transformImage(srcImageRange(fimg), destImage(timg),
                     Arg1() + Param(0.1 * rand() / (RAND_MAX + 1.0)));
      gaussianSmoothing(srcImageRange(timg), destImage(bimg), gauss_size);
    } else
    {
      #ifdef __DEBUG__
        printf("--- gaussian smoothing\n");
      #endif
      gaussianSmoothing(srcImageRange(img), destImage(bimg), gauss_size);
    }

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(bimg), vigra::ImageExportInfo(filepath_export_inv.c_str()));
    #endif

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(img_bin), vigra::ImageExportInfo(filepath_export_binary.c_str()));
    #endif

    #ifdef __DEBUG__
      printf("StopWatch: transform+smoothing %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();


    #ifdef __DEBUG__
      printf("--- disc dilation, radius %d\n", maxima_size);
    #endif

    bool bScaleDiscDilation = true;

    if (bScaleDiscDilation)
    {

      discDilation(srcImageRange(bimg), destImage(labels), maxima_size);

      combineTwoImagesIf(srcImageRange(bimg), srcImage(labels), maskImage(img_bin), destImage(labels2),
                       ifThenElse(Arg1() < Arg2(),
                                  Param(background),
                                  Arg2())
                      );

    } else
    {
      discDilation(srcImageRange(bimg), destImage(labels), maxima_size);

      combineTwoImagesIf(srcImageRange(bimg), srcImage(labels), maskImage(img_bin), destImage(labels2),
                       ifThenElse(Arg1() < Arg2(),
                                  Param(background),
                                  Arg2())
                      );
    }

    #ifdef __DEBUG__
      printf("StopWatch: disc dilation %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();


    // label the minima just found
    int max_region_label =
      labelImageWithBackground(srcImageRange(labels2), destImage(labels2),
                               false, background);
    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_min.c_str()));
    #endif

//    vigra::ArrayOfRegionStatistics<FindAVGCenter> maxcenter(max_region_label);
//    inspectTwoImagesIf(srcIterRange(vigra::Diff2D(0,0), vigra::Diff2D(wx,hx)),
//                       srcImage(labels2),
//                       maskImage(labels2),
//                       maxcenter);
//    labels2 = 0;
//    for (int ci=1; ci < maxcenter.size()-1; ci++)
//    {
//      bool valid = true;
//      vigra::Point2D pi(maxcenter[ci]());
//      for (int cj=ci+1; cj < maxcenter.size(); cj++)
//      {
//        vigra::Point2D pj(maxcenter[cj]());
//        if ((pi - pj).squaredMagnitude() <= 2)
//        {
//          valid = false;
//          break;
//        }
//      }
//      if (valid)
//        labels2[pi] = ci;
//    }

//      labels2[c + vigra::Diff2D(1,0)] = ci;
//      labels2[c + vigra::Diff2D(0,1)] = ci;
//      labels2[c + vigra::Diff2D(-1,0)] = ci;
//      labels2[c + vigra::Diff2D(0,-1)] = ci;
//      labels2[c + vigra::Diff2D(1,1)] = ci;
//      labels2[c + vigra::Diff2D(-1,-1)] = ci;
//      labels2[c + vigra::Diff2D(1,-1)] = ci;
//      labels2[c + vigra::Diff2D(-1,1)] = ci;




    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_min.c_str()));
    #endif


    //discMedian(srcImageRange(img), destImage(timg), 2);

    // invert image
    gaussianSmoothing(srcImageRange(img), destImage(timg), 1.0);
    //transformImage(srcImageRange(timg), destImage(timg),
    //               vigra::linearIntensityTransform(-1, -255));
    //transformImage(srcImageRange(timg), destImage(timg),
    //               vigra::linearIntensityTransform(-1, -255));

    //vigra::FImage gimg(w, h);
    //gaussianSmoothing(srcImageRange(timg), destImage(gimg), 1.0);
    /*
    combineTwoImages(srcImageRange(timg), srcImage(img_bin), destImage(timg),
                     ifThenElse(Arg2() == Param(0), Param(255), Arg1() * Param(0.2))
                     );
    */

    #ifdef __DEBUG__
      printf("--- seeded region growing\n");
    #endif

    vigra::ArrayOfRegionStatistics<SRGDirectValueFunctor<double, -1> > gradstat(max_region_label);

    labels = 0;
    seededRegionGrowing(srcImageRange(timg), srcImage(labels2),
                        destImage(labels), gradstat, KeepContours);

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels), vigra::ImageExportInfo(filepath_export_voronoi.c_str()));
    #endif

    //vigra::ArrayOfRegionStatistics<vigra::FindROISize<label_value_type> > wsroisize(max_region_label);
    //inspectTwoImages(srcImageRange(labels), srcImage(labels), wsroisize);

    int bin_region_label =
      labelImageWithBackground(srcImageRange(img_bin), destImage(labels2), false, background);

    //regionImageToEdgeImage(srcImageRange(labels), destImage(img_bin),
    //                       vigra::NumericTraits<image_value_type>::zero());

    //holeFilling(img_bin, true, background, foreground);

    /*
    ImageMaskContainer8 container(img, img_bin);
    container.markObjects(RED, false, false);




    typedef vigra::IImage::traverser SrcIterator;
    typedef vigra::BImage::traverser DestIterator;
    typedef vigra::BRGBImage::traverser IllIterator;

    typedef vigra::IImage::Accessor SrcAccessor;
    typedef vigra::BImage::Accessor DestAccessor;
    typedef vigra::BRGBImage::Accessor IllAccessor;

    SrcIterator sul(labels.upperLeft());
    SrcIterator slr(labels.lowerRight());
    SrcAccessor sa(labels.accessor());

    SrcIterator rul(labels2.upperLeft());
    SrcAccessor ra(labels2.accessor());

    DestIterator dul(img_bin.upperLeft());
    DestAccessor da(img_bin.accessor());

    IllIterator iul(container.img_rgb.upperLeft());
    IllAccessor ia(container.img_rgb.accessor());

    vigra::BRGBImage::value_type ill_marker = YELLOW;


    //     findSplits(labels.upperLeft(), labels.lowerRight(), labels.accessor(),
    //            labels2.upperLeft(), labels.accessor(),
    //            img_bin.upperLeft(), img_bin.accessor(),
    //            container.img_rgb.upperLeft(), container.img_rgb.accessor(),
    //            vigra::NumericTraits<image_value_type>::zero(),
    //            YELLOW);

    int ws = slr.x - sul.x;
    int hs = slr.y - sul.y;
    int x,y;

    static const vigra::Diff2D right(1,0);
    static const vigra::Diff2D left(-1,0);
    static const vigra::Diff2D bottomright(1,1);
    static const vigra::Diff2D bottom(0,1);
    static const vigra::Diff2D top(0,-1);

    SrcIterator iy = sul;
    SrcIterator ry = rul;
    DestIterator dy = dul;
    IllIterator ly = iul;

    //typedef boost::property<boost::name_t, int> vertex_property;
    typedef boost::adjacency_list<boost::setS, boost::vecS, boost::undirectedS> graph_type;

    typedef std::map<int, graph_type> graph_map_type;

    graph_map_type graph_map;

    for (y=0; y<hs-1; ++y, ++iy.y, ++dy.y, ++ry.y, ++ly.y)
    {
      SrcIterator ix = iy;
      SrcIterator rx = ry;
      DestIterator dx = dy;
      IllIterator lx = ly;

      for (x=0; x<ws-1; ++x, ++ix.x, ++dx.x, ++rx.x, ++lx.x)
      {
        int orig_label = ra(rx);
        if (orig_label != 0)
        {
          int other = -1;
          int current = sa(ix);
          if (sa(ix, right) != current)
            other = sa(ix, right);
          else if (sa(ix, bottom) != current)
            other = sa(ix, bottom);

          if (other != -1)
          {
              ia.set(ill_marker, lx);
              add_edge(current, other, graph_map[orig_label]);
              //printf("%d: %d %d\n", orig_label, current, other);
          }
        }
      }

      if (sa(ix, bottom) != sa(ix))
      {
          ia.set(ill_marker, lx);
      }
    }

    SrcIterator ix = iy;
    DestIterator dx = dy;
    IllIterator lx = ly;
    for (x=0; x<ws-1; ++x, ++ix.x, ++dx.x, ++lx.x)
    {
      if (sa(ix, right) != sa(ix))
        ia.set(ill_marker, lx);
    }


    graph_map_type::iterator git = graph_map.begin();
    for (; git != graph_map.end(); ++git)
    {
      graph_type& g = (*git).second;
      int orig_label = (*git).first;

      printf("orig: %d\n", orig_label);

      boost::graph_traits<graph_type>::vertex_iterator vi, vi_end;
      boost::graph_traits<graph_type>::adjacency_iterator ai, ai_end;
      boost::property_map<graph_type, boost::vertex_index_t>::type index_map = get(boost::vertex_index, g);

      for (boost::tie(vi, vi_end) = vertices(g); vi != vi_end; ++vi)
      {
        boost::tie(ai, ai_end) = adjacent_vertices(*vi, g);
        if (ai != ai_end)
        {
          std::cout << get(index_map, *vi) << "  is parent of ";
          for (; ai != ai_end; ++ai)
            std::cout << get(index_map, *ai) << " ";
          std::cout << std::endl;
        }
      }
      printf("\n");
    }

*/



    transformImageIf(srcImageRange(labels), maskImage(img_bin), destImage(img_bin),
                     ifThenElse(Arg1() == Param(background),
                                Param(background),
                                Param(foreground))
                     );

    //max_region_label =
    //    labelImageWithBackground(srcImageRange(img_bin), destImage(labels2),
    //                             false, background);

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(img_bin), vigra::ImageExportInfo(filepath_export_binws.c_str()));
      //exportImage(srcImageRange(container.img_rgb), vigra::ImageExportInfo(filepath_export_rgb.c_str()));
      //exportImage(srcImageRange(labels), vigra::ImageExportInfo(filepath_export_binws.c_str()));
    #endif




    #ifdef __DEBUG__
      printf("--- image container\n");
    #endif

    ImageMaskContainer8 container(img, img_bin, false);

    ImageMaskContainer8::ObjectMap::iterator obj_it = container.objects.begin();
    std::vector<unsigned> obj_idL;
    std::vector<std::string> obj_strL;
    for (; obj_it != container.objects.end(); ++obj_it)
    {
      obj_idL.push_back((*obj_it).first);
      obj_strL.push_back(num_to_string((*obj_it).first));
    }

    #ifdef __DEBUG_IMAGE_EXPORT__
      //container.showLabels(obj_idL, obj_strL);
      container.markObjects(obj_idL, RED, false, true);
      //container.exportRGB(filepath_export_rgb, "");
    #endif

    #ifdef __DEBUG__
      printf("--- object merge\n");
    #endif

    typedef vigra::triple<unsigned, unsigned, ROIObject> merged_type;
    std::vector<merged_type> mergedL;

    int size = obj_idL.size();
    for (int j=0; j < size-1; ++j)
    {
      unsigned id_j = obj_idL[j];

      #ifdef __DEBUG__
        printf("* %d\n", id_j);
      #endif

      const ROIObject& obj_j = container.objects[id_j];

      for (int i=j+1; i < size; ++i)
      {
        unsigned id_i = obj_idL[i];
        const ROIObject& obj_i = container.objects[id_i];

        int dist = (int)((obj_i.center + obj_i.roi.upperLeft) - (obj_j.center + obj_j.roi.upperLeft)).magnitude();
        //printf("moo %d %d - (%d,%d) (%d,%d) \n", dist, squaredRsize,
        //       obj_i.center.x, obj_i.center.y, obj_j.center.x, obj_j.center.y);

        if (dist < squaredRsize)
        {
          #ifdef __DEBUG__
            printf("  %d\n", id_i);
          #endif

          typedef ImageMaskContainer8::binary_type::traverser ImageIterator;

          vigra::Diff2D start_j = obj_j.crack_start2;
          vigra::CrackContourCirculator<ImageIterator> crack_j(container.img_binary.upperLeft() + start_j);
          vigra::CrackContourCirculator<ImageIterator> crackend_j(crack_j);
          bool found = false;
          typedef std::vector<vigra::Diff2D> point2d_vector;
          point2d_vector found_pointL;

          //bool diff_i_found = false, diff_j_found = false;
          //vigra::Diff2D diff_i_old, diff_j_old;
          //int diff_i_count = 0, diff_j_count = 0, diff_max = 4;

          do
          {
            vigra::Diff2D p_j = start_j + crack_j.pos();
            //container.img_rgb.accessor().set(RED, container.img_rgb.upperLeft() + start_j + crack_j.pos());
            vigra::Diff2D start_i = obj_i.crack_start2;
            vigra::CrackContourCirculator<ImageIterator> crack_i(container.img_binary.upperLeft() + start_i);
            vigra::CrackContourCirculator<ImageIterator> crackend_i(crack_i);

            //if (j == 2 or j == 6 or j == 7 or j == 8)
            //  printf("%d: %d,%d\n", j, crack_j.diff().x, crack_j.diff().y);

            do
            {
              vigra::Diff2D p_i = start_i + crack_i.pos();
              //container.img_rgb.accessor().set(GREEN, container.img_rgb.upperLeft() + start_i + crack_i.pos());
              int dist = (p_j - p_i).squaredMagnitude();

              if (dist < 4)
              {
                //printf("HEUREKA!\n");
                //printf("    (%d,%d) - (%d,%d)\n",crack_j.pos().x, crack_j.pos().y, crack_i.pos().x, crack_i.pos().y);
                #ifdef __DEBUG__
                  container.img_rgb[p_j] = YELLOW;
                  container.img_rgb[p_i] = YELLOW;
                #endif

                found = true;
                found_pointL.push_back(p_j);
                found_pointL.push_back(p_i);
              }

              //if (crack_i.diff() == diff_i_old)
              //  diff_i_count++;
              //else
              //  diff_i_count = 0;
              //if (diff_i_count > diff_max)
              //  diff_i_found = true;
              //diff_i_old = crack_i.diff();

            } while (++crack_i != crackend_i && !found);

            //if (crack_j.diff() == diff_j_old)
            //  diff_j_count++;
            //else
            //  diff_j_count = 0;
            //if (diff_j_count > diff_max)
            //  diff_j_found = true;
            //diff_j_old = crack_j.diff();


            //container.img_rgb.accessor().set(YELLOW, container.img_rgb.upperLeft() + start_j);
            //container.img_rgb.accessor().set(YELLOW, container.img_rgb.upperLeft() + start_i);

          } while (++crack_j != crackend_j && !found);

          if (found)
          {
            //#ifdef __DEBUG__
            //  printf("%d - %d (j-i)  HEUREKA\n", id_j, id_i);
            //  printf("  diff: j %d, i %d\n", diff_j_found, diff_i_found);
            //#endif

            unsigned id_ij = id_j;
            //found_pointL.unique();
            //ImageLabelContainer8::value_type value_sum = vigra::NumericTraits<ImageLabelContainer8::value_type>::zero();
            //ImageLabelContainer8::value_type value_square_sum = vigra::NumericTraits<ImageLabelContainer8::value_type>::zero();

            ImageMaskContainer8::label_type img_new_labels(container.img_labels.size());
            copyImage(srcImageRange(container.img_labels), destImage(img_new_labels));
            transformImageIfLabel(srcImageRange(img_new_labels),
                                  maskImage(img_new_labels),
                                  destImage(img_new_labels),
                                  id_i,
                                  Param(id_ij));

            // fill the gap between objects
            point2d_vector::iterator point_it = found_pointL.begin();
            for (; point_it != found_pointL.end(); ++point_it)
              img_new_labels[*point_it] = id_ij;

            // look for remaining gap-pixels to fill (in neighborhood of the watershed-line)
            const int neighborhood = 8;
            for (point_it = found_pointL.begin(); point_it != found_pointL.end(); ++point_it)
            {
              for (int ni=0; ni < neighborhood; ++ni)
                if (img_new_labels[*point_it + NEIGHBORS[ni]] != id_ij)
                {
                  unsigned cnt_non_ij = 0;
                  for (int nj=0; nj < neighborhood; ++nj)
                    if (img_new_labels[*point_it + NEIGHBORS[ni] + NEIGHBORS[nj]] != id_ij)
                      cnt_non_ij++;
                  if (cnt_non_ij <= 2)
                    img_new_labels[*point_it + NEIGHBORS[ni]] = id_ij;
                }
            }


            // new bounding-box of merged object
            int roi_x1 = std::min(obj_j.roi.x, obj_i.roi.x);
            int roi_y1 = std::min(obj_j.roi.y, obj_i.roi.y);
            int roi_x2 = std::max(obj_j.roi.x + obj_j.roi.width,  obj_i.roi.x + obj_i.roi.width);
            int roi_y2 = std::max(obj_j.roi.y + obj_j.roi.height, obj_i.roi.y + obj_i.roi.height);
            vigra::Diff2D roi_ul(roi_x1, roi_y1);
            vigra::Diff2D roi_lr(roi_x2, roi_y2);

            double roisize_ij = obj_i.roisize + obj_j.roisize + found_pointL.size();
            vigra::Diff2D roicenter_ij = (obj_j.center + obj_i.center) / 2;

            double perimeter_ij = blockInspector<BlockPerimeter>(img_new_labels.upperLeft() + roi_ul,
                                  img_new_labels.upperLeft() + roi_lr,
                                  img_new_labels.accessor(), id_ij);
            double perimeter_i  = blockInspector<BlockPerimeter>(container.img_labels.upperLeft() + roi_ul,
                                  container.img_labels.upperLeft() + roi_lr,
                                  container.img_labels.accessor(), id_i);
            double perimeter_j  = blockInspector<BlockPerimeter>(container.img_labels.upperLeft() + roi_ul,
                                  container.img_labels.upperLeft() + roi_lr,
                                  container.img_labels.accessor(), id_j);

            double circ_ij = feature_circularity(perimeter_ij, roisize_ij);
            double circ_i  = feature_circularity(perimeter_i, obj_i.roisize);
            double circ_j  = feature_circularity(perimeter_j, obj_j.roisize);


            #ifdef __DEBUG__
              printf("  p_ij: %.2f  p_i: %.2f  p_j: %.2f\n", perimeter_ij, perimeter_i, perimeter_j);
              printf("  s_ij: %.2f  s_i: %.2f  s_j: %.2f\n", roisize_ij, obj_i.roisize, obj_j.roisize);
              printf("  c_ij: %.2f  c_i: %.2f  c_j: %.2f\n", circ_ij, circ_i, circ_j);
            #endif

            //if (circ_ij <= circ_j or circ_ij <= circ_i or
            //    (diff_i_found and diff_j_found and perimeter_i < 200 and perimeter_j < 200)
            //   )
            //if (circ_ij <= circ_j or circ_ij <= circ_i or
            //    (diff_i_found and diff_j_found and (obj_i.roisize < 50 or obj_j.roisize < 50))
            //   )
            if (!(circ_i < circ_ij || circ_j < circ_ij) ||
                obj_i.roisize < iMinMergeSize || obj_j.roisize < iMinMergeSize
               )
            {
              #ifdef __DEBUG__
                printf("  MERGE!\n");
              #endif

              copyImageIfLabel(img_new_labels.upperLeft() + roi_ul,
                               img_new_labels.upperLeft() + roi_lr,
                               img_new_labels.accessor(),
                               img_new_labels.upperLeft() + roi_ul,
                               img_new_labels.accessor(),
                               container.img_labels.upperLeft() + roi_ul,
                               container.img_labels.accessor(),
                               id_ij);

              // store merged obj data

              vigra::Diff2D crackstart_ij = findCrackStart(container.img_labels.upperLeft() + roi_ul,
                                                           container.img_labels.upperLeft() + roi_lr,
                                                           container.img_labels.accessor(),
                                                           id_ij);

              ROIObject obj_ij(roi_ul, roi_lr, roicenter_ij, crackstart_ij, crackstart_ij, roisize_ij);
              mergedL.push_back(merged_type(id_i, id_j, obj_ij));
            }

            #ifdef __DEBUG__
              printf("\n");
            #endif
          }

        } // if

      } // for i
    } // for j

    #ifdef __DEBUG_IMAGE_EXPORT__
      container.exportRGB(filepath_export_rgb, "");
    #endif

    // modify the objects...
    std::vector<merged_type>::iterator it_merged = mergedL.begin();
    for (; it_merged != mergedL.end(); ++it_merged)
    {
      unsigned& id_erase =  (*it_merged).first;
      unsigned& id_insert = (*it_merged).second;
      ROIObject& obj_insert = (*it_merged).third;

      #ifdef __DEBUG__
        printf("* erase: %d  insert/update: %d \n", id_erase, id_insert);
      #endif
      container.objects.erase(id_erase);
      container.objects[id_insert] = obj_insert;
    }

    #ifdef __DEBUG__
      printf("moo erase1\n");
    #endif

    transformImage(srcImageRange(container.img_labels),
                   destImage(container.img_binary),
                   ifThenElse(Arg1() == Param(0), Param(0), Param(255))
                   );

    #ifdef __DEBUG__
      printf("moo erase2\n");
    #endif


    // do some hole-filling
    holeFilling(container.img_binary, false, background, foreground);


    #ifdef __DEBUG_IMAGE_EXPORT__
      container.img_rgb = BLACK;
      container.markObjects(RED, false, true, false, true);
      container.exportRGB(filepath_export_rgb_merged, "");
      container.exportBinary(filepath_export_binary_merged, "");
    #endif

    #ifdef __DEBUG__
      printf("moo erase3\n");
    #endif

    if (filepath_rgb != "")
    {
      //container.makeRGB();
      //copyImage(srcImageRange(img_rgb), destImage(container.img_rgb));
      //container2.markObjects(WHITE, false, true, false, true);
      //container2.exportRGB(filepath_rgb, "");
    }

    copyImage(container.img_binary.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              container.img_binary.lowerRight() - vigra::Diff2D(mem_border, mem_border),
              container.img_binary.accessor(),
              bin_out.upperLeft(),
              bin_out.accessor());

    #ifdef __DEBUG__
      printf("moo erase4\n");
    #endif

    #ifdef __DEBUG__
      printf("StopWatch: final %.3fs\n", oStopWatchTotal.measure());
    #endif
    oStopWatch.reset();
  }





  ImageMaskContainer<8>
  testPreSegmentation(std::string filepath_img, std::string filepath_msk, std::string filepath_rgb, int channel)
  {
    typedef ImageMaskContainer<8> ImageMaskContainer8;
    typedef ImageMaskContainer8::label_type::value_type label_value_type;
    typedef ImageMaskContainer8::image_type::value_type image_value_type;
    typedef ImageMaskContainer8::binary_type::value_type binary_value_type;

    std::string filepath_base = filepath_img.substr(0, filepath_img.size()-4);
    std::string filepath_export_rgb           = filepath_base + "__seg.png";
    std::string filepath_export_rgb_merged    = filepath_base + "__seg_merged.png";

    int squaredRsize = 1600;


    ImageMaskContainer8 container(filepath_img, filepath_msk, channel, false);

    ImageMaskContainer8::ObjectMap::iterator obj_it = container.objects.begin();
    std::vector<unsigned> obj_idL;
    std::vector<std::string> obj_strL;
    for (; obj_it != container.objects.end(); ++obj_it)
    {
      obj_idL.push_back((*obj_it).first);
      obj_strL.push_back(num_to_string((*obj_it).first));
    }

    #ifdef __DEBUG_IMAGE_EXPORT__
      //container.showLabels(obj_idL, obj_strL);
      container.markObjects(obj_idL, RED, false, true);
      //container.exportRGB(filepath_export_rgb, "");
    #endif


    typedef vigra::triple<unsigned, unsigned, ROIObject> merged_type;
    std::vector<merged_type> mergedL;

    for (int j=0; j < obj_idL.size()-1; j++)
    {
      unsigned id_j = obj_idL[j];
      printf("* %d\n", id_j);
      const ROIObject& obj_j = container.objects[id_j];

      for (int i=j+1; i < obj_idL.size(); i++)
      {
        unsigned id_i = obj_idL[i];
        const ROIObject& obj_i = container.objects[id_i];

        if (((obj_i.center + obj_i.roi.upperLeft) - (obj_j.center + obj_j.roi.upperLeft)).squaredMagnitude() < squaredRsize)
        {
          printf("  %d\n", id_i);

          typedef ImageMaskContainer8::binary_type::traverser ImageIterator;

          vigra::Diff2D start_j = obj_j.roi.upperLeft + obj_j.crack_start;
          vigra::CrackContourCirculator<ImageIterator> crack_j(container.img_binary.upperLeft() + start_j);
          vigra::CrackContourCirculator<ImageIterator> crackend_j(crack_j);
          bool found = false;
          typedef std::vector<vigra::Diff2D> point2d_vector;
          point2d_vector found_pointL;

          do
          {
            vigra::Diff2D p_j = start_j + crack_j.pos();
            //container.img_rgb.accessor().set(RED, container.img_rgb.upperLeft() + start_j + crack_j.pos());
            vigra::Diff2D start_i = obj_i.roi.upperLeft + obj_i.crack_start;
            vigra::CrackContourCirculator<ImageIterator> crack_i(container.img_binary.upperLeft() + start_i);
            vigra::CrackContourCirculator<ImageIterator> crackend_i(crack_i);

            do
            {
              vigra::Diff2D p_i = start_i + crack_i.pos();
              //container.img_rgb.accessor().set(GREEN, container.img_rgb.upperLeft() + start_i + crack_i.pos());
              int dist = (p_j - p_i).squaredMagnitude();

              if (dist < 4)
              {
                //printf("HEUREKA!\n");
                //printf("    (%d,%d) - (%d,%d)\n",crack_j.pos().x, crack_j.pos().y, crack_i.pos().x, crack_i.pos().y);
                container.img_rgb[p_j] = YELLOW;
                container.img_rgb[p_i] = YELLOW;
                found = true;
                found_pointL.push_back(p_j);
                found_pointL.push_back(p_i);
              }
            } while (++crack_i != crackend_i);

            //container.img_rgb.accessor().set(YELLOW, container.img_rgb.upperLeft() + start_j);
            //container.img_rgb.accessor().set(YELLOW, container.img_rgb.upperLeft() + start_i);

          } while (++crack_j != crackend_j);

          if (found)
          {
            printf("%d - %d (j-i)  HEUREKA\n", id_j, id_i);
            unsigned id_ij = id_j;
            //found_pointL.unique();
            //ImageLabelContainer8::value_type value_sum = vigra::NumericTraits<ImageLabelContainer8::value_type>::zero();
            //ImageLabelContainer8::value_type value_square_sum = vigra::NumericTraits<ImageLabelContainer8::value_type>::zero();

            ImageMaskContainer8::label_type img_new_labels(container.img_labels.size());
            copyImage(srcImageRange(container.img_labels), destImage(img_new_labels));
            transformImageIfLabel(srcImageRange(img_new_labels),
                                  maskImage(img_new_labels),
                                  destImage(img_new_labels),
                                  id_i,
                                  Param(id_ij));

            // fill the cap between objects
            point2d_vector::iterator point_it = found_pointL.begin();
            for (; point_it != found_pointL.end(); ++point_it)
              img_new_labels[*point_it] = id_ij;

            // look for remaining cap-pixels to fill (in neighborhood of the watershed-line)
            const int neighborhood = 8;
            for (point_it = found_pointL.begin(); point_it != found_pointL.end(); ++point_it)
            {
              for (int ni=0; ni < neighborhood; ni++)
                if (img_new_labels[*point_it + NEIGHBORS[ni]] != id_ij)
                {
                  unsigned cnt_non_ij = 0;
                  for (int nj=0; nj < neighborhood; nj++)
                    if (img_new_labels[*point_it + NEIGHBORS[ni] + NEIGHBORS[nj]] != id_ij)
                      cnt_non_ij++;
                  if (cnt_non_ij <= 2)
                    img_new_labels[*point_it + NEIGHBORS[ni]] = id_ij;
                }
            }


            // new bounding-box of merged object
            int roi_x1 = std::min(obj_j.roi.x, obj_i.roi.x);
            int roi_y1 = std::min(obj_j.roi.y, obj_i.roi.y);
            int roi_x2 = std::max(obj_j.roi.x + obj_j.roi.width,  obj_i.roi.x + obj_i.roi.width);
            int roi_y2 = std::max(obj_j.roi.y + obj_j.roi.height, obj_i.roi.y + obj_i.roi.height);
            vigra::Diff2D roi_ul(roi_x1, roi_y1);
            vigra::Diff2D roi_lr(roi_x2, roi_y2);

            double roisize_ij = obj_i.roisize + obj_j.roisize + found_pointL.size();
            vigra::Diff2D roicenter_ij = (obj_j.center + obj_i.center) / 2;

            double perimeter_ij = blockInspector<BlockPerimeter>(img_new_labels.upperLeft() + roi_ul,
                                  img_new_labels.upperLeft() + roi_lr,
                                  img_new_labels.accessor(), id_ij);
            double perimeter_i  = blockInspector<BlockPerimeter>(container.img_labels.upperLeft() + roi_ul,
                                  container.img_labels.upperLeft() + roi_lr,
                                  container.img_labels.accessor(), id_i);
            double perimeter_j  = blockInspector<BlockPerimeter>(container.img_labels.upperLeft() + roi_ul,
                                  container.img_labels.upperLeft() + roi_lr,
                                  container.img_labels.accessor(), id_j);

            double circ_ij = feature_circularity(perimeter_ij, roisize_ij);
            double circ_i  = feature_circularity(perimeter_i, obj_i.roisize);
            double circ_j  = feature_circularity(perimeter_j, obj_j.roisize);


            printf("  p_ij: %.2f  p_i: %.2f  p_j: %.2f\n", perimeter_ij, perimeter_i, perimeter_j);
            printf("  s_ij: %.2f  s_i: %.2f  s_j: %.2f\n", roisize_ij, obj_i.roisize, obj_j.roisize);
            printf("  c_ij: %.2f  c_i: %.2f  c_j: %.2f\n", circ_ij, circ_i, circ_j);


            if (circ_ij <= circ_j || circ_ij <= circ_i)
            {
              printf("  MERGE!\n");
              copyImageIfLabel(img_new_labels.upperLeft() + roi_ul,
                               img_new_labels.upperLeft() + roi_lr,
                               img_new_labels.accessor(),
                               img_new_labels.upperLeft() + roi_ul,
                               img_new_labels.accessor(),
                               container.img_labels.upperLeft() + roi_ul,
                               container.img_labels.accessor(),
                               id_ij);

              // store merged obj data

              vigra::Diff2D crackstart_ij = findCrackStart(container.img_labels.upperLeft() + roi_ul,
                                                           container.img_labels.upperLeft() + roi_lr,
                                                           container.img_labels.accessor(),
                                                           id_ij);

              ROIObject obj_ij(roi_ul, roi_lr, roicenter_ij, crackstart_ij, crackstart_ij, roisize_ij);
              mergedL.push_back(merged_type(id_i, id_j, obj_ij));
            }

            printf("\n");
          }

        } // if

      } // for i
    } // for j

    #ifdef __DEBUG_IMAGE_EXPORT__
      container.exportRGB(filepath_export_rgb, "");
    #endif

    // modify the objects...
    std::vector<merged_type>::iterator it_merged = mergedL.begin();
    for (; it_merged != mergedL.end(); ++it_merged)
    {
      unsigned& id_erase =  (*it_merged).first;
      unsigned& id_insert = (*it_merged).second;
      ROIObject& obj_insert = (*it_merged).third;

      printf("* erase: %d  insert/update: %d \n", id_erase, id_insert);
      container.objects.erase(id_erase);
      container.objects[id_insert] = obj_insert;
    }


    #ifdef __DEBUG_IMAGE_EXPORT__
      container.markObjects(obj_idL, RED, false, true, false, true);
      container.exportRGB(filepath_export_rgb_merged, "");
      //container.exportBinary(filepath_export_binary_merged, "");
    #endif

    if (filepath_rgb != "")
    {
      //container.makeRGB();
      //copyImage(srcImageRange(img_rgb), destImage(container.img_rgb));
      container.markObjects(obj_idL, WHITE, false, true, false, true);
      container.exportRGB(filepath_rgb, "");
    }

    copyImage(srcImageRange(container.img_labels), destImage(container.img_binary));

    return ImageMaskContainer8(container.img, container.img_binary, false);
  }



}

#endif // CECOG_SEGMENTATION
