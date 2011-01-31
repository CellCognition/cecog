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

library(hwriter)
library(igraph)
library(Cairo)

read.screen <- function(dir,filenameLayout,regionName,graph,fuseClasses=NULL,singleBranch=FALSE)
{
    screen <- list()
    screen$dir <- dir
    screen$layout <- read.delim(filenameLayout, as.is=TRUE)
    screen$nrOfPositions <- dim(screen$layout)[1]
    screen$nrOfCells <- 0
    screen$K <- graph$K
    screen$fuseClasses <- fuseClasses
    screen$regionName <- regionName
    nr <- screen$nrOfPositions
    for (i in 1:nr)
    {
        if (!is.null(screen$layout$Stage.position.nr))
            pos.name = "Stage.position.nr."
        else
            pos.name = "Position"
        pos = screen$layout[i, pos.name]
        #print(paste(pos, pos.name))
        if (is.numeric(pos))
            str.pos <- sprintf("%04d", as.numeric(pos))
        else
            str.pos = pos
        #path = paste(str.pos, "_tracking/_features_events", sep="/")
        #spath = paste(str.pos, "_tracking", sep="/")
        spath = paste(str.pos, "statistics", "events", sep="/")
        path = paste(dir, spath, sep="/")
        #print(paste(str.pos, path,file.exists(path)))
        if (file.exists(path))
        {
            filename <- list.files(path, paste(".*",regionName,".*",sep=""))
            if (singleBranch)
                filename = filename[grep('_B01_', filename)]
            #if (length(filename) > 0)
            {
                if (length(filename) > 0)
                  valid = rep(TRUE, length(filename))
                else
                {
                    filename = ""
                    valid = c(FALSE)
                }
                name <- filename
                tracking <- spath
                filename <- paste(spath, filename, sep="/")
                screen$nrOfCells <- screen$nrOfCells + length(filename)
                position <- rep(str.pos,length(filename))
                gene <- rep(screen$layout$GeneSymbol[i],length(filename))
                oligoid <- rep(screen$layout$OligoID[i],length(filename))
                cell <- data.frame(filename = filename, position = position,
                                   gene = gene, oligoid = oligoid,
                                   tracking = tracking, name = name,
                                   valid = valid)
                if (i == 1)
                    screen$cell <- cell
                else
                    screen$cell <- rbind(screen$cell,cell)
            } #else
            #    screen$nrOfPositions = screen$nrOfPositions - 1
        } else
            screen$nrOfPositions = screen$nrOfPositions - 1
    }
    return(screen)
}

hmm.read.graph.structure <- function(filename) {
  L <- readLines(filename)
  I <- grep("#",substr(L,1,1))
  if (length(I) > 0) {
    L <- L[-I]
  }
  graph <- list()
  i = 1
  while (!grepl("numberOfClasses",L[i])) {
    i <- i + 1
  }
  i <- i + 1
  C <- as.integer(L[i])
  graph$C <- C
  while (!grepl("numberOfHiddenStates",L[i])) {
    i <- i + 1
  }
  i <- i + 1
  K <- as.integer(L[i])
  graph$K <- K
  while (!grepl("startNodes",L[i])) {
    i <- i + 1
  }
  i <- i + 1
  st <- unlist(strsplit(L[i],split="[ \\t]"))
  I = nchar(st) > 0
  if (length(I) > 0) {
    st = st[I]
    graph$start <- rep(0,K)
    graph$start[as.integer(st)] = 1
  } else {
    graph$start[] = 1
  }

  graph$trans <- matrix(0,nr=K,nc=K)
  while (!grepl("transitionGraph",L[i])) {
    i <- i + 1
  }
  i <- i + 1
  while (!grepl("hiddenNodeToClassificationNode",L[i])) {
    sp <- strsplit(L[i],split="[ \\t]*->[ \\t]*")[[1]]
    if (length(sp) == 2) {
      sp1 <- unlist(strsplit(sp[[1]],split="[ \\t]*,[ \\t]*"))
      sp2 <- unlist(strsplit(sp[[2]],split="[ \\t]*,[ \\t]*"))
      graph$trans[as.integer(sp1),as.integer(sp2)] = 1
    }
    i <- i + 1
  }
  i <- i + 1
  graph$h2o <- rep(0,K)
  while (i <= length(L)) {
    sp <- strsplit(L[i],split="[ \\t(\t)]+")[[1]]
    graph$h2o[as.integer(sp[1])] = as.integer(sp[2])
    i <- i+1
  }

  graph$col <- sample(rainbow(graph$C))
  for (i in 1:graph$C) { graph$col[i] = substr(graph$col[i],1,7) }
  graph$name <- LETTERS[1:graph$C]
  graph$name.short <- LETTERS[1:graph$C]

  cat("number of classes ",graph$C,"\n")
  cat("number of hidden states ",graph$K,"\n")
  cat("start states ",graph$start,"\n")
  cat("allowed transitions:")
  print(graph$trans)
  cat("\nassociation from hidden to original classes ",graph$h2o,"\n")

  return(graph)
}

