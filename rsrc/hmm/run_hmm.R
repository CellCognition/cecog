#                          The CellCognition Project
#                    Copyright (c) 2006 - 2010 Michael Held
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

print('Running HMM error correction...')

FILENAME_GRAPH_P = NULL
FILENAME_GRAPH_S = NULL

SORT_CLASSES_P = NULL
SORT_CLASSES_S = NULL

#WORKING_DIR
setwd(WORKING_DIR)

source('hmm.R')
source('hmm_report.R')

#FILENAME_MAPPING
#PATH_INPUT
#GROUP_BY_GENE
#GROUP_BY_OLIGOID
#TIMELAPSE
#MAX_TIME
#SINGLE_BRANCH
#GALLERIES

#PATH_OUT_P
#FILENAME_GRAPH_P
#REGION_NAME_P
#SORT_CLASSES_P
#CLASS_COLORS_P

#PATH_OUT_S
#FILENAME_GRAPH_S
#REGION_NAME_S
#SORT_CLASSES_S
#CLASS_COLORS_S

if (!is.null(FILENAME_GRAPH_P))
{
    graphP <- hmm.read.graph.structure(FILENAME_GRAPH_P)
    screenP <- read.screen(PATH_INPUT, FILENAME_MAPPING, REGION_NAME_P, graphP, singleBranch=SINGLE_BRANCH)

    if (screenP$nrOfPositions > 0)
    {
        class.colors <- CLASS_COLORS_P
        class.colors.hmm <- class.colors[graphP$h2o]

        probP <- read.probabilities(screenP)
        res = write.hmm.report(screenP, probP,
                         outdir=PATH_OUT_P,
                         graphP,
                         sortClasses=SORT_CLASSES_P,
                         groupByGene=GROUP_BY_GENE,
                         groupByOligoId=GROUP_BY_OLIGOID,
                         openHTML=FALSE,
                         timelapse=TIMELAPSE,
                         max_time=MAX_TIME,
                         write_decode=TRUE,
                         write_decode2=FALSE,
                         galleries=GALLERIES
                         )


if (!is.null(FILENAME_GRAPH_S))
{
    graphS <- hmm.read.graph.structure(FILENAME_GRAPH_S)
    screenS <- read.screen(PATH_INPUT, FILENAME_MAPPING, REGION_NAME_S, graphS, singleBranch=SINGLE_BRANCH)

    if (screenS$nrOfPositions > 0)
    {
        class.colors <- CLASS_COLORS_S
        class.colors.hmm <- class.colors[graphS$h2o]

        probS <- read.probabilities(screenS)
        write.hmm.report(screenS, probS,
                indices=res$overall_indices,
                outdir=PATH_OUT_S,
                graphS,
                sortClasses=SORT_CLASSES_S,
                groupByGene=GROUP_BY_GENE,
                groupByOligoId=GROUP_BY_OLIGOID,
                openHTML=FALSE,
                timelapse=TIMELAPSE,
                max_time=MAX_TIME,
                write_decode=TRUE,
                write_decode2=FALSE,
                galleries=GALLERIES
        )
    }
}
}
}