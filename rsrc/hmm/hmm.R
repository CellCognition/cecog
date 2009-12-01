#                          The CellCognition Project
#                    Copyright (c) 2006 - 2009 Michael Held
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


hmm.summarize <- function(prob, post) {
  hmm <- list()
  N <- dim(prob)[1]
  T <- dim(prob)[2]
  C <- dim(prob)[3]
  K <- dim(post)[3]
  hmm$T <- T
  hmm$start <- rep(0,K)
  hmm$trans <- matrix(0,nr=K,nc=K)
  for (i in 1:N) {
    for (j in 2:T) {
      P <- matrix(post[i,j-1,],nr=K,nc=1) %*% matrix(post[i,j,],nr=1,nc=K)
      hmm$trans <- hmm$trans + P
    }
    hmm$start <- hmm$start + post[i,1,]
  }
  hmm$e <- matrix(0,nr=K,nc=C)
  for (i in 1:N) {
    for (j in 1:T) {
      P <- matrix(post[i,j,],nr=K,nc=1) %*% matrix(prob[i,j,],nr=1,nc=C)
      hmm$e <- hmm$e + P
    }
  }
  return(hmm)
}

hmm.add <- function(hmm1,hmm2) {
  hmm1$start = hmm1$start + hmm2$start
  hmm1$trans = hmm1$trans + hmm2$trans
  hmm1$e = hmm1$e + hmm2$e
  return(hmm1)
}

hmm.normalize <- function(hmm, graph) {

  ## normalize transition probabilities
  for (i in 1:graph$K) {
    I <- graph$trans[i,] > 0
    if (sum(I) ==0) {
      graph$trans[i,] = 0
      graph$trans[i,i] = 1
 #     cat("ERROR: Each node has to have one outgoing edge.")
#      stop()
    }
    s <- sum(hmm$trans[i,I])
    if (s > 0) {
      hmm$trans[i,I] = hmm$trans[i,I] / s
    } else {
      hmm$trans[i,I] = 1 / graph$K
    }
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

hmm.posterior <- function(prob,hmm) {
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
    P[1,] <- hmm$start * E[1,]
    for (t in 2:T) {
      for (p in 1:K) {
        P2[p,] <- P[t-1,p] * hmm$trans[p,] * E[t,]
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

hmm.post.init <- function(prob,graph) {
  N <- dim(prob)[1]
  T <- dim(prob)[2]
  K <- dim(prob)[3]
  post <- array(0.0,dim=c(N,T,graph$K))
  for (i in 1:graph$K) {
    post[,,i] = prob[,,graph$h2o[i]]
  }
  return(post)
}

hmm.learn <- function(prob, graph, steps = 5) {
  post <- hmm.post.init(prob,graph)
  for (i in 1:steps) {
    hmm <- hmm.summarize(prob,post)
    hmm <- hmm.normalize(hmm,graph)
    post <- hmm.posterior(prob,hmm)
  }
  return(hmm)
}

