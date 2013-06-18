#                          The CellCognition Project
#                    Copyright (c) 2006 - 2010 Michael Held
#                     Gerlich Lab, ETH Zurich, Switzerland
#                             www.cellcognition.org
#
#             CellCognition is distributed under the LGPL License.
#                       See trunk/LICENSE.txt for details.
#                See trunk/AUTHORS.txt for author contributions.
#
# Author(s): Bernd Fischer
# Date: $Date:$
# Revision: $Rev:$'
# Source: $URL:$'

hmm.export <- function(hmm, filename) {
  write.table(hmm$trans, filename, quote=FALSE, sep="\t",  row.names=FALSE)
}

hmm.summarize <- function(post, ntracks, nframes, nclasses, nsymbols, emission) {
  hmm <- list()
  hmm$T <- nframes
  hmm$start <- rep(0, nclasses)
  hmm$trans <- matrix(0, nr=nclasses, nc=nclasses)
  
  for (i in 1:ntracks) {
    for (j in 2:nframes) {
      # conditional prediction probabilities averaged over all transitions
      # sum( P(t_j=t|t_j=t+1) )
      P <- matrix(post[i,j-1,], nr=nclasses, nc=1) %*% matrix(post[i,j,], nr=1, nc=nclasses)
      hmm$trans <- hmm$trans + P
    }
    # sum over all prediction probabilities of the first frame of each track
    hmm$start <- hmm$start + post[i, 1, ]
  }
  # use a simple diagonal matrix as emmistion matrix if no custom emission matrix is given
  if (is.null(emission)) {
    emission = matrix(0, nr=nclasses, nc=nsymbols)
    diag(emission) = 1  
  }
  hmm$e = emission  

  return(hmm)
}

hmm.add <- function(hmm1,hmm2) {
  hmm1$start = hmm1$start + hmm2$start
  hmm1$trans = hmm1$trans + hmm2$trans
  hmm1$e = hmm1$e + hmm2$e
  return(hmm1)
}

# acctually normalize and apply constraints!
hmm.normalize <- function(hmm, graph) {

  # normalize transition probabilities
  for (i in 1:graph$K) {
    I <- graph$trans[i,] > 0
    
    # if no transitions are defined at all
    # stop with error message would be better!
    if (sum(I) == 0) {
      graph$trans[i,] = 0
      graph$trans[i,i] = 1
    }
    
    s <- sum(hmm$trans[i, I])
    if (s > 0) {
      hmm$trans[i,I] = hmm$trans[i,I] / s
    } else {
      # if no allowed transitions are defined, the model defaults to 
      # equal probabilities
      # is it ok this way, it would mix up different constr
      hmm$trans[i,I] = 1 / graph$K
    }
    
    # why not a matrix multiplication?
    if (sum(I) < graph$K) {
      hmm$trans[i,!I] = 0
    }
  }

  ## normalize start probabilities
  I <- graph$start > 0
  if (sum(I) ==0) {
    cat("ERROR: There has to be at least one start node.")
    stop()
  }
  s <- sum(hmm$start[I])
  if (s > 0) {
    hmm$start[I] = hmm$start[I] / s
  } else {
    hmm$start[I] = 1 / graph$K
  }
  if (sum(I) < graph$K) {
    hmm$start[!I] = 0
  }

  # normalize emission probabilities
  for (i in 1:graph$K) {
    s <- sum(hmm$e[i,])
    if (s > 0) {
      hmm$e[i,] = hmm$e[i,] / s
    } else {
      hmm$e[i,] = 1/graph$C
    }
  }
  hmm$graph <- graph
  return(hmm)
}

