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
    int background_id = 0;
    unsigned max_region = 0;
    for (unsigned i = 1; i < background_roisize.size(); i++)
      if (background_roisize[i]() > max_region) {
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

  void segmentationCorrection(vigra::BImage const & img_in,
                              vigra::BImage const & bin_in,
                              vigra::BImage & bin_out,
                              int rsize,
                              int gauss_size, int maxima_size,
                              int iMinMergeSize,
                              SegmentationType segmentation_type=ShapeBasedSegmentation)

  {
    const int squaredRsize = 2*rsize;

    StopWatch oStopWatch, oStopWatchTotal;

#ifdef __DEBUG_IMAGE_EXPORT__
    //std::string filepath_base = filepath_img.substr(0, filepath_img.size()-4);
    std::string filepath_base = DEBUG_PREFIX;
    std::string filepath_export_original      = filepath_base + "__00original.tiff";
    std::string filepath_export_original_bin  = filepath_base + "__00originalbin.tiff";
    std::string filepath_export_inv           = filepath_base + "__01inv.png";
    std::string filepath_export_binary        = filepath_base + "__02bin.png";
    std::string filepath_export_min           = filepath_base + "__03min.png";
    std::string filepath_export_voronoi       = filepath_base + "__04voronoi.png";
    std::string filepath_export_binws         = filepath_base + "__05binws.png";
    std::string filepath_export_rgb           = filepath_base + "__06seg.png";
    std::string filepath_export_rgb_merged    = filepath_base + "__07seg_merged.png";
    std::string filepath_export_binary_merged = filepath_base + "__08bin_merged.png";
    std::string filepath_export_colmin           = filepath_base + "__09colmin.png";
    std::string filepath_export_ws_input           = filepath_base + "__10wsinput.png";
#endif

    typedef ImageMaskContainer<8> ImageMaskContainer8;
    typedef ImageMaskContainer8::label_type::value_type label_value_type;
    typedef ImageMaskContainer8::image_type::value_type image_value_type;
    typedef ImageMaskContainer8::binary_type::value_type binary_value_type;

    binary_value_type background = 0;
    binary_value_type foreground = 255;

    static const int mem_border = 10;
    int w = img_in.width();
    int h = img_in.height();
    int wx = w + 2*mem_border;
    int hx = h + 2*mem_border;

    ImageMaskContainer<8>::image_type img(wx, hx);

#ifdef __DEBUG_IMAGE_EXPORT__
	exportImage(srcImageRange(img_in), vigra::ImageExportInfo(filepath_export_original.c_str()));
#endif

    copyImage(img_in.upperLeft(),
              img_in.lowerRight(),
              img_in.accessor(),
              img.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              img.accessor());

    ImageMaskContainer8::binary_type img_bin(wx, hx);
	#ifdef __DEBUG_IMAGE_EXPORT__
    	exportImage(srcImageRange(bin_in), vigra::ImageExportInfo(filepath_export_original_bin.c_str()));
	#endif
    copyImage(bin_in.upperLeft(),
              bin_in.lowerRight(),
              bin_in.accessor(),
              img_bin.upperLeft() + vigra::Diff2D(mem_border, mem_border),
              img_bin.accessor());

    vigra::IImage labels(wx, hx), labels2(wx, hx);

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
      //transformImage(srcImageRange(fimg), destImage(timg),
      //               Arg1() + Param(0.1 * rand() / (RAND_MAX + 1.0)));
      // The addition of a random value aimed at making sure that there were not
      // maxima with equal values. Maxima with equal values posed a problem when implementing
      // the minimal distance condition via dilation (as below). But this strategy fails:
      // adding random values can actually generate new minima
      // it is partially reverted by the gaussian filtering.
      // and in addition, bimg is not a float image, so that it is completely unclear whether
      // this works.
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

    // FIXME:
    // the parameter maxima_size
    // should indicate the minimal distance between seeds.
    // First problem here: if two maxima are closer than maxima_size/2 but have
    // the same value, then both are kept.
    // Second problem: for large dilations, it is possible that different connected
    // connected components are influencing each other.
    // And in principle, this is not correct anyways, as slow slopes would also be detected
    // by this method. However, for distance functions, this should still be fine if maxima_size >= 2
    // (where maxima_size is the RADIUS of the Structuring Element).
    discDilation(srcImageRange(bimg), destImage(labels), maxima_size);

    combineTwoImagesIf(srcImageRange(bimg), srcImage(labels), maskImage(img_bin), destImage(labels2),
    				   ifThenElse(Arg1() < Arg2(),
    				   Param(background),
					   Arg2()));


    #ifdef __DEBUG__
      printf("StopWatch: disc dilation %.3fs\n", oStopWatch.measure());
    #endif
    oStopWatch.reset();


    // label the minima just found
    // note: we have to use 8 connected minima. If not, there can be 8-connected minima
    // each of which is a seed for the region growing.
    // as a consequence, the watershed line cannot be 4-connected, and therefore the bassins
    // (regions) have to be 4-connected (which is not the case). Therefore,
    // this leads to a documented error (github) of an existing separation, that does not
    // really separate two objects (because both objects and separating lines are 8-connected).
    int max_region_label =
      labelImageWithBackground(srcImageRange(labels2), destImage(labels2),
                               true, background);
    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels2), vigra::ImageExportInfo(filepath_export_min.c_str()));

      typedef vigra::BRGBImage rgb_type;
      rgb_type col = rgb_type(bimg.size());

      typedef vigra::RGBValue<unsigned char> rgb_val;
      rgb_val value = rgb_val(255, 0, 0);

      ImOverlayBinaryImage(vigra::srcImageRange(bimg), vigra::srcImage(labels2),
    		  	  	  	   vigra::destImage(col), value);
      exportImage(srcImageRange(col), vigra::ImageExportInfo(filepath_export_colmin.c_str()));

    #endif

