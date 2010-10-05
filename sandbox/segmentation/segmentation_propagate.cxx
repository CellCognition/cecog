 // Propagation segmentation based on image seeds.
 //
 // Based on CellProfiler's  'IdentifySecPropagateSubfunction.cpp'
 // Paper(s): 'Voronoi-Based Segmentation of Cells on Image Manifolds'
 //
 // Copyright 2003-2007 Thouis Jones, Michael Held
 // Distributed under the GNU General Public License


#include "vigra/impex.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/transformimage.hxx"
#include "vigra/functorexpression.hxx"

#include "cecog/thresholds.hxx"
#include "cecog/seededregion.hxx"
#include "cecog/readout.hxx"
#include "cecog/utilities.hxx"

int main(int argc, char** argv)
{
  using namespace cecog;

  vigra::ImageImportInfo infoImg(argv[1]);
  vigra::UInt8Image imgIn(infoImg.size());
  importImage(infoImg, destImage(imgIn));

  vigra::ImageImportInfo infoLabels(argv[2]);
  vigra::Int16Image imgLabelsIn(infoLabels.size());
  importImage(infoLabels, destImage(imgLabelsIn));

  vigra::Int16Image imgLabelsOut(infoLabels.size());

  vigra_precondition((infoImg.width() == infoLabels.width() && infoImg.height() == infoLabels.height()),
                     "Images must have same size!");


  double lambda = atof(argv[3]);
  int deltaWidth = atoi(argv[4]);
  int radius = atoi(argv[5]);
  float alpha = atof(argv[6]);
//  int t = atoi(argv[6]);
//  int rsize = atoi(argv[6]);
//  int limit = atoi(argv[7]);
//  int rsize2 = atoi(argv[8]);
//  int limit2 = atoi(argv[9]);


  vigra::UInt8Image imgInBinary(infoImg.size());
  vigra::UInt8Image imgInBinary2(infoImg.size());
  vigra::UInt8Image imgPre(infoImg.size());

  vigra::discMedian(srcImageRange(imgIn), destImage(imgPre), radius);
  //printf("%d\n", radius);
//  windowAverageThreshold(imgPre, imgInBinary, rsize, limit, true);
//  windowAverageThreshold(imgPre, imgInBinary2, rsize2, limit2, true);

//  using namespace vigra::functor;
//  vigra::combineTwoImages(srcImageRange(imgInBinary), srcImage(imgInBinary2),
//                          destImage(imgInBinary), max(Arg1(), Arg2()));

  typedef FindHistogram<vigra::UInt8> histogram;
  histogram f(255);
  vigra::inspectImage(srcImageRange(imgPre), f);
  int t = otsuThreshold(f.probabilities()) * alpha;
  printf("otsu t=%d\n", t);

  transformImage(srcImageRange(imgPre), destImage(imgInBinary),
                 vigra::Threshold<vigra::BImage::value_type, vigra::BImage::value_type>(t, 255, 0, 255));


  StopWatch stopwatch;
  segmentationPropagate(imgPre, imgInBinary, imgLabelsIn, imgLabelsOut, lambda, deltaWidth);
  stopwatch.print();

  vigra::BImage imgWatersheds(infoImg.size());
  using namespace vigra::functor;
  transformImage(srcImageRange(imgLabelsOut), destImage(imgWatersheds),
                 ifThenElse(Arg1() == Param(-1), Param(255), Param(0))
                 );

  vigra::BImage imgBLabelIn(infoImg.size());
  using namespace vigra::functor;
  transformImage(srcImageRange(imgLabelsIn), destImage(imgBLabelIn),
                 ifThenElse(Arg1() == Param(0), Param(0), Param(255))
                 );
  vigra::BImage imgBLabelOut(infoImg.size());
  using namespace vigra::functor;
  transformImage(srcImageRange(imgLabelsOut), destImage(imgBLabelOut),
                 ifThenElse(Arg1() == Param(0), Param(0), Param(255))
                 );

  vigra::BImage imgContours(infoImg.size());
  drawContour(srcImageRange(imgBLabelOut), destImage(imgContours), 255);

  typedef vigra::BasicImageView<unsigned char> BImageView;
  vigra::ArrayVector<BImageView> imageVector;
  imageVector.push_back(BImageView(imgIn.data(), imgIn.size()));
  imageVector.push_back(BImageView(imgBLabelOut.data(), imgBLabelOut.size()));
  imageVector.push_back(BImageView(imgBLabelIn.data(), imgBLabelIn.size()));
  imageVector.push_back(BImageView(imgWatersheds.data(), imgWatersheds.size()));



  vigra::ArrayVector<RGBValue> colorVector;
  colorVector.push_back(RGBValue(0,255,0));
  colorVector.push_back(RGBValue(255,0,0));
  colorVector.push_back(RGBValue(0,0,255));
  colorVector.push_back(RGBValue(255,255,255));

  vigra::ArrayVector<float> alphaVector;
  alphaVector.push_back(1.0);
  alphaVector.push_back(0.25);
  alphaVector.push_back(0.5);
  alphaVector.push_back(0.5);

  vigra::BRGBImage imgRGB = makeRGBImage(imageVector, colorVector, alphaVector);

  exportImage(srcImageRange(imgLabelsOut), vigra::ImageExportInfo("propagate.png"));
  exportImage(srcImageRange(imgInBinary), vigra::ImageExportInfo("propagate_in_binary.png"));
  exportImage(srcImageRange(imgRGB), vigra::ImageExportInfo("propagate_rgb.png"));
  exportImage(srcImageRange(imgPre), vigra::ImageExportInfo("propagate_pre.png"));

  return 0;
}
