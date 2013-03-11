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


#ifndef CECOG_CONTAINER
#define CECOG_CONTAINER

#include <map>
#include <string>

#include "vigra/impex.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/transformimage.hxx"
#include "vigra/labelimage.hxx"
#include "vigra/inspectimage.hxx"
#include "vigra/distancetransform.hxx"
#include "vigra/contourcirculator.hxx"
#include "vigra/localminmax.hxx"
#include "vigra/functorexpression.hxx"
#include "vigra/combineimages.hxx"
#include "vigra/contourcirculator.hxx"
#include "vigra/stdconvolution.hxx"
#include "vigra/convolution.hxx"
#include "vigra/tuple.hxx"
#include "vigra/pixelneighborhood.hxx"


#include "boost/config.hpp"
#include "boost/lexical_cast.hpp"

#include "cecog/shared_objects.hxx"
#include "cecog/thresholds.hxx"
#include "cecog/transforms.hxx"
#include "cecog/inspectors.hxx"
#include "cecog/math.hxx"
#include "cecog/features.hxx"
#include "cecog/font.hxx"
#include "cecog/images.hxx"
#include "cecog/utilities.hxx"
#include "cecog/config.hxx"

#include "cecog/basic/integral_images.hxx"
#include "cecog/morpho/basic.hxx"
#include "cecog/basic/moments.hxx"

namespace cecog
{
  using namespace vigra::functor;

  // FIXME: the nomenclature and processing of feature classes
  //        needs to be better organzied (feature classes directly depend
  //        on features to extract)
  static const unsigned FEATURE_COUNT = 12;
  static const std::string FEATURES[FEATURE_COUNT] =
    {"perimeter", "circularity",
     "irregularity","irregularity2", "axes",
     "normbase2", "normbase", "levelset",
     "roisize", "minmax"
    };


  /**
   * abstract base class
   * - organize the mapping from one graylevel image to a label image and its
   *   associated ROIs (ROIObject) by a mapping label ID->object (ObjectMap)
   * - extract features from ROIObjects (store as a map in every object)
   * - export RGB images for visualization of segmentation results
   * - export single objects to build a training set
   */
  template <int BIT_DEPTH>
  class ObjectContainerBase
  {
  public:
    typedef std::map<unsigned, ROIObject> ObjectMap;
    typedef Image<BIT_DEPTH> image_type;
    typedef vigra::BImage binary_type;
    typedef vigra::Int16Image label_type;
    typedef vigra::BRGBImage rgb_type;
    typedef vigra::BasicImageView<vigra::UInt8> image_view;
    typedef typename image_type::value_type value_type;
    typedef typename image_type::Histogram Histogram;
    typedef std::vector<image_view> ImageViews;
    typedef std::vector<vigra::BImage> ImageVector;
    typedef std::vector<vigra::Diff2D> PositionList;

    BOOST_STATIC_CONSTANT(typename image_type::value_type, BACKGROUND = 0);
    BOOST_STATIC_CONSTANT(typename image_type::value_type, FOREGROUND = 255);
    BOOST_STATIC_CONSTANT(unsigned, GREYLEVELS = image_type::PixelTypeTraits::greylevels);

    BOOST_STATIC_CONSTANT(unsigned, DEF_HARALICK_LEVELS = 32);
    BOOST_STATIC_CONSTANT(unsigned, DEF_HARALICK_DIST = 1);
    BOOST_STATIC_CONSTANT(unsigned, DEF_LEVELSET_LEVELS = 32);


    // constructor
    ObjectContainerBase()
        : font(Config::strFontFilepath),
        haralick_levels(DEF_HARALICK_LEVELS),
        haralick_distance(DEF_HARALICK_DIST),
        levelset_levels(DEF_LEVELSET_LEVELS),
        rgb_made(false),
        region_size(0),
        bRemoveBorderObjects(true)
    {
            // settings for granulometry
            granuSizeVec.push_back(1);
            granuSizeVec.push_back(2);
            granuSizeVec.push_back(3);
            granuSizeVec.push_back(5);
            granuSizeVec.push_back(7);

            required_ext = 0;

    };