// This is the original version (before 1.3.3): the watershed is applied on the original image.
// I.e. not on the gradient image and not on the distance map.
//    gaussianSmoothing(srcImageRange(img), destImage(timg), 1.0);
//
//    #ifdef __DEBUG_IMAGE_EXPORT__
//    	exportImage(srcImageRange(timg), vigra::ImageExportInfo(filepath_export_ws_input.c_str()));
//	#endif


    #ifdef __DEBUG__
      printf("--- seeded region growing\n");
    #endif

    // REGION GROWING:
    // gradstat gives back the cost of adding a pixel to a region.
    // Here we just use the pixel value in the input image for this.
    // Which means that it performs a watershed.
    vigra::ArrayOfRegionStatistics<SRGDirectValueFunctor<double, -1> > gradstat(max_region_label);

    // Initialization of the image labels
    labels = 0;

    // The vigra:: seededRegionGrowing with EightNeighborCode() is identical to
    // the cecog::seededRegionGrowing.
    vigra::seededRegionGrowing(srcImageRange(bimg), srcImage(labels2),
    						   destImage(labels), gradstat,
    						   vigra::KeepContours,
    						   vigra::EightNeighborCode());

    #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(labels), vigra::ImageExportInfo(filepath_export_voronoi.c_str()));
    #endif

    transformImageIf(srcImageRange(labels), maskImage(img_bin), destImage(img_bin),
                     ifThenElse(Arg1() == Param(background),
                                Param(background),
                                Param(foreground))
                     );

     #ifdef __DEBUG_IMAGE_EXPORT__
      exportImage(srcImageRange(img_bin), vigra::ImageExportInfo(filepath_export_binws.c_str()));
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
        if (dist < squaredRsize)
        {
          #ifdef __DEBUG__
            printf("  %d\n", id_i);
          #endif

          typedef ImageMaskContainer8::binary_type::traverser ImageIterator;

          vigra::Diff2D start_j = obj_j.crack_start + obj_j.roi.upperLeft;
          vigra::CrackContourCirculator<ImageIterator> crack_j(container.img_binary.upperLeft() + start_j);
          vigra::CrackContourCirculator<ImageIterator> crackend_j(crack_j);
          bool found = false;
          typedef std::vector<vigra::Diff2D> point2d_vector;
          point2d_vector found_pointL;
          do
          {
            vigra::Diff2D p_j = start_j + crack_j.pos();
            vigra::Diff2D start_i = obj_i.crack_start + obj_i.roi.upperLeft;
            vigra::CrackContourCirculator<ImageIterator> crack_i(container.img_binary.upperLeft() + start_i);
            vigra::CrackContourCirculator<ImageIterator> crackend_i(crack_i);

            do
            {
              vigra::Diff2D p_i = start_i + crack_i.pos();
              int dist = (p_j - p_i).squaredMagnitude();

              if (dist < 4) {
                #ifdef __DEBUG__
                  container.img_rgb[p_j] = YELLOW;
                  container.img_rgb[p_i] = YELLOW;
                #endif

                found = true;
                found_pointL.push_back(p_j);
                found_pointL.push_back(p_i);
              }
            } while (++crack_i != crackend_i && !found);
          } while (++crack_j != crackend_j && !found);

          if (found) {
            unsigned id_ij = id_j;
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
              for (int ni = 0; ni < neighborhood; ++ni)
                if (static_cast<unsigned>(img_new_labels[*point_it + NEIGHBORS[ni]]) != id_ij)
                {
                  unsigned cnt_non_ij = 0;
                  for (int nj = 0; nj < neighborhood; ++nj)
                    if (static_cast<unsigned>(img_new_labels[*point_it + NEIGHBORS[ni] + NEIGHBORS[nj]]) != id_ij)
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

              ROIObject obj_ij(roi_ul, roi_lr, roicenter_ij, crackstart_ij, roisize_ij);
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
}

#endif // CECOG_SEGMENTATION