read.probabilities <- function(screen)
{
    T <- NULL
    K <- screen$K
    fuseClasses <- screen$fuseClasses
    n <- 0
    for (i in 1:screen$nrOfCells)
    {
        valid = screen$cell$valid[i]
        print(paste("Read file: ", screen$dir, "/", screen$cell$filename[i], ", valid=", valid, sep=" "))

        if (valid)
        {
        t <- read.delim(paste(screen$dir,"/",screen$cell$filename[i],sep=""), as.is=TRUE)

        if (is.null(T))
        {
          T = dim(t)[1]
            prob <- array(0,dim = c(screen$nrOfCells,T,K))
        }
        if (dim(t)[1] != T) {
            cat("ERROR: The number of time points in file ", screen$cell$filename[i], " is ", dim(t)[1],". Expected number of time points is ",T,"\n")
            stop()
        }

        for (j in 1:T)
        {
            Cstr <- t$class__probability[j]
            Cstr2 <- strsplit(Cstr,split=",")[[1]]
            C <- strsplit(Cstr2, split=":")
            Cs <- rep(0, K)
            for (n in 1:length(C))
                Cs[as.numeric(C[[n]][1])] <- as.numeric(C[[n]][2])
            p = rep(0,K)
            #k <- length(C)
            #if (k != K) {
            #    cat("ERROR: The number of classes in file ", screen$cell$filename[i], " number of classes is ", k,". Expected number of classes is ",K,"\n")
            #    stop()
            #}
            for (k in 1:K)
            {
                if (!is.null(fuseClasses) && k %in% fuseClasses[,2])
                {
                    k2 = fuseClasses[which(fuseClasses[,2] == k), 1]
                    #print(k)
                    #print(k2)
                }
                else
                    k2 = k
                p[k2] <- p[k2] + Cs[k]
            }
            prob[i,j,] <- p
        }
        }
    }
    return(prob)
}

read.features <- function(screen, name)
{
    T <- NULL
    features <- NULL
    n <- 0
    for (i in 1:screen$nrOfCells)
    {
        cat("Read file ", paste(screen$dir,"/",screen$cell$filename[i],sep=""), "\n")
        table <- read.delim(paste(screen$dir,"/",screen$cell$filename[i],sep=""), as.is=TRUE)

        if (is.null(T))
        {
            T <- dim(table)[1]
            features <- array(0, dim = c(screen$nrOfCells, T))
        }

        if (dim(table)[1] != T)
        {
            cat("ERROR: The number of time points in file ", screen$cell$filename[i], " is ", dim(t)[1],". Expected number of time points is ",T,"\n")
            stop()
        }
        features[i,] <- table[,name]
    }
    return(features)
}


plot.transition.graph <- function(hmm, loops=FALSE,type=NULL,filename=NULL,weights=TRUE)
{
    if (weights)
    {
        T <- hmm$trans
        K <- hmm$graph$K
    } else
    {
        T <- hmm$trans
        K <- hmm$K
    }
    #cat("start ", K,"\n")
    #cat("HMM=",length(hmm),"\n")
    #cat("filename",filename,"\n")
    #cat("weights",weights,"\n")
    if (!loops)
        diag(T) <- 0

    for (i in 1:K)
    {
        s <- sum(T[i,])
        if (s > 0)
            T[i,] <- T[i,] / s
    }
    if (weights)
    {
    #print(paste('moo',K))
        w.K = rep(1, K)
        for (i in 1:K)
        {
#            w.K[i] <- hmm$trans.raw[i,i]
            w.K[i] <- T[i,i]
        }
        s <- sum(w.K)
        if (abs(s) > 0.0) {
          w.K <- w.K / s
      }
    }
    isolation_threshold <- 1e-200
    I <- T > 0
    J <- hmm$start > 0
    M <- sum(I) + sum(J)
    el <- matrix(0,nr=M,nc=2)
    w <- rep(0,M,nc=2)
    z <- 0
    max.w <- c()
  #print(K)
    for (i in 1:K)
    {
        z.start <- z
        for (j in 1:K)
        {
            if (T[i,j] > 0.001)
            {
                z <- z + 1
                el[z,] <- c(i,j)
                w[z] <- T[i,j]
            }
        }
        if (z > z.start) {
            max.w <- append(max.w, which.max(w[z.start+1:z]) + z.start)
        }
        # FIXME: capturing isolated nodes (no outgoing edge)
        #if (sum(T[i,]) < isolation_threshold) {
        #  z <- z+1
        #  el[z,] <- c(i,i)
        #  w[z] <- 0
        #}
    }
    z.start <- z
  #print(K)
    for (i in 1:K)
    {
        if (hmm$start[i] > 0)
        {
            z <- z + 1
            el[z,] <- c(0,i)
            w[z] <- hmm$start[i]
        }
    }
    if (z > z.start)
        max.w <- append(max.w, which.max(w[z.start+1:z]) + z.start)

    #print(el)
    idx <- sort(w, index.return=TRUE)$ix
    el <- el[idx,]
    w <- w[idx]

    #print(el)

    g <- graph.edgelist(el,directed = TRUE)
    g$layout <- layout.circle
    w.col <- round(w * 256)
    w.col[w.col < 1] <- 1
    w.col[w.col > 256] <- 256
    if (!weights)
    {
        w[] = 1
        w.col[] = 256
        #w.col[] = 1
    }

    E(g)$color <- bwcol[w.col]
    #E(g)$color[max.w] <- 'red'
    V(g)$color <- c('#FFFFFF', class.colors.hmm)
    V(g)$frame.color <- 'black' #'transparent'#white

    #E(g)$width = 3 * w
    if (weights)
    {
        # mark the outgoing edges with highest prob. red (with the current weight)
        #E(g)$color[max.w] <- redcol[w.col[max.w]]
        #V(g)$size <- 80 * c(0, w.K) + 15
    }
    #par(family = 'sans')
    V(g)$size <- 25
    E(g)$width <- 2
    V(g)$label.font <- 2
    V(g)$label.cex <- 2
    V(g)$label.color <- 'black'
    #V(g)$loop.angle <- -pi

    if (type=="PNG")
    {
        CairoPNG(filename, bg='transparent')
        #png(filename, bg='transparent')
        plot(g)
        dev.off()
    } else
    if (type=="PS")
    {
        #postscript(filename, bg='transparent')
        CairoPS(filename, bg='transparent')
        plot(g, vertex.label.family="Helvetica")
        dev.off()
    } else
    {
        if (type=="PDF")
        {
            pdf(filename, bg='transparent')
            plot(g, vertex.label.family="Helvetica")
            dev.off()
        } else
            plot(g)
    }
}