    /**
     * Apply a feature by name to all objects of this container
     */
    int applyFeature(std::string name, bool force=false)
    {
      int feature_exist = 1;

      // check if feature is already calculated (or force recalc.)
      if (!calculated_features[name] || force)
      {
        // simple features

        if (name == "minmax")
        {
          vigra::ArrayOfRegionStatistics<vigra::FindMinMax
          <value_type> > functor(total_labels);
          inspectTwoImages(srcImageRange(img), srcImage(img_labels),
                           functor);
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ObjectMap::key_type id = (*it).first;
            ROIObject& o = (*it).second;
            o.features["min"] = FeatureValue(functor[id].min);
            o.features["max"] = FeatureValue(functor[id].max);
          }
        }
        else if (name == "roisize")
        {
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            o.features["roisize"] = o.roisize;
          }
        }
        // shape features
        else if (name == "perimeter")
        {
          // old: __blockFeature<BlockPerimeter>(name);
          // The problem of the BlockPerimeter functor is that it does not
          // ask whether the pixel is on the image border (-> segmentation fault)
          // for secondary objects, we do generally not remove objects touching
          // the borders.
          // The call is now according to the axes feature.
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            o.features["perimeter"] = (double)calculatePerimeter(
              img_labels.upperLeft(),
              img_labels.upperLeft(),
              img_labels.accessor(),
              o.roi.upperLeft,
              o.roi.lowerRight,
              (*it).first,
              width, height
            );
            //std::cout << o.features["perimeter"] << "  ";
          }
          //std::cout << std::endl;
        }
        else if (name == "axes")
        {
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            axes_4tuple tuple = calculateAxes(img_labels.upperLeft()+
                                              o.roi.upperLeft,
                                              img_labels.upperLeft()+
                                              o.roi.lowerRight,
                                              img_labels.accessor(),
                                              o.center,
                                              (*it).first);
            // dist_max is the maximal distance between the centre of
            // gravity and a border pixel; dist_min the minimal distance
            // analogously calculated.
            o.features["dist_max"] = tuple.first;
            o.features["dist_min"] = tuple.third;
            o.features["dist_ratio"] = tuple.third / tuple.first;
          }
        }
        if(name == "moments")
        {
          applyFeature("axes");

          vigra::ArrayOfRegionStatistics<Moments> moments(total_labels);

          vigra::inspectTwoImages(vigra::srcIterRange(vigra::Diff2D(0,0),
              vigra::Diff2D(0,0) + img_labels.size()),
              vigra::srcImage(img_labels), moments);

          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
              ObjectMap::key_type id = (*it).first;
              ROIObject& o = (*it).second;

              moments[id].CalculateCentralMoments(true);
              moments[id].CalculatePrincipalMoments();

              o.features["eccentricity"] = moments[id].Eccentricity();
              o.features["gyration_radius"] = moments[id].GyrationRadius();
              o.features["gyration_ratio"] = o.features["gyration_radius"]/o.features["dist_max"];
              o.features["moment_I1"] = moments[id].I1();
              o.features["moment_I2"] = moments[id].I2();
              o.features["moment_I3"] = moments[id].I3();
              o.features["moment_I4"] = moments[id].I4();
              o.features["moment_I5"] = moments[id].I5();
              o.features["moment_I6"] = moments[id].I6();
              o.features["moment_I7"] = moments[id].I7();
              o.features["ellip_major_axis"] = moments[id].SemiMajorAxis();
              o.features["ellip_minor_axis"] = moments[id].SemiMinorAxis();
              o.features["ellip_axis_ratio"] = o.features["ellip_minor_axis"] / o.features["ellip_major_axis"];
              o.features["princ_gyration_x"] = moments[id].PrincipalGyrationRadiusX();
              o.features["princ_gyration_y"] = moments[id].PrincipalGyrationRadiusY();
              o.features["princ_gyration_ratio"] = o.features["princ_gyration_y"] / o.features["princ_gyration_x"];
              o.features["skewness_x"] = fabs(moments[id].PrincipalSkewnessX());
              o.features["skewness_y"] = fabs(moments[id].PrincipalSkewnessY());
          }
        }
        else if (name == "circularity")
        {
          applyFeature("perimeter");
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            o.features[name] = feature_circularity(o.features["perimeter"], o.roisize);
          }
        }
        else if (name == "irregularity")
        {
          applyFeature("axes");
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            o.features[name] = feature_irregularity(o.features["dist_max"], o.roisize);
          }
        }
        else if (name == "irregularity2")
        {
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            double dist_avg, dist_stddev;
            averageCenterDistance(img_labels.upperLeft()+
                                  o.roi.upperLeft,
                                  img_labels.upperLeft()+
                                  o.roi.lowerRight,
                                  img_labels.accessor(),
                                  o.center,
                                  (*it).first,
                                  dist_avg,
                                  dist_stddev);
            o.features[name] = feature_irregularity(dist_avg, o.roisize);
          }
        }
        else if(name == "convexhull")
        {
          applyFeature("perimeter");

          ObjectMap::iterator it = objects.begin();
          for(; it != objects.end(); ++it)
          {
              ROIObject& o = (*it).second;
              ConvexHull<label_type, image_type> conv(img_labels, o, (*it).first);

              conv.CalculateFeatures(o);
          }
         }
         else if(name == "dynamics")
         {
            ObjectMap::iterator it = objects.begin();
            for(; it != objects.end(); ++it)
            {
                ROIObject &o = (*it).second;
                DynamicFeatures<image_type, label_type> dynMin(img, img_labels, o, (*it).first,
                                                               0, 20, "dyn_minima");
                dynMin.EraseMaximalValues();
                dynMin.CalculateFeatures(o);

                DynamicFeatures<image_type, label_type> dynMax(img, img_labels, o, (*it).first,
                                                               1, 20, "dyn_maxima");
                dynMax.EraseMaximalValues();
                dynMax.CalculateFeatures(o);
            }
         }
         else if(name == "distance")
          {
              ObjectMap::iterator it = objects.begin();
              for(; it != objects.end(); ++it)
              {
                  ROIObject &o = (*it).second;
                  DynamicDistanceFeatures<label_type>
                      dist(img_labels, o, (*it).first, 2);
                  dist.CalculateFeatures(o);

              }
          }
          else if(name == "granulometry")
            {
                ObjectMap::iterator it = objects.begin();
                for(; it != objects.end(); ++it)
                {
                    ROIObject &o = (*it).second;

                    Granulometry<image_type, label_type> granuOpen(img, img_labels, o, (*it).first,
                                                                   granuSizeVec, "granu_open", 0);
                    granuOpen.CalculateFeatures(o);

                    Granulometry<image_type, label_type> granuClose(img, img_labels, o, (*it).first,
                                                                   granuSizeVec, "granu_close", 1);
                    granuClose.CalculateFeatures(o);

                }
            }
        // haralick
        else if (name == "haralick")
        {
          char dStr[30];
          sprintf(dStr, "h%d_", haralick_distance);

          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            Haralick<image_type, label_type>
              haralick(img, img_labels,
                       o, (*it).first,
                       haralick_levels,
                       GREYLEVELS-1,
                       haralick_distance);

            o.features[std::string(dStr)+"ASM"] = haralick.ASM();
            o.features[std::string(dStr)+"IDM"] = haralick.IDM();
            o.features[std::string(dStr)+"CON"] = haralick.CON();
            o.features[std::string(dStr)+"VAR"] = haralick.VAR();
            o.features[std::string(dStr)+"PRO"] = haralick.PRO();
            o.features[std::string(dStr)+"SHA"] = haralick.SHA();
            o.features[std::string(dStr)+"COR"] = haralick.COR();
            o.features[std::string(dStr)+"SAV"] = haralick.SAV();
            o.features[std::string(dStr)+"DAV"] = haralick.DAV();
            o.features[std::string(dStr)+"SVA"] = haralick.SVA();
            o.features[std::string(dStr)+"ENT"] = haralick.ENT();
            o.features[std::string(dStr)+"SET"] = haralick.SET();
            o.features[std::string(dStr)+"COV"] = haralick.COV();
            o.features[std::string(dStr)+"average"] = haralick.avg();
            o.features[std::string(dStr)+"variance"] = haralick.var();
          }
        }
        // haralick 2 (object gray levels normalized)
        else if (name == "haralick2")
        {
          char dStr[30];
          sprintf(dStr, "h%d_2", haralick_distance);

          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            Haralick<image_type, label_type>
              haralick(img, img_labels,
                       o, (*it).first,
                       haralick_levels,
                       0,
                       haralick_distance);

            o.features[std::string(dStr)+"ASM"] = haralick.ASM();
            o.features[std::string(dStr)+"IDM"] = haralick.IDM();
            o.features[std::string(dStr)+"CON"] = haralick.CON();
            o.features[std::string(dStr)+"VAR"] = haralick.VAR();
            o.features[std::string(dStr)+"PRO"] = haralick.PRO();
            o.features[std::string(dStr)+"SHA"] = haralick.SHA();
            o.features[std::string(dStr)+"COR"] = haralick.COR();
            o.features[std::string(dStr)+"SAV"] = haralick.SAV();
            o.features[std::string(dStr)+"DAV"] = haralick.DAV();
            o.features[std::string(dStr)+"SVA"] = haralick.SVA();
            o.features[std::string(dStr)+"ENT"] = haralick.ENT();
            o.features[std::string(dStr)+"SET"] = haralick.SET();
            o.features[std::string(dStr)+"COV"] = haralick.COV();
            o.features[std::string(dStr)+"average"] = haralick.avg();
            o.features[std::string(dStr)+"variance"] = haralick.var();
          }
        }
        // normbase (object gray levels normalized)
        else if (name == "normbase")
        {
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            Normbase<image_type, label_type>
              normbase(img, img_labels,
                       o, (*it).first,
                       GREYLEVELS,
                       0);
            o.features["n_avg"]     = normbase.avg();
            o.features["n_stddev"]  = normbase.stddev();
            o.features["n_wavg"]    = normbase.wavg();
            o.features["n_wiavg"]   = normbase.wiavg();
            o.features["n_wdist"]   = normbase.wdist();
          }
        }
        // normbase2
        else if (name == "normbase2")
        {
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            Normbase<image_type, label_type>
              normbase(img, img_labels,
                       o, (*it).first,
                       GREYLEVELS,
                       GREYLEVELS-1);
            o.features["n2_avg"]     = normbase.avg();
            o.features["n2_stddev"]  = normbase.stddev();
            o.features["n2_wavg"]    = normbase.wavg();
            o.features["n2_wiavg"]   = normbase.wiavg();
            o.features["n2_wdist"]   = normbase.wdist();
          }
        }
        // Walker's Statistical Geometric Features
        else if (name == "levelset")
        {
          ObjectMap::iterator it = objects.begin();
          for (; it != objects.end(); ++it)
          {
            ROIObject& o = (*it).second;
            Levelset<image_type, label_type>
              levelset(img, img_labels,
                       o, (*it).first,
                       levelset_levels,
                       0);
            o.features.insert(levelset.values.begin(),
                              levelset.values.end());
          }
        }
        else
        {
          // not found!
          feature_exist = 0;
        }
      }

      // remember already calculated features
      if (feature_exist)
      {
        if (name != "haralick" && name != "haralick2")
          //    name += unsigned_to_string(haralick_distance);
          calculated_features[name] = true;
      }

      return feature_exist;
    }

    /**
     * RGB export image: initialize 'img_rgb' by base image 'img'
     */
    inline
    void eraseRGB()
    {
      img_rgb = BLACK;
    }

    void addExtraImage(vigra::BImage const imgExtra)
    {
      extra_img_vector.push_back(imgExtra);
    }

    /**
     * RGB export image: initialize 'img_rgb' by base image 'img'
     */
    inline
    void makeRGB(bool force=false)
    {
      if (!rgb_made || force)
      {
        eraseRGB();
        img_rgb = mergeRGB(img, img_rgb, 7);
        rgb_made = true;
      }
    }

    /**
     * RGB export image:
     * create a RGB image for display and export
     * combine the basic image (img) with extra channels (extra_img_vector)
     * flags (bit positions): 1 - red, 2 - green, 3 - blue
     * example: combineExtraRGB([1,0,6],[0.8,0,1.0])
     *          -> creates RGB image with basic img in red 80%,
     *             the first extra_img ignored and
     *             the second extra_img in green and blue 100%
     */
    void combineExtraRGB(std::vector<int> const &vFlag, std::vector<double> const &vAlpha)
    {
      rgb_made = true;
      double dAlpha;
      if (vFlag.size() > 0)
      {
        if (vFlag[0] != 0)
        {
          dAlpha = (vAlpha.size() > 0) ? vAlpha[0] : 1.0;
          img_rgb = mergeRGB(img, img_rgb, vFlag[0], dAlpha);
        }
      }
      for (int i=1, j=0; i < vFlag.size() && j < extra_img_vector.size(); i++, j++)
      {
        dAlpha = (vAlpha.size() > 0) ? vAlpha[i] : 1.0;
        img_rgb = mergeRGB(extra_img_vector[j], img_rgb, vFlag[i], dAlpha);
      }
    }

    /**
     * RGB export image:
     * draw ellipse at position (x,y) with radi (a,b)
     */
    void drawEllipse(int x, int y, int a, int b, RGBValue color=YELLOW,
                     bool force=false)
    {
      makeRGB(force);
      cecog::drawEllipse(x, y, a, b,
                        img_rgb.upperLeft(), img_rgb.accessor(), color);
    }

    /**
     * RGB export image:
     * visualize segmentation results for a set of object IDs
     */
    void markObjects(std::vector<unsigned> ids, RGBValue color=WHITE,
                     bool quad=false, bool showIds=false,
                     bool fill=false, bool force=false)
    {
      // FIXME: some stupid bugfix
      vigra::IImage imgLabels2(img_labels.size()+vigra::Diff2D(2,2));
      copyImage(this->img_labels.upperLeft(),
                this->img_labels.lowerRight(),
                this->img_labels.accessor(),
                imgLabels2.upperLeft() + vigra::Diff2D(1,1),
                imgLabels2.accessor());

      makeRGB(force);
      std::vector<unsigned>::iterator it = ids.begin();
      // loop over all object IDs
      for (; it != ids.end(); ++it)
        if (objects.count(*it))
        {
          // reference to object
          ROIObject& o = objects[*it];

          // draw object contour
          if (!fill)
            drawContourIfLabel(imgLabels2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(1,1),
                               imgLabels2.upperLeft()+o.roi.lowerRight+vigra::Diff2D(1,1),
                               imgLabels2.accessor(),
                               img_rgb.upperLeft()+o.roi.upperLeft,
                               img_rgb.accessor(),
                              *it, color, quad);
          // draw filled object
          else
            transformImageIfLabel(imgLabels2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(1,1),
                                  imgLabels2.upperLeft()+o.roi.lowerRight+vigra::Diff2D(1,1),
                                  imgLabels2.accessor(),
                                  imgLabels2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(1,1),
                                  imgLabels2.accessor(),
                                  img_rgb.upperLeft()+o.roi.upperLeft,
                                  img_rgb.accessor(),
                                  *it,
                                  Param(color)
                                  );

          // write the object ID at the upperleft corner
          if (showIds)
            font.write(img_rgb, o.roi.upperLeft,
                       unsigned_to_string(*it));

        }
        else
          std::cout << "no object with this id: " << unsigned(*it)
                    << std::endl;
    }

    /**
     * RGB export image:
     * visualize segmentation results for ALL objects
     */
    void markObjects(RGBValue color=WHITE,
                     bool quad=false, bool showIds=false,
                     bool fill=false, bool force=false)
    {
      std::vector<unsigned> idL;
      ObjectMap::iterator it = objects.begin();
      for (; it != objects.end(); ++it)
        idL.push_back((*it).first);
      markObjects(idL, color, quad, showIds, fill, force);
    }

    /**
     * RGB export image:
     * draws for every object one text-label to upperleft
     */
    void showLabels(std::vector<unsigned> ids,
                    std::vector<std::string> labels,
                    bool force=false)
    {
      makeRGB(force);
      std::vector<unsigned>::iterator oit = ids.begin();
      std::vector<std::string>::iterator lit = labels.begin();
      for (; oit != ids.end() && lit != labels.end(); ++oit, ++lit)
        if (objects.count(*oit))
        {
          ROIObject& o = objects[*oit];
          font.write(img_rgb, o.roi.upperLeft, *lit);
        }
        else
          std::cerr << "no object with this id: " << unsigned(*oit)
                    << std::endl;
    }

    template <class IMAGE>
    void drawLabelsByIds(std::vector<unsigned> const &ids,
                         IMAGE &imgOut)
    {
      std::vector<unsigned>::const_iterator oit = ids.begin();
      for (; oit != ids.end(); ++oit)
      {
        ROIObject& o = objects[*oit];
        font.write(imgOut, o.roi.upperLeft, unsigned_to_string(*oit));
      }
    }

    template <class IMAGE>
    void drawTextsByIds(std::vector<unsigned> const &ids,
                       std::vector<std::string> const &labels,
                       IMAGE &imgOut)
    {
      std::vector<unsigned>::const_iterator oit = ids.begin();
      std::vector<std::string>::const_iterator lit = labels.begin();
      for (; oit != ids.end() && lit != labels.end(); ++oit, ++lit)
      {
        ROIObject& o = objects[*oit];
        font.write(imgOut, o.roi.upperLeft, *lit);
      }
    }

    template <class IMAGE>
    void drawLabels(IMAGE &imgOut)
    {
      ObjectMap::iterator it = objects.begin();
      for (; it != objects.end(); ++it)
          font.write(imgOut, (it->second).roi.upperLeft, unsigned_to_string(it->first));
    }

    template <class IMAGE>
    void drawContoursByIds(std::vector<unsigned> ids, typename IMAGE::value_type color, IMAGE &imgOut,
                           bool quad=false, bool fill=false)
    {
      // FIXME: some stupid bugfix
      vigra::IImage imgLabels2(img_labels.size()+vigra::Diff2D(4,4));
      copyImage(this->img_labels.upperLeft(),
                this->img_labels.lowerRight(),
                this->img_labels.accessor(),
                imgLabels2.upperLeft() + vigra::Diff2D(2,2),
                imgLabels2.accessor());
      IMAGE imgOut2(imgOut.size()+vigra::Diff2D(4,4));
      copyImage(imgOut.upperLeft(),
                imgOut.lowerRight(),
                imgOut.accessor(),
                imgOut2.upperLeft() + vigra::Diff2D(2,2),
                imgOut2.accessor());
      std::vector<unsigned>::iterator it = ids.begin();
      // loop over all object IDs
      for (; it != ids.end(); ++it)
        if (objects.count(*it))
        {
          // reference to object
          ROIObject& o = objects[*it];

          // draw object contour
          if (!fill)
            drawContourIfLabel(imgLabels2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(2,2),
                               imgLabels2.upperLeft()+o.roi.lowerRight+vigra::Diff2D(2,2),
                               imgLabels2.accessor(),
                               imgOut2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(2,2),
                               imgOut2.accessor(),
                               *it, color, quad);
          // draw filled object
          else
            transformImageIfLabel(imgLabels2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(2,2),
                                  imgLabels2.upperLeft()+o.roi.lowerRight+vigra::Diff2D(2,2),
                                  imgLabels2.accessor(),
                                  imgLabels2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(2,2),
                                  imgLabels2.accessor(),
                                  imgOut2.upperLeft()+o.roi.upperLeft+vigra::Diff2D(2,2),
                                  imgOut2.accessor(),
                                  *it,
                                  Param(color)
                                  );
        }
        else
          std::cout << "no object with this id: " << unsigned(*it)
                    << std::endl;

      copyImage(imgOut2.upperLeft() + vigra::Diff2D(2,2),
                imgOut2.lowerRight() - vigra::Diff2D(2,2),
                imgOut2.accessor(),
                imgOut.upperLeft(),
                imgOut.accessor());
    }


    /**
     * RGB export image:
     * connect the center of two objects with a line
     */
    void connectObjects(unsigned id1, unsigned id2,
                        RGBValue color=RED, bool force=false)
    {
      if (objects.count(id1) && objects.count(id2))
      {
        makeRGB(force);
        ROIObject& o1 = objects[id1];
        ROIObject& o2 = objects[id2];
        vigra::Diff2D p1(o1.roi.upperLeft+o1.center);
        vigra::Diff2D p2(o2.roi.upperLeft+o2.center);
        cecog::drawLine(p1, p2,
                       img_rgb.upperLeft(), img_rgb.accessor(), color);
      }
      else
        std::cerr << "no object with ids: " << unsigned(id1)
                  << ", " << unsigned(id2)
                  << std::endl;
    }

    binary_type getBinary()
    {
      binary_type imgBin(img_labels.size());
      transformImageIf(srcImageRange(img_labels),
                       maskImage(img_labels),
                       destImage(imgBin),
                       Param(255));
      return imgBin;
    }

    label_type getLabels()
    {
      //label_type imgLabels(img_labels.size());
      //copyImage(srcImageRange(img_labels), destImage(imgLabels));
      return img_labels;
    }

    PositionList getCrackCoordinates(unsigned objId)
    {
      PositionList posList;
      ROIObject& obj = objects[objId];
      label_type limg(obj.roi.size+vigra::Diff2D(4,4));
      copyImageIfLabel(this->img_labels.upperLeft()+obj.roi.upperLeft,
                       this->img_labels.upperLeft()+obj.roi.lowerRight,
                       this->img_labels.accessor(),
                       this->img_labels.upperLeft()+obj.roi.upperLeft,
                       this->img_labels.accessor(),
                       limg.upperLeft() + vigra::Diff2D(2,2),
                       limg.accessor(),
                       objId);
      vigra::Diff2D anchor(obj.crack_start + vigra::Diff2D(2,2));
      vigra::CrackContourCirculator<label_type::Iterator> crack(limg.upperLeft() + anchor);
      vigra::CrackContourCirculator<label_type::Iterator> crackEnd(crack);
      //printf("\n crack start (%d,%d) %d\n", anchor.x, anchor.y, limg[anchor]);
      do
      {
        posList.push_back(obj.crack_start + crack.pos());
        //vigra::Diff2D np = obj.crack_start + crack.pos();
        //printf("  (%d,%d)  (%d,%d)\n", crack.pos().x, crack.pos().y, np.x, np.y);
      } while (++crack != crackEnd);
      return posList;
    }

    /**
     * RGB export image:
     * exports the image img_rgb
     */
    void exportRGB(std::string filepath,
                   std::string compression = "100",
                   bool force=false)
    {
      makeRGB(force);
      vigra::ImageExportInfo exp_info(filepath.c_str());
      exp_info.setCompression(compression.c_str());
      vigra::exportImage(srcImageRange(img_rgb), exp_info);
    }

    /**
     * exports the image
     */
    void exportImage(std::string filepath,
                     std::string compression = "100")
    {
      vigra::ImageExportInfo exp_info(filepath.c_str());
      exp_info.setCompression(compression.c_str());
      vigra::exportImage(srcImageRange(img), exp_info);
    }

    /**
     * exports the segmentation result (img_binary)
     */
    void exportBinary(std::string filepath,
                      std::string compression = "100")
    {
      vigra::ImageExportInfo exp_info(filepath.c_str());
      exp_info.setCompression(compression.c_str());
      vigra::exportImage(srcImageRange(img_binary), exp_info);
    }

    /**
     * export the label image
     */
    void exportLabelImage(std::string filepath,
                          std::string compression = "100")
    {
      vigra::ImageExportInfo exp_info(filepath.c_str());
      exp_info.setCompression(compression.c_str());
      vigra::exportImage(srcImageRange(img_labels), exp_info);
    }

    /**
     * exports a cropped version of img (input image).
     * and a cropped version of the segmentation result (here called mask).
     * for the mask, it is assured, that there is only the object with the ID objId.
     */
    void exportObject(ObjectMap::key_type objId,
                      std::string img_name,
                      std::string msk_name,
                      std::string compression = "100")
    {
      // add a border of 1 pixel arround object image & mask
      //const vigra::Diff2D ul_1px(-1,-1);
      //const vigra::Diff2D lr_1px(+1,+1);

      if (objects.count(objId))
      {
    	  // add a border of 1 pixel arround object image & mask
    	  // and fixes a segfault in vigra::exportImage
    	  int xul, yul, xlr, ylr;
    	  xul = (o.roi.upperLeft.x == 0) ? 0 : -1;
    	  yul = (o.roi.upperLeft.y == 0) ? 0 : -1;
    	  xlr = (o.roi.lowerRight.x == img.width()) ? 0 : 1;
    	  ylr = (o.roi.lowerRight.y == img.height()) ? 0 : 1;
    	  const vigra::Diff2D ul_1px(xul, yul);
    	  const vigra::Diff2D lr_1px(xlr, ylr);

      	ROIObject& o = objects[objId];

      	vigra::ImageExportInfo img_info(img_name.c_str());
      	img_info.setCompression(compression.c_str());

      	vigra::ImageExportInfo msk_info(msk_name.c_str());
      	msk_info.setCompression(compression.c_str());

        vigra::Diff2D ul = o.roi.upperLeft + ul_1px;
        vigra::Diff2D lr = o.roi.lowerRight + lr_1px;
        //printf("img: %d %d, %d %d, %d %d\n", t1.x, t1.y, t2.x, t2.y, img.width(), img.height());

        vigra::exportImage(img.upperLeft() + ul,
                           img.upperLeft() + lr,
                           img.accessor(),
                           img_info);
        //printf("done!\n");

        binary_type mask(o.roi.width+2, o.roi.height+2);

        typedef binary_type::value_type binary_value;

        copyImageIfLabel(img_binary.upperLeft() + ul,
                         img_binary.upperLeft() + lr,
                         img_binary.accessor(),
                         img_labels.upperLeft() + ul,
                         img_labels.accessor(),
                         mask.upperLeft(),
                         mask.accessor(),
                         objId);

        vigra::exportImage(srcImageRange(mask), msk_info);
      }
      else
        std::cout << "no object for this id: "
                  << ObjectMap::key_type(objId)
                  << std::endl;
    }

    /**
     * remove object by ID from the list of objects and
     *
     */
    void delObject(ObjectMap::key_type object_id)
    {
      objects.erase(object_id);
      transformImageIfLabel(srcImageRange(img_labels),
                            maskImage(img_labels),
                            destImage(img_labels),
                            object_id,
                            Param(0)
                            );
    }


