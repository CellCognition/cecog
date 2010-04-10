/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Thomas Walter
// $Date$
// $Rev$
// $URL$


#ifndef MOMENTS_HXX_
#define MOMENTS_HXX_

namespace cecog{


    class Moments {

    public:
        typedef vigra::Diff2D argument_type;
        typedef double result_type;

        Moments()
        {
            isFirstPixel_ = true;
            reset();
        }

        void reset()
        {
            centralCalc_ = false;
            theta_ = 3 * M_PI;

            // 0th order
            m00 = 0;

            // first order
            m01 = 0;
            m10 = 0;

            // second order
            m02 = 0;
            m11 = 0;
            m20 = 0;

            // third order
            m03 = 0;
            m12 = 0;
            m21 = 0;
            m30 = 0;

            // central moments
            central00 = 0;

            central01 = 0;
            central10 = 0;

            central02 = 0;
            central20 = 0;
            central11 = 0;

            central30 = 0;
            central21 = 0;
            central12 = 0;
            central03 = 0;

        }

        void operator()(const argument_type & pixel)
        {
            if(isFirstPixel_)
            {
                center_x = pixel.x;
                center_y = pixel.y;
                isFirstPixel_ = false;
            }

            result_type pix_x = (result_type)pixel.x - center_x;
            result_type pix_y = (result_type)pixel.y - center_y;

            m00++;

            m10 += (result_type)pix_x;
            m01 += (result_type)pix_y;

            m20 += (result_type)(pix_x * pix_x);
            m02 += (result_type)(pix_y * pix_y);
            m11 += (result_type)(pix_x * pix_y);

            m30 += (result_type)(pix_x * pix_x * pix_x);
            m03 += (result_type)(pix_y * pix_y * pix_y);
            m21 += (result_type)(pix_x * pix_x * pix_y);
            m12 += (result_type)(pix_x * pix_y * pix_y);
        }

        void CalculatePrincipalMoments()
        {
            //CalculateCentralMoments(true);
            double theta = Theta();

            princ00 = central00;
            princ01 = - sin(theta) * central10 + cos(theta) * central01;
            princ10 = cos(theta) * central10 + sin(theta) * central01;

            princ20 = cos(theta) * cos(theta) * central20 +
                      2 * cos(theta) * sin(theta) * central11 +
                      sin(theta) * sin(theta) * central02;
            princ02 = sin(theta) * sin(theta) * central20 +
                      (-2) * cos(theta) * sin(theta) * central11 +
                      cos(theta) * cos(theta) * central02;
            princ11 = (-1) * cos(theta) * sin(theta) * central20 +
                             cos(theta) * cos(theta) * central11 +
                      (-1) * sin(theta) * sin(theta) * central11 +
                             cos(theta) * sin(theta) * central02 ;

            princ30 =     cos(theta) * cos(theta) * cos(theta) * central30 +
                      3 * cos(theta) * cos(theta) * sin(theta) * central21 +
                      3 * cos(theta) * sin(theta) * sin(theta) * central12 +
                          sin(theta) * sin(theta) * sin(theta) * central03;

            princ03 = (-1) * sin(theta) * sin(theta) * sin(theta) * central30 +
                        3  * cos(theta) * sin(theta) * sin(theta) * central21 +
                      (-3) * cos(theta) * cos(theta) * sin(theta) * central12 +
                             cos(theta) * cos(theta) * cos(theta) * central03;

            princ21 = (-1) * cos(theta) * cos(theta) * sin(theta) * central30 +
                             cos(theta) * cos(theta) * cos(theta) * central21 +
                      (-2) * cos(theta) * sin(theta) * sin(theta) * central21 +
                        2  * cos(theta) * sin(theta) * sin(theta) * central12 +
                      (-1) * sin(theta) * sin(theta) * sin(theta) * central12 +
                             cos(theta) * sin(theta) * sin(theta) * central03;

            princ12 =        cos(theta) * sin(theta) * sin(theta) * central30 +
                      (-2) * cos(theta) * cos(theta) * sin(theta) * central21 +
                             cos(theta) * cos(theta) * cos(theta) * central12 +
                             sin(theta) * sin(theta) * sin(theta) * central21 +
                      (-2) * cos(theta) * sin(theta) * sin(theta) * central12 +
                             cos(theta) * cos(theta) * sin(theta) * central03;

        }

        double PrincipalGyrationRadiusX()
        {
            return(sqrt(princ20 / princ00));
        }

        double PrincipalGyrationRadiusY()
        {
            return(sqrt(princ02 / princ00));
        }

        double PrincipalSkewnessX()
        {
            return(princ30 / pow(princ20, 1.5));
        }

        double PrincipalSkewnessY()
        {
            return(princ03 / pow(princ02, 1.5));
        }


        double SemiMajorAxis()
        {
            return(sqrt( 2 * (princ20 + princ02 +
                              sqrt( (princ20 - princ02) * (princ20 - princ02) +
                                    4.0 * princ11 * princ11) ) / princ00)  );
        }