write.decode <- function(screen, cell, hmm)
{
    T <- hmm$T
    K <- hmm$graph$K
    for (f in 1:dim(cell)[1])
    {
        #cat("Read file ", paste(screen$dir, cell$filename[f], sep="/"), "\n")
        t <- read.delim(paste(screen$dir, cell$filename[f], sep="/"), as.is=TRUE)
        if (!is.null(t$class__A__probability) && !is.null(t$class__B__probability))
        {
            nCells = 2
            colNames <- c("class__A__label", "class__B__label")
            v <- array(0, c(nCells, T))
            v[1,] <- t$class__A__probability
            v[2,] <- t$class__B__probability
        } else
        if (!is.null(t$class__A__probability))
        {
            nCells = 1
            colNames <- c("class__A__label")
            v <- array(0, c(nCells, T))
            v[1,] <- t$class__A__probability
        } else
        {
            nCells = 1
            colNames <- c("class__B__label")
            v <- array(0, c(nCells, T))
            v[1,] <- t$class__B__probability
        }

        fuseClasses <- screen$fuseClasses
        prob2 <- array(0,dim = c(nCells,T,K))
        n <- 0
        for (ic in 1:nCells)
        {

            for (j in 1:T)
            {
                Cstr <- v[ic,j]
                Cstr2 <- strsplit(Cstr,split=",")[[1]]
                C <- strsplit(Cstr2, split=":")
                Cs <- rep(0, K)
                for (n in 1:length(C))
                    Cs[as.numeric(C[[n]][1])] <- as.numeric(C[[n]][2])
                p = rep(0,K)
                #k <- length(C)
                #if (k != K) {
                #    cat("ERROR: The number of classes in file ", screen$cell$filename[i], " number of classes is ", k,". Expected number of classes is ",K,"\n")
                #    stop()
                #}
                for (k in 1:K)
                {
                    if (!is.null(fuseClasses) && k %in% fuseClasses[,2])
                        k2 = fuseClasses[which(fuseClasses[,2] == k), 2]
                    else
                        k2 = k
                    p[k2] <- p[k2] + Cs[k]
                }
                prob2[ic,j,] <- p
            }
        }
        Sequence2 <- hmm.decode(prob2, hmm)
        #print(Sequence2)
        dirHmm <- paste(screen$dir, cell$tracking[f], "_hmm", sep="/")
        if (!file.exists(dirHmm))
            dir.create(dirHmm)
        write.table(t(Sequence2), paste(dirHmm, cell$name[f], sep="/"), quote=FALSE, sep="\t",
                row.names=FALSE,
                col.names=colNames)
        #write.table(Sequence2, paste(dirHmm, cell$name[f], sep="/"), quote=FALSE, sep="\t")
    }

}

subsearch <- function(y, x)
{
  i <- which(apply(embed(y, length(x)), 1, identical, rev(x)))
  if (length(i) == 0)
    i <- NA
  return(i)
}