//   void regionExpansion()
//    {
//
//    }

    /**
     * returns the number of objects initially calculated.
     */
    unsigned labelCount() { return total_labels; }

    /**
     * the current number of objects (items in ObjectMap).
     */
    unsigned size() { return objects.size(); }

    // FIXME: these attributes should be private

    // ObjectMap is std::map<unsigned, ROIObject>
    ObjectMap objects;

    // feature settings
    unsigned haralick_levels, haralick_distance, levelset_levels;

    // region properties
    unsigned region_size, width, height, required_ext;

    unsigned total_labels;

    // images
    image_type img, img_seg;
    binary_type img_binary;
    label_type img_labels;
    rgb_type img_rgb;


    // extra images needed for feature extraction in other channels
    // or for visualization using the combineExtraRGB-method
    // FIXME: concept be improved (especially for 5D data)
    ImageVector extra_img_vector;

    // flag indicating if border objects shall be removed in __buildObjects
    bool bRemoveBorderObjects;


  protected:

  /**
     * apply a functor to the image and write its features to ObjectMap
     */
    template <class FUNCTOR>
    void __inspectFeature(std::string featureName, FUNCTOR & functor)
    {
      inspectTwoImages(srcImageRange(img), srcImage(img_labels),
                       functor);
      ObjectMap::iterator it = objects.begin();
      for (; it != objects.end(); ++it)
      {
        ObjectMap::key_type id = (*it).first;
        ROIObject& o = (*it).second;
        o.features[featureName] = FeatureValue(functor[id]());
      }
    }


    template <template <typename, typename> class FUNCTOR>
    void __blockFeature(std::string name)
    {
      ObjectMap::iterator it = objects.begin();
      for (; it != objects.end(); ++it)
      {
        ROIObject& o = (*it).second;
        o.features[name] = blockInspector<FUNCTOR>
                           (img_labels.upperLeft() + o.roi.upperLeft,
                            img_labels.upperLeft() + o.roi.lowerRight,
                            img_labels.accessor(),
                            (*it).first);
      }
    }

    /**
     * create the object list (ObjectMap) from the label image.
     * ObjectMap(key, value) -> (object ID, object)
     */
    void _buildObjects(bool findCrack=true, bool removeSinglePixel=true)
    {
      vigra::ArrayOfRegionStatistics< vigra::FindBoundingRectangle >
        bounds(this->total_labels);
      inspectTwoImages(srcIterRange(vigra::Diff2D(0,0),
                                    vigra::Diff2D(0,0) +
                                    this->img_labels.size()),
                       srcImage(this->img_labels), bounds);

      vigra::ArrayOfRegionStatistics< FindAVGCenter >
        center(this->total_labels);
      inspectTwoImages(srcIterRange(vigra::Diff2D(0,0),
                                    vigra::Diff2D(0,0) +
                                    this->img_labels.size()),
                       srcImage(this->img_labels), center);

      vigra::ArrayOfRegionStatistics< vigra::FindROISize<value_type> >
        roisize(this->total_labels);
      inspectTwoImages(srcImageRange(this->img_labels),
                       srcImage(this->img_labels), roisize);

//      // FIXME: some stupid bugfix
//      vigra::IImage imgLabels2(img_labels.size()+vigra::Diff2D(2,2));
//      copyImage(this->img_labels.upperLeft(),
//                this->img_labels.lowerRight(),
//                this->img_labels.accessor(),
//                imgLabels2.upperLeft() + vigra::Diff2D(1,1),
//                imgLabels2.accessor());

      for (int i=1; i <= this->total_labels; ++i)
      {
        vigra::Diff2D ul = bounds[i].upperLeft;
        vigra::Diff2D lr = bounds[i].lowerRight;
        vigra::Diff2D diff = lr - ul;

        // check for border and size greater 1 pixel
        if ((!removeSinglePixel ||
			 (diff.x > 1 && diff.y > 1)) &&
            (!bRemoveBorderObjects ||
             (ul.x > this->region_size &&
              ul.y > this->region_size &&
              lr.x < this->img.width()-this->region_size &&
              lr.y < this->img.height()-this->region_size)
            )
           )
        {
          vigra::Diff2D cn = center[i]() - ul;
          vigra::Diff2D cs(0,0);
//          vigra::Diff2D cs2(0,0);
          if (findCrack)
          {
//            cs = findCrackStart(imgLabels2.upperLeft() + ul + vigra::Diff2D(1,1),
//                                imgLabels2.upperLeft() + lr + vigra::Diff2D(1,1),
//                                imgLabels2.accessor(), i);
            cs = findCrackStart(this->img_labels.upperLeft() + ul,
                                this->img_labels.upperLeft() + lr,
                                this->img_labels.accessor(), i);
          }
          this->objects[i] = ROIObject(ul, lr, cn, cs, roisize[i]());
        } else
          // delete not used objects from label image
          transformImageIfLabel(this->img_labels.upperLeft() + ul,
                                this->img_labels.upperLeft() + lr,
                                this->img_labels.accessor(),
                                this->img_labels.upperLeft() + ul,
                                this->img_labels.accessor(),
                                this->img_labels.upperLeft() + ul,
                                this->img_labels.accessor(),
                                i,
                                Param(0)
                                );
      }
    }

    // font for text labels
    Font font;
    bool rgb_made;

    // calculated_features stores the information if the feature has been
    // already calculated (look-up-table for LAZY calculation)
    std::map<std::string, bool> calculated_features;

    // the sizes for granulometry
    std::vector<unsigned> granuSizeVec;

  }; // end of ObjectContainerBase


  /**
   * subclass of ObjectContainerBase to perform segmentation and labeling
   * on gray level reference
   */
  template <int BIT_DEPTH>
  class ObjectContainer : public ObjectContainerBase<BIT_DEPTH>
  {
  public:
    typedef ObjectContainerBase<BIT_DEPTH> Base;
    typedef typename Base::image_type image_type;
    typedef typename Base::binary_type binary_type;
    typedef typename Base::value_type value_type;
    typedef typename Base::label_type label_type;
    typedef typename Base::rgb_type rgb_type;
    typedef typename Base::Histogram Histogram;
    typedef vigra::FImage tmap_type;
    using Base::GREYLEVELS;
    using Base::FOREGROUND;
    using Base::BACKGROUND;

    ObjectContainer(image_type const & img)
      : Base()
    {
      this->img = img;
      this->img_seg = img;
      this->img_binary = binary_type(img.size());
      this->img_labels = label_type(img.size());
      this->img_rgb = rgb_type(img.size());
      this->width = img.width();
      this->height = img.height();
      this->tmap = tmap_type(img.size());
    }


    /**
     * find a threshold automayically by applying a THRESHOLD_FUNCTOR to the
     * gray level histogram of the segmentation image (img_seg)
     */
    template <class THRESHOLD_FUNCTOR>
    unsigned char findThreshold()
    {
      THRESHOLD_FUNCTOR functor;
      Histogram histogram = this->img_seg.histogram();
      unsigned char threshold = functor(histogram.probabilities());

      #ifdef __DEBUG__
        std::cout << " maxv=" << int(histogram.max())
                  << " maxi=" << int(histogram.argmax())
                  << " t=" << int(threshold) << std::endl;
      #endif
      return threshold;
    }

    /**
     * threshold the segmentation image (img_seg) by applying a lower and an
     * upper threshold (values in between are mapped to binary image)
     */
    binary_type threshold(value_type t1,
                          value_type t2 = GREYLEVELS-1)
    {
      transformImage(srcImageRange(this->img_seg),
                     destImage(this->img_binary),
                     vigra::Threshold<value_type, value_type>
                       (t1, t2, 0, GREYLEVELS-1));
      return this->img_binary;
    }

    /**
     * local adatptive threshold by caching row and column averages
     */
    binary_type localThresholdCaching(unsigned region_size, value_type limit)
    {
      this->region_size = region_size;
      windowAverageThreshold(this->img_seg,
                             this->img_binary,
                             //tmap,
                             this->region_size, limit);
      return this->img_binary;
    }

    /**
     * local adaptive thresholding by integral images
     */
    binary_type localThresholdIntegral(unsigned int region_size, value_type limit)
    {
      this->region_size = region_size;
      ImLocalThreshold(this->img_seg,
                       this->img_binary,
                       vigra::Diff2D(region_size, region_size),
                       limit);
      return this->img_binary;
    }

    /**
     * double local adaptive thresholding by integral images:
     * the result is the union of two thresholdings with different
     * window sizes.
     */
    binary_type doubleLocalThreshold(int region_size1, value_type limit1,
                                     int region_size2, value_type limit2)
    {

        ImLocalThreshold(this->img_seg, this->img_binary,
                         vigra::Diff2D(region_size1, region_size1), limit1);

        binary_type temp(this->img_binary.size());
        ImLocalThreshold(this->img_seg, temp,
                         vigra::Diff2D(region_size2, region_size2), limit2);

        ImCompare(temp, this->img_binary, this->img_binary,
                  temp, this->img_binary,
                  IsGreater<value_type, value_type>());

        return this->img_binary;

    }

    /**
     * toggle mappings and median
     */
    void prefiltering(int toggle_mapping_size, int median_size)
    {
      using namespace morpho;
      #ifdef __DEBUG__
        std::cout << "ToggleMapping, size 1 + Median, size 2" << std::endl;
      #endif

      structuringElement2D se(WITHCENTER8, toggle_mapping_size);
      image_type temp((this->img_seg).size());

      // toggle mappings: type 2 is a fast erosion/dilation toggle mapping
      // is already quite fast, but can still be optimized (performance).
      ImToggleMapping(this->img_seg, temp, se, 2);
      vigra::discMedian(srcImageRange(temp),
                        destImage(this->img_seg),
                        median_size);
    }

    /**
     * Post processing: imin bin imout mean_thresh
     * removes all connected components from image bin, for which the
     * mean average in imin is lower than mean_thresh
     * slow implementation, should not be used in the final version.
     */
    void postProcessing(const int rsize, const double mean_thresh, std::string filepath)
    {
        // removes all connected components from bin
        // with a mean grey level of less than mean_thresh

        morpho::neighborhood2D nb(morpho::WITHOUTCENTER8, (this->img_seg).size());

        image_type bgsub((this->img_seg).size());
        label_type label((this->img_seg).size());

        ImBackgroundSubtraction(this->img, bgsub,
                                vigra::Diff2D(rsize, rsize));
        int maxLabel = ImLabel(this->img_binary, label, nb);

        vigra::ArrayOfRegionStatistics<vigra::FindAverage<value_type> >
                                                          avg(maxLabel);
        vigra::inspectTwoImages(srcImageRange(bgsub), srcImage(label), avg);

        typedef typename label_type::value_type label_value_type;

        std::vector<label_value_type> valToZero;
        valToZero.push_back(0);

        for(int i = 1; i<=maxLabel; ++i)
        {
            if(avg[i].average() < mean_thresh)
                valToZero.push_back(i);

        }

        DeleteListOfValues<label_value_type, value_type> f(valToZero, 0, 255);

        vigra::transformImage(srcImageRange(label), destImage(this->img_binary), f);
    }

    /**
     * label binary image by connected component analysis
     * (label 0: background, label >0: objects)
     * and build ObjectMap
     */
    binary_type label()
    {
      this->total_labels =
        labelImageWithBackground(srcImageRange(this->img_binary),
                                 destImage(this->img_labels),
                                 true, 0);

      this->_buildObjects();

      // build binary image from label image (set all !0 to 255)
      transformImageIf(srcImageRange(this->img_labels),
                       maskImage(this->img_labels),
                       destImage(this->img_binary),
                       Param(static_cast<typename binary_type::value_type>(FOREGROUND))
                       );

      //return this->img_labels;
      return this->img_binary;
    }

  private:
    tmap_type tmap;
  };



  /**
   * subclass of ObjectContainerBase to extract features from single
   * exported objects via the exportObject-method
   * (load pair of raw- and binary image)
   */
  template <int BIT_DEPTH>
  class SingleObjectContainer : public ObjectContainerBase<BIT_DEPTH>
  {
  public:
    typedef ObjectContainerBase<BIT_DEPTH> Base;
    typedef typename Base::image_type image_type;
    typedef typename Base::binary_type binary_type;
    typedef typename Base::value_type value_type;
    typedef typename Base::label_type label_type;
    typedef typename Base::rgb_type rgb_type;
    using Base::GREYLEVELS;

    SingleObjectContainer(std::string img_name,
                          std::string msk_name)
        : Base()
    {
      vigra::ImageImportInfo img_info(img_name.c_str());
      vigra::ImageImportInfo msk_info(msk_name.c_str());

      if (img_info.size() != msk_info.size())
        std::cerr << "size conflict of img and mask!"
        << std::endl;

      this->img = image_type(img_info.size());
      this->img_binary = binary_type(msk_info.size());

      importImage(img_info, destImage(this->img));
      importImage(msk_info, destImage(this->img_binary));

      this->img_seg = image_type(this->img.size());
      this->img_labels = label_type(this->img.size());
      this->img_rgb = rgb_type(this->img.size());

      this->width = this->img.width();
      this->height = this->img.height();
      if (this->img_binary.width() != this->width ||
          this->img_binary.height() != this->height)
        std::cerr << "size conflict of img and mask!"
        << std::endl;

      unsigned single_id = 1;
      this->total_labels = single_id;
      this->region_size = 0;
      this->bRemoveBorderObjects = false;

      // convert binary to label (e.g. 255 to 1)
      transformImageIf(srcImageRange(this->img_binary),
                       maskImage(this->img_binary),
                       destImage(this->img_labels),
                       Param(single_id)
                       );

      this->_buildObjects();
    }
  };

  /**
   * subclass of ObjectContainerBase to create an object container by loading
   * already segmented image data (pair raw/binary) from file (gray level or
   * RGB) or from varibale references (image_type/binary_type)
   */
  template <int BIT_DEPTH>
  class ImageMaskContainer : public ObjectContainerBase<BIT_DEPTH>
  {
  public:
    typedef ObjectContainerBase<BIT_DEPTH> Base;
    typedef typename Base::image_type image_type;
    typedef typename Base::binary_type binary_type;
    typedef typename Base::value_type value_type;
    typedef typename Base::label_type label_type;
    typedef typename Base::rgb_type rgb_type;
    using Base::GREYLEVELS;
    using Base::FOREGROUND;
    using Base::BACKGROUND;

    /**
     * load from file pair (RGB image, gray level image)
     */
    ImageMaskContainer(std::string img_filepath,
                       std::string msk_filepath,
                       int channel,
                       bool bRemoveBorderObjects=true)
        : Base()
    {
      this->bRemoveBorderObjects = bRemoveBorderObjects;

      vigra::ImageImportInfo img_info(img_filepath.c_str());
      vigra::ImageImportInfo msk_info(msk_filepath.c_str());

      this->img = image_type(img_info.size());
      this->img_binary = binary_type(msk_info.size());

      this->img_rgb = rgb_type(img_info.size());

      importImage(img_info, destImage(this->img_rgb));
      importImage(msk_info, destImage(this->img_binary));

      transformImage(srcImageRange(this->img_rgb),
                     destImage(this->img),
                     RGBChannelFunctor<vigra::BRGBImage::PixelType,
                       vigra::BImage::PixelType>(channel));

      __doLabeling();
    }

    /**
     * load from file pair (gray level image, grey level image)
     */
    ImageMaskContainer(std::string img_filepath,
                       std::string msk_filepath,
                       bool bRemoveBorderObjects=true)
        : Base()
    {
      this->bRemoveBorderObjects = bRemoveBorderObjects;

      vigra::ImageImportInfo img_info(img_filepath.c_str());
      vigra::ImageImportInfo msk_info(msk_filepath.c_str());

      this->img = image_type(img_info.size());
      this->img_binary = binary_type(msk_info.size());

      importImage(img_info, destImage(this->img));
      importImage(msk_info, destImage(this->img_binary));

      __doLabeling();
    }

    /**
     * load from const references: (gray level image, grey level image)
     */
    ImageMaskContainer(image_type const & img_in,
                       binary_type const & msk_in,
                       bool bRemoveBorderObjects=true
                       )
        : Base()
    {
      this->bRemoveBorderObjects = bRemoveBorderObjects;

      this->img        = img_in;
      this->img_binary = msk_in;

      __doLabeling();
    }


    // FIXME!
    ImageMaskContainer(vigra::BImage const & img_in,
                       binary_type const & msk_in,
                       bool bRemoveBorderObjects=true
                       )
        : Base()
    {
      this->bRemoveBorderObjects = bRemoveBorderObjects;

      this->img        = image_type(img_in.size());
      this->img_binary = msk_in;
      copyImage(srcImageRange(img_in), destImage(this->img));

      __doLabeling();
    }

    ImageMaskContainer(vigra::BImage const & imgIn,
                       label_type const & imgLabel,
                       bool bRemoveBorderObjects=true,
                       bool findCrack=true,
					   bool removeSinglePixel=true
                       )
        : Base()
    {
      this->bRemoveBorderObjects = bRemoveBorderObjects;

      this->img        = image_type(imgIn.size());
      copyImage(srcImageRange(imgIn), destImage(this->img));

      this->img_labels = imgLabel;

      if (this->img.size() != this->img_labels.size())
        std::cerr << "size conflict of img and labels!"
        << std::endl;

      this->img_seg = image_type(this->img.size());
      this->img_rgb = rgb_type(this->img.size());
      this->width = this->img.width();
      this->height = this->img.height();

      this->region_size = 0;
      vigra::FindMinMax<typename label_type::value_type> functor;
      inspectImage(srcImageRange(this->img_labels), functor);
      this->total_labels = functor.max;

      this->img_binary = binary_type(imgIn.size());
      transformImageIf(srcImageRange(this->img_labels),
                       maskImage(this->img_labels),
                       destImage(this->img_binary),
                       Param(static_cast<typename binary_type::value_type>(FOREGROUND))
                       );

      this->_buildObjects(findCrack, removeSinglePixel);
    }


  protected:
    void __doLabeling()
    {
      if (this->img.size() != this->img_binary.size())
        std::cerr << "size conflict of img and mask!"
        << std::endl;

//      // FIXME: in case we get an label-image (non-binary) as mask-image
//      transformImageIf(srcImageRange(this->img_binary),
//                       maskImage(this->img_binary),
//                       destImage(this->img_binary),
//                       Param(static_cast<typename binary_type::value_type>(FOREGROUND))
//                       );

      this->img_seg = image_type(this->img.size());
      this->img_labels = label_type(this->img.size());
      this->img_rgb = rgb_type(this->img.size());
      this->width = this->img.width();
      this->height = this->img.height();

      this->total_labels =
        labelImageWithBackground(srcImageRange(this->img_binary),
                                 destImage(this->img_labels), true, BACKGROUND);

      this->region_size = 0;

      this->_buildObjects();
    }
  };

}

#endif // CECOG_CONTAINER