        double SemiMinorAxis()
        {
            return(sqrt( 2 * (princ20 + princ02 -
                              sqrt( (princ20 - princ02) * (princ20 - princ02) +
                                    4.0 * princ11 * princ11) ) / princ00)  );
        }

        void CalculateCentralMoments(bool normalize)
        {
            center_x = m10 / m00;
            center_y = m01 / m00;

            central00 = m00;

            central01 = 0;
            central10 = 0;

            central20 = m20 - m00 * center_x *center_x;
            central02 = m02 - m00 * center_y *center_y;
            central11 = m11 - m00 * center_x * center_y;

            central30 = m30 - 3 * m20 * center_x +
                        2 * m00 * center_x * center_x * center_x;
            central03 = m03 - 3 * m02 * center_y +
                        2 * m00 * center_y * center_y * center_y;
            central21 = m21 - m20 * center_y - 2 * m11 * center_x +
                        2 * m00 * center_x * center_x * center_y;
            central12 = m12 - m02 * center_x - 2 * m11 * center_y +
                        2 * m00 * center_y * center_y * center_x;

            if(normalize)
            {
                // old : double normFactor = m00 / (central20 + central02);
                central00 = 1;

                // new:
                double temp = 1.0 / (double)(m00 * m00);
                // old: double temp = normFactor/m00;
                central20 = central20 * temp;
                central02 = central02 * temp;
                central11 = central11 * temp;

                // new:
                temp = 1.0/pow((double)m00, 2.5);
                // old: temp = pow(normFactor, 1.5)/m00;
                central12 = central12 * temp;
                central21 = central21 * temp;
                central30 = central30 * temp;
                central03 = central03 * temp;

            }

            centralCalc_ = true;

        }

        double Theta()
        {
            double phi=0.0;

            if(theta_ > 2*M_PI)
            {
                if( (central20 - central02) != 0)
                    phi = .5 * atan( 2.0 * central11 / (central20 - central02)  );
                else
                    phi = 0;

                // theta_ is initialised as 3 * M_PI
                // after calculation it lies between - M_PI/4 and M_PI/4
                if( (central11 == 0) && ( (central20 - central02) < 0) )
                    theta_ = M_PI / 2.0;
                if( (central11 > 0) && ( (central20 - central02) < 0) )
                    theta_ = phi + M_PI / 2.0;
                if( (central11 > 0) && ( (central20 - central02) == 0) )
                    theta_ = M_PI / 4.0;
                if( (central11 > 0) && ( (central20 - central02) > 0) )
                    theta_ = phi;
                if( (central11 == 0) && ( (central20 - central02) >= 0) )
                    theta_ = 0;
                if( (central11 < 0) && ( (central20 - central02) > 0) )
                    theta_ = phi;
                if( (central11 < 0) && ( (central20 - central02) == 0) )
                    theta_ = - M_PI / 4.0;
                if( (central11 < 0) && ( (central20 - central02) < 0) )
                    theta_ = phi - M_PI / 2.0;
            }
            return(theta_);
        }

        double Eccentricity()
        {
            return( ( (central20 - central02) * (central20 - central02) +
                       4.0 * central11 * central11) /
                    ( (central20 + central02) * (central20 + central02)) );
        }

        double GyrationRadius()
        {
            return(sqrt( (double)(central02 + central20)/(double)central00) );
        }

        result_type I1()
        {
            return( central20 + central02 );
        }

        result_type I2()
        {
            return( (central20 - central02) * (central20 - central02)
                    + 4 * central11 * central11);
        }

        result_type I3()
        {
            return( (central30 - 3 * central12) * (central30 - 3 * central12)
                    + (3 * central21 - central03) * (3 * central21 - central03));
        }

        result_type I4()
        {
            return( (central30 + central12) * (central30 + central12) +
                    (central21 + central03) * (central21 + central03) );
        }

        result_type I5()
        {
            result_type a = central30 - 3 * central12;
            result_type b = central30 + central12;
            result_type c = central21 + central03;
            result_type d = 3 * central21 - central03;
            return( a*b*(b*b - 3*c*c) + d*c*(3*b*b - c*c));
        }

        result_type I6()
        {
            result_type a = central20 - central02;
            result_type b = central30 + central12;
            result_type c = central21 + central03;
            return( a* (b * b - c * c) +
                    4 * central11 * b * c );
        }

        result_type I7()
        {
            result_type a = 3 * central21 - central03;
            result_type b = central30 + central12;
            result_type c = central21 + central03;
            result_type d = central30 - 3 * central12;
            return( a*b*( b*b - 3*c*c) - d*c*( 3*b*b - c*c)  );
        }

        // data
        result_type center_x, center_y;
        result_type m00, m01, m02, m03, m10, m11, m12, m20, m21, m30;
        result_type central00, central01, central10,
            central02, central11, central20,
            central30, central21, central12, central03;
        result_type princ00, princ01, princ10,
                    princ20, princ11, princ02,
                    princ30, princ21, princ12, princ03;

        bool isFirstPixel_;
        bool centralCalc_;
        double theta_;

    };
};
#endif /*MOMENTS_HXX_*/
