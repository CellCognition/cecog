#                          The CellCognition Project
#                    Copyright (c) 2006 - 2009 Michael Held
#                     Gerlich Lab, ETH Zurich, Switzerland
#                             www.cellcognition.org
#
#             CellCognition is distributed under the LGPL License.
#                       See trunk/LICENSE.txt for details.
#                See trunk/AUTHORS.txt for author contributions.
#
# Author(s): Bernd Fischer, Michael Held
# Date: $Date:$
# Revision: $Rev:$'
# Source: $URL:$'

FILENAME_GRAPH_P = NULL
FILENAME_GRAPH_S = NULL

SORT_CLASSES_P = NULL
SORT_CLASSES_S = NULL

source('hmm.R')
source('hmm_report.R')

#FILENAME_MAPPING
#PATH_INPUT
#PATH_OUTPUT
#GROUP_BY_GENE
#GROUP_BY_OLIGOID
#TIMELAPSE
#MAX_TIME

#FILENAME_GRAPH_P
#REGION_NAME_P
#SORT_CLASSES_P
#CLASS_COLORS_P

#FILENAME_GRAPH_S
#REGION_NAME_S
#SORT_CLASSES_S
#CLASS_COLORS_S

if (!is.null(FILENAME_GRAPH_P))
{
    graphP <- hmm.read.graph.structure(FILENAME_GRAPH_P)
    screenP <- read.screen(PATH_INPUT, FILENAME_MAPPING, REGION_NAME_P, graphP)

    if (screenP$nrOfPositions > 0)
    {
        class.colors <- CLASS_COLORS_P
        class.colors.hmm <- class.colors[graphP$h2o]

        probP <- read.probabilities(screenP)
        write.hmm.report(screenP, probP,
                         outdir=PATH_OUTPUT,
                         graphP,
                         sortClasses=SORT_CLASSES_P,
                         groupByGene=GROUP_BY_GENE,
                         groupByOligoId=GROUP_BY_OLIGOID,
                         openHTML=TRUE,
                         timelapse=TIMELAPSE,
                         max_time=MAX_TIME,
                         )
    }
}

if (!is.null(FILENAME_GRAPH_S))
{
    graphS <- hmm.read.graph.structure(FILENAME_GRAPH_S)
    screenS <- read.screen(PATH_INPUT, FILENAME_MAPPING, REGION_NAME_S, graphS)

    if (screenS$nrOfPositions > 0)
    {
        class.colors <- CLASS_COLORS_S
        class.colors.hmm <- class.colors[graphS$h2o]

        probS <- read.probabilities(screenS)
        write.hmm.report(screenS, probS,
                outdir=PATH_OUTPUT,
                graphS,
                sortClasses=SORT_CLASSES_S,
                groupByGene=GROUP_BY_GENE,
                groupByOligoId=GROUP_BY_OLIGOID,
                openHTML=TRUE,
                timelapse=TIMELAPSE,
                max_time=MAX_TIME,
        )
    }
}