hmm.posterior <- function(prob, hmm) {
  N <- dim(prob)[1]
  T <- dim(prob)[2]
  C <- dim(prob)[3]
  K <- hmm$graph$K
  P <- array(0,dim=c(N,T,K))
  fw <- matrix(0,nr=T,nc=K)
  bw <- matrix(0,nr=T,nc=K)
  E <- matrix(0,nr=T,nc=K)
  for (i in 1:N) {
    E[] <- 0.0
    for (k in 1:C) {
      E <- E + matrix(rep(hmm$e[,k],each=T),nr=T,nc=K) *
               matrix(rep(prob[i,,k],times=K),nr=T,nc=K)
    }
    fw[1,] <- E[1,] * hmm$start
    for (t in 2:T) {
      fw[t,] <- E[t,] * (matrix(fw[t-1,],nr=1,nc=K) %*% hmm$trans)
    }
    bw[T,] <- rep(1,K)
    for (t in (T-1):1) {
      bw[t,] <- hmm$trans %*% matrix(bw[t+1,] * E[t+1,], nr=K, nc=1)
    }
    P[i,,] <- fw * bw
    for (t in 1:T) {
      s <- sum(P[i,t,])
      if (s > 0) {
        P[i,t,] <- P[i,t,] / s
      } else {
        P[i,t,] <- 1 / K
      }
    }
  }
  return(P)
}

hmm.decode <- function(prob,hmm) {
  N <- dim(prob)[1]
  T <- dim(prob)[2]
  C <- dim(prob)[3]
  K <- hmm$graph$K
  Sequence <- array(0,dim=c(N,T))
  E <- matrix(0,nr=T,nc=K)
  for (i in 1:N) {
    E[] <- 0.0
    for (k in 1:C) {
       E <- E + matrix(rep(hmm$e[,k],each=T),nr=T,nc=K) *
                matrix(rep(prob[i,,k],times=K),nr=T,nc=K)
    }
    P <- matrix(0,nr=T,nc=K)
    bp <- matrix(0,nr=T,nc=K)
    P2 <- matrix(0,nr=K,nc=K)

    # new
    P[1,] <- hmm$start * E[1,]
    # old
    #P[1,] <- hmm$start * prob[i,1,]
    for (t in 2:T) {
      for (p in 1:K) {
        # new implementation: emission prob. learned by EM
        P2[p,] <- P[t-1,p] * hmm$trans[p,] * E[t,]

        # old implementation: equal-distributed emission prob.
        #P2[p,] <- P[t-1,p] * hmm$trans[p,] * prob[i,t,]
    }
      for (q in 1:K) {
        P[t,q] <- max(P2[,q])
        bp[t,q] <- which.max(P2[,q])
      }
    }
    Sequence[i,T] <- which.max(P[T,])
    for (t in (T-1):1) {
      Sequence[i,t] <- bp[t+1,Sequence[i,t+1]]
    }
  }
  return(Sequence)
}

hmm.post.init <- function(prob, graph) {
  # number of tracks
  N <- dim(prob)[1]  
  # number of frames
  T <- dim(prob)[2]  
  # number of classes
  K <- graph$K
  
  # if the association between hidden states and emisstions is 1 to 1
  # i.e. a hidden state corresponds to one destinct emission
  # post equals prob, otherwise only columns are exchanged.
  post <- array(0.0, dim=c(N,T,K))
  for (i in 1:K) {
    post[,,i] = prob[,,graph$h2o[i]]
  }
  return(post)
}

hmm.learn <- function(prob, graph, steps = 1, initial_emission=NULL) {

  # in case no emission matrix is given take unit-matrix with small error rates
  # outside the main diagonal. values are normalized in hmm.normalize.
  if (is.null(initial_emission)) {
      C <- dim(prob)[3]
      K <- graph$K
      initial_emission = matrix(0, nr=K, nc=C)
    diag(initial_emission) = 1
    initial_emission = initial_emission + 0.001
  }

  for (i in 1:steps) {
    if (i == 1) {
           post <- hmm.post.init(prob, graph)
    }
    else {
        post <- hmm.posterior(prob, hmm)
    }
        
    hmm <- hmm.summarize(post, dim(prob)[1], dim(prob)[2], dim(prob)[3], dim(prob)[3], initial_emission)
    hmm <- hmm.normalize(hmm, graph)
  }
  return(hmm)
}