write.hmm.report <- function(screen, prob, outdir, graph, openHTML=TRUE,
                             sortClasses=NULL, filterClasses=NULL,
                             indices=NULL,
                             realign=NULL,
                             realign_onset=NULL,
                             realign_truncate=0,
                             realign_center=10,
                             features=NULL,
                             write_decode=TRUE,
                             write_decode2=TRUE,
                             groupByOligoId=FALSE,
                             groupByGene=FALSE,
                             visualizeDecode=FALSE,
                             timelapse=1.0,
                             max_time=120,
                             feature_range=c(0,1.2),
                             feature_filter_range=NULL,
                             hmm_em_steps=1,
                             hmm_initial_emission=NULL,
                             performDecode=TRUE,
                             truncate_from_front=NULL,
                             motif_sequence=NULL)
{
    if (!file.exists(outdir))
        dir.create(outdir)

    if (groupByOligoId)
        suffix = 'byoligo'
    else if (groupByGene)
        suffix = 'bysymbol'
    else
        suffix = 'bypos'

    outdir_region = paste(outdir, paste(screen$regionName, suffix, sep='_'), sep='/')
    if (!file.exists(outdir_region))
        dir.create(outdir_region)

    rel_sequences = '_sequences'
    outdir_sequences = paste(outdir_region, rel_sequences, sep='/')
    if (!file.exists(outdir_sequences))
        dir.create(outdir_sequences)

    N <- dim(prob)[1]
    T <- dim(prob)[2]
    C <- graph$C
    K <- graph$K
    T.old <- T

    counts.all <- list()
    names.all <- list()
    symbols.all <- list()

    overall_indices = NULL
    overall_realign = NULL

    # Learn HMM model for each condition

    hmm <- list()
    post <- array(0,dim=dim(prob))
    Sequence.Raw <- array(0, dim=c(N,T))
    Sequence <- array(0, dim=c(N,T))
    L <- levels(screen$cell$gene)
    Lpos <- levels(screen$cell$position)
    S <- length(L)
    Spos <- length(Lpos)


    if (groupByOligoId)
    {
        L <- levels(screen$cell$oligoid)
        S <- length(L)
        groups <- S
        #sortedIndex <- seq(1,S)
        sortedIndex <- sort(L, index.return=TRUE, method="shell")$ix
    } else
    if (groupByGene)
    {
        L <- levels(screen$cell$gene)
        S <- length(L)
        groups <- S
        #sortedIndex <- seq(1,S)
        sortedIndex <- sort(L, index.return=TRUE, method="shell")$ix
    } else
    {
        groups <- Spos
        pos.names <- vector(length=Spos)
        for (i in 1:Spos)
        {
            I <- screen$cell$position == Lpos[i]
            #print(screen$cell[I,]$gene[1])
            name = as.character(screen$cell[I,]$gene[1])
            if (is.na(name))
                name = Lpos[i]
            pos.names[i] = name
            #print(pos.names[i])
        }
        print(pos.names)
        sortedIndex <- sort(pos.names, index.return=TRUE, method="shell")$ix
        #print(sortedIndex)
        #break
    }

    T1 <- matrix("", nr=3, nc=groups)
  cat("groups=",groups,"\n")

    fn <- matrix("",nr=groups,nc=2)
    fn.raw <- matrix("",nr=groups,nc=2)
    fn.f <- matrix("",nr=groups,nc=2)
    fn.b <- matrix("",nr=groups,nc=2)


###MICHIO####
    countsAll.mean <- matrix(0,nr=groups,nc=K)
    countsAll.sd <- matrix(0,nr=groups,nc=K)
    countsAll.median <- matrix(0,nr=groups,nc=K)
    TrajectoryNumber <- matrix(0,nr=groups,nc=3)
    countsMotif <- matrix(0,nr=groups,nc=4)
###MICHIO####

    for (i in 1:groups)
    {
        if (groupByOligoId)
        {
            I <- screen$cell$oligoid == L[sortedIndex[i]]
                pos.name = L[sortedIndex[i]]
                gene.name = L[sortedIndex[i]]
                gene.symbol = screen$cell$gene[I][1]
                pos.list = levels(factor(screen$cell$position[I]))
                str.pos.list = paste(pos.list, collapse=',')
            #I <- (screen$cell$oligoid == L[sortedIndex[i]] && screen$cell$valid == TRUE)
        }
        else
        if (groupByGene)
        {
            I <- screen$cell$gene == L[sortedIndex[i]]
                pos.name = L[sortedIndex[i]]
                gene.name = L[sortedIndex[i]]
                gene.symbol = screen$cell$gene[I][1]
                pos.list = levels(factor(screen$cell$position[I]))
                str.pos.list = paste(pos.list, collapse=',')
                str.pos.filename = paste(pos.list, collapse='_')

            #I <- (screen$cell$gene == L[sortedIndex[i]] && screen$cell$valid == TRUE)
        }
        else
        {
            I <- screen$cell$position == Lpos[sortedIndex[i]]
                pos.name <- Lpos[sortedIndex[i]]
                gene.name <- pos.names[sortedIndex[i]]
                str.pos.list = pos.name
                str.pos.filename = str.pos.list
                gene.symbol = screen$cell$gene[I][1]
            #I <- (screen$cell$position == Lpos[sortedIndex[i]] && screen$cell$valid == TRUE)
        }
        N.gene <- sum(I)
        print(paste("Generate HMM:", pos.name, " Pos:", str.pos.list, " Group:", i, " Samples:", N.gene))


#    if (!is.null(features) & !is.null(feature_filter_range))
#   {
#      I2 <- seq(1,length(I))[I]
#      #print(I2)
#      feature.means <- apply(features[I,], 1, mean)
#      #print(feature.meaeans)
#      I[I2[feature.means < feature_filter_range[0] | feature.means > feature_filter_range[1]]] <- FALSE
#      #print(I)
#    }

    if (N.gene <= 1)
    {
        I[c(1,2)] = TRUE
        N.gene <- sum(I)
    }

  N.gene.old = N.gene
        {

            hmm[[i]] <- hmm.learn(prob[I,,], graph, steps=hmm_em_steps, initial_emission=hmm_initial_emission)

            Sequence.Raw[I,] <- apply(prob[I,,], c(1,2), which.max)
            if (visualizeDecode)
            {
                dirHmm <- paste(screen$dir, "..", "hmm", "_visualized", screen$regionName, sep="/")
                Sequence[I,] <- hmmDecode(prob[I,,], hmm[[i]],
                                          visualize=TRUE,
                                          cell=screen$cell[I,],
                                          dirHmm=dirHmm)
            } else
            {
                if (performDecode)
                    Sequence[I,] <- hmm.decode(prob[I,,], hmm[[i]])
                else
                    Sequence[I,] <- Sequence.Raw[I,]
            }

            # export hmm model
            dir_model <- paste(outdir_region, '_model', sep="/")
            if (!file.exists(dir_model))
                dir.create(dir_model, recursive=TRUE)
            hmm.export(hmm[[i]], paste(dir_model, '/', pos.name, '__pre.txt', sep=''))

            # build new model based on corrected input
            # generate prob vector for corrected sequences
            if (K == C) {
                prob2 = array(.0, dim=c(N.gene, T, K))
                for (k1 in 1:N.gene)
                    for (k2 in 1:T)
                        prob2[k1,k2,Sequence[I,][k1,k2]] = 1.
                hmm2 <- hmm.learn(prob2, graph, steps=1)
                hmm.export(hmm2, paste(dir_model, '/', pos.name, '__post.txt', sep=''))
            }

            if (write_decode)
            {
                write.decode(screen, screen$cell[I,], hmm[[i]])
            }
            if (write_decode2)
            {
                #print(Sequence2)
                mcell <- screen$cell[I,]
                for (f in 1:dim(mcell)[1])
                {
                    dirHmm2 <- paste(screen$dir, mcell$tracking[f], "_hmm2", sep="/")
                    if (!file.exists(dirHmm2))
                        dir.create(dirHmm2)
                    #print(dim(mcell))
                    #print(Sequence[I,][f,])
                    write.table(Sequence[I,][f,], paste(dirHmm2, mcell$name[f], sep="/"), quote=FALSE, sep="\t",
                        row.names=FALSE,
                        col.names=c("class__A__label"))
                }
            }

            fn[i,1] <- paste(rel_sequences,"/sequence__",pos.name,".png",sep="")
            fn[i,2] <- paste(rel_sequences,"/sequence__",pos.name,".ps",sep="")

            fn.raw[i,1] <- paste(rel_sequences,"/sequence_raw__",pos.name,".png",sep="")
            fn.raw[i,2] <- paste(rel_sequences,"/sequence_raw__",pos.name,".ps",sep="")

            fn.f[i,1] <- paste(rel_sequences,"/sequence_features__",pos.name,".png",sep="")
            fn.f[i,2] <- paste(rel_sequences,"/sequence_features_lines__",pos.name,".png",sep="")

            fn.b[i,1] <- paste(rel_sequences,"/sequence_boxplot__",pos.name,".png",sep="")
            fn.b[i,2] <- paste(rel_sequences,"/sequence_barplot__",pos.name,".png",sep="")



            #print(paste("Generate plots: ", L[i], N.gene))

            # Plot transition graphs

            # write PNG and PDF
            plot.transition.graph(hmm[[i]], type="PNG", filename=paste(outdir_sequences,"/graph_loop__",pos.name,".png",sep=""), loops=TRUE, weights=TRUE)
            #plotTransitionGraph(hmm[[i]], type="PDF", filename=paste(outdir_sequences,"/graph_loop__",pos.name,".pdf",sep=""), loops=TRUE, weights=TRUE)
            plot.transition.graph(hmm[[i]], type="PS",  filename=paste(outdir_sequences,"/graph_loop__",pos.name,".ps",sep=""), loops=TRUE, weights=TRUE)

            plot.transition.graph(hmm[[i]], type="PNG", filename=paste(outdir_sequences,"/graph__",pos.name,".png",sep=""), loops=FALSE, weights=TRUE)
            #plotTransitionGraph(hmm[[i]], type="PDF", filename=paste(outdir_sequences,"/graph__",pos.name,".pdf",sep=""), loops=FALSE, weights=TRUE)
            #plot.transition.graph(hmm[[i]], type="PS",  filename=paste(outdir_sequences,"/graph_",i,".ps",sep=""), loops=FALSE, weights=TRUE)


            # write HTML
            #T1[2,i] <- hwriteImage(paste("graph_loop_",i,".png",sep=""), link=paste("graph_loop_",i,".pdf",sep=""))
            T1[2,i] <- hwriteImage(paste(rel_sequences,"/graph__",pos.name,".png",sep=""), link=paste(rel_sequences,"/graph__",pos.name,".png",sep=""), width=400, height=400)
            T1[3,i] <- hwriteImage(paste(rel_sequences,"/graph__loop",pos.name,".png",sep=""), link=paste(rel_sequences,"/graph__loop",pos.name,".png",sep=""), width=400, height=400)
            #T1[2,i] <- hwriteImage(paste("graph_",i,".png",sep=""), link=paste("graph_",i,".pdf",sep=""))
            #T1[i,3] <- hwrite(hmm[[i]]$trans)


#            sq <- Sequence[I,seq(1,T)]
            sq <- Sequence[I,]
            sq.raw <- Sequence.Raw[I,]

          realign.starts.nofilter <- rep(0,0)
          if (!is.null(realign_onset) || !is.null(realign)) {
            #print(dim(sq))
            #print(T)
            #I3 <- rep(FALSE, sum(I))

              if (is.null(realign))
                  onsets <- apply(sq, 1, subsearch, realign_onset)
            else {
                  I.id = realign$id == i
                  #print(sum(I.id))
                    realign.i <- realign$ix[I.id]
        }

        T <- dim(sq)[2]
                I2 <- seq(1,length(I))[I]
                nsq <- matrix(0, nc=T, nr=0)
                nsq.raw <- matrix(0, nc=T, nr=0)
                realign.starts <- rep(0,0)
                center <- realign_center
                for (k in 1:length(I2)) {
                    if (is.null(realign))
                        s <- center - onsets[k][[1]][1]
                    else
                        s <- realign.i[k]
                    if (!is.na(s))
                    {
                        line <- rep(0,T)
                        line.raw <- rep(0,T)
                        if (s < 0) {
                          line[1:(T+s)] <- sq[k,(1-s):T]
                          line.raw[1:(T+s)] <- sq.raw[k,(1-s):T]
                        } else {
                          line[(s+1):T] <- sq[k,1:(T-s)]
                          line.raw[(s+1):T] <- sq.raw[k,1:(T-s)]
                        }
                        nsq <- rbind(nsq, line)
                        nsq.raw <- rbind(nsq.raw, line.raw)
                        realign.starts <- append(realign.starts, s)
                    } else
                        I[I2[k]] <- FALSE
                    realign.starts.nofilter <- append(realign.starts.nofilter, s)
                }

                if (is.null(overall_realign))
                {
                  overall_realign = list()
                  overall_realign$id = rep(i, length(realign.starts.nofilter))
                  overall_realign$ix = realign.starts.nofilter
                } else {
                  overall_realign$id = c(overall_realign$id, rep(i, length(realign.starts.nofilter)))
                  overall_realign$ix = c(overall_realign$ix, realign.starts.nofilter)
                 }
                #print(length(realign.starts.nofilter))

                T <- T - realign_truncate
    #            print(dim(nsq))
    #            print(T)
                I2 <- seq(1,length(I))[I]
                check <- rep(0,0)
                Kn <- dim(nsq)[1]
                #sq <- matrix(0, nc=T, nr=0)
                #sq.raw <- matrix(0, nc=T, nr=0)
                sq = nsq
                sq.raw = nsq.raw
                check = 1:Kn
                if (Kn > 0 && FALSE)
                for (k in 1:Kn) {
                    #print("moo1")
                    #print(dim(nsq))
                    #print(k)
                    #print(T)
                    if (nsq[k,T] != 0) {
                       #print("moo2")
                        sq <- rbind(sq, nsq[k,1:T])
                        sq.raw <- rbind(sq.raw, nsq.raw[k,1:T])
                        check <- append(check, k)
                    } else
                        I[I2[k]] <- FALSE
                }
                realign.starts <- realign.starts[check]
                N.gene <- dim(sq)[1]
            } else
                realign.starts <- rep(0, N.gene)

            if (is.null(indices))
                I.indices <- 1:N.gene
            else
            {
                I.id = indices$id == i
                #print(sum(I.id))
                I.indices <- indices$ix[I.id]
                #print(length(I.indices))
                sq <- sq[I.indices,]
                sq.raw  <- sq.raw[I.indices,]
                N.gene <- dim(sq)[1]

            }
            I.sort <- rep(TRUE, N.gene)

    #        sq.r <- Sequence.Raw[I,][I.indices,]
    #        idx <- apply(sq.r[,1:9], 1, max) <= 2
    #        #print(idx)
    #        #idx <- idx[80:160]
    #        #print(length(idx))
    #        I.indices <- I.indices[idx][81:160]
    #        print(I.indices)
    #        sq <- Sequence[I,][I.indices,]
    #        print(dim(sq))
    #        N.gene <- length(sq)

    #        if (!is.null(indices))
    #        {
    #            sq <- sq[indices,]
    #            N.gene <- length(sq)
    #        } else
    #        {
    #            N.gene <- length(sq)
    #            indices <- rep(TRUE, N.gene)
    #        }
    #        I.filter <- rep(TRUE, N.gene)
    #        if (!is.null(filterClasses))
    #        {
    #            I.filter <- as.logical(apply(apply(sq, 1, function (x) !x %in% filterClasses), 2, min))
    #            N.gene <- sum(I.filter)
    #            sq <- sq[I.filter,]
    #        }
            if (!is.null(sortClasses))
            {
                occurence <- sq
                occurence[] = FALSE
                for (s in sortClasses)
                    occurence <- occurence | (sq == s)
                I.sort <- rev(sort(apply(occurence, 1, sum), index.return=TRUE, method="shell")$ix)
                sq <- sq[I.sort,]
            }
        if (is.null(overall_indices))
        {
        overall_indices = list()
        overall_indices$id = rep(i, N.gene)
        overall_indices$ix = I.sort
      } else {
        overall_indices$id = c(overall_indices$id, rep(i, N.gene))
        overall_indices$ix = c(overall_indices$ix, I.sort)
      }

            #cell <- screen$cell[I,][I.indices,][I.sort,]
            export.data <- data.frame(name=screen$cell[I,][I.indices,][I.sort,]$name,
                          realign=realign.starts[I.indices][I.sort])
            #print(export.data)
            dirHmm <- paste(outdir_region, '_index', sep="/")
            if (!file.exists(dirHmm))
                dir.create(dirHmm, recursive=TRUE)
            write.table(export.data, paste(dirHmm, "/", pos.name, ".txt", sep=""), quote=FALSE, sep="\t",
                        row.names=FALSE, col.names=c("Trajectory", "Realign"))

            if (groupByOligoId | groupByGene)
                plot_title = paste(gene.name, " n=", N.gene,"/",N.gene.old, " (", str.pos.list, ")", sep="")
            else
                plot_title = paste(pos.name, " - ", gene.name, " n=", N.gene,"/",N.gene.old, sep="")
            print(plot_title)
            T1[1,i] <- plot_title


      if (!is.null(truncate_from_front))
      {
        print(T)
        if (T > truncate_from_front)
          T.trunc = truncate_from_front
        else
          T.trunc = T
        print(T.trunc)
        print(dim(sq))
        print(N.gene)
        if (!is.null(dim(sq)))
          sq <- sq[,1:T.trunc]
        print(dim(sq))
      } else
        T.trunc = T

            CairoPNG(paste(outdir_region,"/",fn[i,1],sep=""), width=1000, height=1000, bg='transparent')
            #CairoPS(paste(outdir,"/",fn[i,2],sep=""), width=15, height=15, bg='transparent')
            #layout(matrix(c(1,2), 2, 1), heights=c(10,10))
            #par(mar=c(1,1,0,0))
            par(mar=c(0,0,0,0))

            if (N.gene > 1)
      {
            image(t(sq), col=class.colors.hmm,
                  #xlab=paste("cells", " (", N.gene, ")", sep=""),
                  #ylab="time",
                  zlim=c(1,K), xaxt="n", yaxt="n")
            box()
            #axis(1, seq(T))
            }
            dev.off()

            counts <- matrix(0,nr=K,nc=N.gene)
            for (k in 1:K)
            {
                s <- sq == k
                #print(sq)
                #print(dim(s))
                if (is.null(dim(s)))
                    counts[k,] <- NA
                else
                    counts[k,] <- apply(s, 1, sum)
                #print(apply(sq == k, 1, sum))
            }

            counts.time <- counts * timelapse
            #counts.time[counts.time == 0] = NA
            # export class counts per position/condition
            dirCounts <- paste(outdir_region, "_counts", sep="/")
            if (!file.exists(dirCounts))
                dir.create(dirCounts, recursive=TRUE)
            write.table(t(counts.time), paste(dirCounts, "/", pos.name, ".txt", sep=""), quote=FALSE, sep="\t",
                row.names=FALSE, col.names=1:k)

            counts.all[[i]] = counts.time
            names.all[[i]] = gene.name
            symbols.all[[i]] = gene.symbol

###MICHIO####
     countsAll.mean[i,] <- apply(counts.time, 1, mean, na.rm=TRUE)
     countsAll.sd[i,] <- apply(counts.time, 1, sd, na.rm=TRUE)
     countsAll.median[i,] <- apply(counts.time, 1, median, na.rm=TRUE)
            TrajectoryNumber[i,1] <- pos.name
            TrajectoryNumber[i,2] <- N.gene.old
            TrajectoryNumber[i,3] <- N.gene
###MICHIO####

      # compute the time between two motifs (or the trajectory length if the
      # motif can not be found)
      if (!is.null(motif_sequence) && N.gene > 1)
      {
        #print(sq)
        #print(motif_sequence$start)
        start = apply(sq, 1, subsearch, motif_sequence$start)
        end = apply(sq, 1, subsearch, motif_sequence$end)
        T.sq = dim(sq)[2]
        empty = apply(sq[,(realign_center:T.sq)], 1, subsearch, c(0))

        start2 = rep(0, N.gene)
        end2 = rep(0, N.gene)
        empty2 = rep(0, N.gene)
        # transform "strange list" constructo to simple vector
        for (k in 1:N.gene)
        {
          start2[k] = start[k][[1]][1]
          end2[k] = end[k][[1]][1]
          empty2[k] = empty[k][[1]][1]
        }
        #print(empty2)
        # replace all NAs (motif not found) by the 0-onset (trajectory end)
        nas = is.na(end2)
        end2[nas] <- empty2[nas]
        # replace all NAs (neither motif nor 0-onset) by the maximum trajectory length
        nas = is.na(end2)
        end2[nas] <- T.sq

        #print(start)
        #print(end)
        counts = (end2 - start2 + 1) * timelapse
        #print(counts)
        #print(paste(T.old, T, T.trunc, dim(sq)))
        counts[counts < 0] <- NA
        countsMotif[i,1] = sum(!is.na(counts))
        countsMotif[i,2] = mean(counts, na.rm=TRUE)
        countsMotif[i,3] = sd(counts, na.rm=TRUE)
        countsMotif[i,4] = median(counts, na.rm=TRUE)
        #print(counts)
      }

            #apply(counts, 1, mean)

            #print('class 4')
            #timelapse =
            #v <- counts.time[4,]
            #print(v)
            #v <- v * timelapse
            #print(paste('mean:',mean(v, na.rm=TRUE)))
            #print(paste('  sd:',sd(v, na.rm=TRUE)))
            #print(paste('size:',length(v)))

            #print('class 3+4')
            #v <- (counts.time[3,] + counts.time[4,])
            #print(v)
            #v <- v[-c(seq(1,14),17,18,19,22,23,24,25,63,84)]
            #print(v)
            #v <- v * timelapse
            #print(paste('mean:',mean(v, na.rm=TRUE)))
            #print(paste('  sd:',sd(v, na.rm=TRUE)))
            #print(paste('size:',length(v)))

            CairoPNG(paste(outdir_region,"/",fn.b[i,1],sep=""), width=400, height=400)
            boxplot(as.data.frame(t(counts.time), optional=TRUE), col=class.colors.hmm, ylim=c(0,max_time),
                    xlab="class", ylab="time [min]")
            title(plot_title)
            dev.off()

            CairoPNG(paste(outdir_region,"/",fn.b[i,2],sep=""), width=400, height=400)
            barplot(apply(counts.time, 1, mean, na.rm=TRUE), col=class.colors.hmm, ylim=c(0,max_time),
                    xlab="class", ylab="time [min]")
            title(plot_title)
            dev.off()

    #        counts <- matrix(0,nr=K,nc=T)
    #        for (k in 1:K)
    #            counts[k,] <- apply(Sequence.Raw[I,] == k, 2, sum)
    #        Single.Sequence <- matrix(0, nr=1, nc=T)
    #        Single.Sequence[1,] <- apply(counts, 2, which.max)

            CairoPNG(paste(outdir_region,"/",fn.raw[i,1],sep=""), width=1000, height=1000, bg='transparent')
            #CairoPS(paste(outdir,"/",fn.raw[i,2],sep=""), width=15, height=15, bg='transparent')
            par(mar=c(0,0,0,0))
            if (N.gene > 1)
      {
            sq.raw <- sq.raw[I.sort,1:T.trunc]
            image(t(sq.raw), col=class.colors, zlim=c(1,C), xaxt="n", yaxt="n")
            box()
            #axis(1, seq(T))
      }
            dev.off()

            if (!is.null(features))
            {
                CairoPNG(paste(outdir_region,"/",fn.f[i,1],sep=""), width=1000, height=1000, bg='transparent')
                par(mar=c(0,0,0,0))
                #limit = 1.2
                #limit = 255
                features2 <- features
                features2[features2 > feature_range[2]] <- feature_range[2]
                features2[features2 < feature_range[1]] <- feature_range[1]
                sq.f <- features2[I,][I.indices,][I.sort,]
                image(t(sq.f), xaxt="n", yaxt="n", col=bwcol_features, zlim=feature_range)
                box()
                #axis(1, seq(T))
                dev.off()

                CairoPNG(paste(outdir_region,"/",fn.f[i,2],sep=""), width=1000, height=1000)
                par(mar=c(5,4,1,1), cex=2)
                sq.f <- sq[,20:60]
                T <- dim(sq.f)[2]
                xv <- seq(1,T)
                xlim <- c(1,T)
                ylim <- feature_range
                col = '#00000099'
                isPlot = FALSE
                for (i in 1:dim(sq)[1])
                {
                    if (!isPlot)
                    {
                        plot(sq.f[i,], xlim=xlim, ylim=ylim, type='l',
                                xaxt='n',
                                xlab='time (min)',
                                ylab='intensity', col=col,
                                xaxs='i', yaxs='i',las=1)
                        xv2 <- xv[seq(1,length(xv), 10)]
                        #axis(1, xv2, labels=format((xv2-1)*2.7, nsmall=0))
                        isPlot = TRUE
                    } else
                        lines(sq.f[i,], type='l', col=col)
                }
                dev.off()
            }
        }
    }
    T3 <- hwriteImage(fn[,1], width=400, height=400, link=fn[,1])
    T4 <- hwriteImage(fn.raw[,1], width=400, height=400, link=fn.raw[,1])
    T5 <- hwriteImage(fn.f[,1], width=400, height=400, link=fn.f[,1])
    T6 <- hwriteImage(fn.f[,2], width=400, height=400, link=fn.f[,2])
    T7 <- hwriteImage(fn.b[,1], width=400, height=400, link=fn.b[,1])
    T8 <- hwriteImage(fn.b[,2], width=400, height=400, link=fn.b[,2])

# html-page

    p <- openPage(paste(outdir_region,"/index.html",sep=""))

#        plotTransitionGraph(graph, type="PS", filename=paste(outdir,"/graph_prior.ps",sep=""),loops=FALSE,weights=FALSE)
    plot.transition.graph(graph, type="PNG", filename=paste(outdir_sequences,"/graph_prior.png",sep=""),loops=FALSE,weights=FALSE)
#    plotTransitionGraph(graph, type="PS", filename=paste(outdir,"/graph_prior_loop.ps",sep=""),loops=TRUE,weights=FALSE)
    plot.transition.graph(graph, type="PNG", filename=paste(outdir_sequences,"/graph_prior_loop.png",sep=""),loops=TRUE,weights=FALSE)
#        #plotTransitionGraph(graph, type="PDF", filename=paste(outdir,"/graph_prior.pdf",sep=""),loops=FALSE,weights=FALSE)
    hwrite("Prior Selected Graph Structure",p,heading=3)
    hwriteImage(paste(outdir_sequences, "/graph_prior.png",sep=""),p,link=paste(outdir_sequences,"/graph_prior.png",sep=""))

    hwrite("Transition probabilities",p,heading=3)
    hwrite(T1,p)

    #hwrite("Class Frequency",p,heading=3)
    #hwrite(T2,p)

    hwrite("Single cell annotation (HMM)",p,heading=3)
    hwrite(T3,p)

    if (!is.null(features))
    {
        hwrite("Features",p,heading=3)
        hwrite(T5,p)
        hwrite(T6,p)
    }

    hwrite("Box plots (HMM)",p,heading=3)
    hwrite(T7,p)

    hwrite("Bar plots (HMM)",p,heading=3)
    hwrite(T8,p)

    hwrite("Single cell annotation (raw)",p,heading=3)
    hwrite(T4,p)

    closePage(p)
    if (openHTML) {
        browseURL(paste(outdir_region,"/index.html",sep=""))
    }

###MICHIO####
  dir_summary <- paste(outdir_region, "_summary", sep="/")
    if (!file.exists(dir_summary))
      dir.create(dir_summary, recursive=TRUE)

    write.table(countsAll.mean, paste(dir_summary, "/all_mean.txt", sep=""), quote=FALSE, sep="\t",
                row.names=FALSE, col.names=FALSE)
    write.table(countsAll.sd, paste(dir_summary, "/all_sd.txt", sep=""), quote=FALSE, sep="\t",
                row.names=FALSE, col.names=FALSE)
    write.table(countsAll.median, paste(dir_summary, "/all_median.txt", sep=""), quote=FALSE, sep="\t",
                row.names=FALSE, col.names=FALSE)
    write.table(TrajectoryNumber, paste(dir_summary, "/all_TrajectoryNumbers.txt", sep=""), quote=FALSE, sep="\t",
                row.names=FALSE, col.names=FALSE)

  together = cbind(TrajectoryNumber, countsAll.mean, countsAll.sd, countsAll.median)
  cnames = c('Pos', 'Pre', 'Post',
             paste('Mean__', 1:K, sep=''),
             paste('Sd__', 1:K, sep=''),
             paste('Median__', 1:K, sep=''))
  if (!is.null(motif_sequence))
  {
      cnames = c(cnames, 'Post__motif', 'Mean__motif', 'Sd__motif', 'Median__motif')
    together = cbind(together, countsMotif)
  }
  print(cnames)
  print(dim(together))
    write.table(together, paste(dir_summary, "/all_together.txt", sep=""), quote=FALSE, sep="\t",
                row.names=FALSE, col.names=cnames)


###MICHIO####


    list(overall_indices=overall_indices,
         overall_realign=overall_realign,
         counts.all = counts.all,
         names.all = names.all,
         symbols.all = symbols.all,
         out.dir=outdir_region)
}

bwcol  <- colorRampPalette(c("#FFFFFF","#000000"), space="rgb")(256)
bwcol_features  <- colorRampPalette(c("#000000","#FFFFFF"), space="rgb")(256)
redcol <- colorRampPalette(c("#FFFFFF","#FF0000"), space="rgb")(256)

