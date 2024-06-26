"""
Module: libfmp.c7.c7s3_version_id
Author: Meinard Mueller, Tim Zunner, Frank Zalkow
License: The MIT license, https://opensource.org/licenses/MIT

This file is part of the FMP Notebooks (https://www.audiolabs-erlangen.de/FMP)
"""
import numpy as np
from numba import jit

import librosa
import libfmp.c4
import libfmp.c7


@jit(nopython=True)
def compute_accumulated_score_matrix_common_subsequence(S):
    """Given the score matrix, compute the accumulated score matrix
       for common subsequence matching with step sizes {(1, 0), (0, 1), (1, 1)}

    Notebook: C7/C7S3_CommonSubsequence.ipynb

    Args:
        S: Score matrix

    Returns:
        D: Accumulated score matrix
    """
    N, M = S.shape
    D = np.zeros((N, M))

    D[0, 0] = max(0, S[0, 0])

    for n in range(1, N):
        D[n, 0] = max(0, D[n-1, 0] + S[n, 0])

    for m in range(1, M):
        D[0, m] = max(0, D[0, m-1] + S[0, m])

    for n in range(1, N):
        for m in range(1, M):
            D[n, m] = max(0, D[n-1, m-1] + S[n, m], D[n-1, m] + S[n, m], D[n, m-1] + S[n, m])

    return D


@jit(nopython=True)
def compute_optimal_path_common_subsequence(D, cellmax=True, n=0, m=0):
    """Given an accumulated score matrix, compute the score-maximizing path
       for common subsequence matching with step sizes {(1, 0), (0, 1), (1, 1)}

    Notebook: C7/C7S3_CommonSubsequence.ipynb

    Args:
        D: Accumulated score matrix
        cellmax: If "True", score-maximizing cell will be computed
        n, m: Indices of cell for backtracking start; only used when cellmax=False

    Returns
        P: Score-maximizing path (list of index pairs)
    """
    if cellmax:
        # n, m = np.unravel_index(np.argmax(D), D.shape)  # doesn't work with jit
        n, m = divmod(np.argmax(D), D.shape[1])
    P = [(n, m)]

    while ((n, m) != (0, 0) and (D[n, m] != 0)):
        if n == 0:
            cell = (0, m-1)
        elif m == 0:
            cell = (n-1, 0)
        else:
            val = max(D[n-1, m-1], D[n-1, m], D[n, m-1])
            if val == D[n-1, m-1]:
                cell = (n-1, m-1)
            elif val == D[n-1, m]:
                cell = (n-1, m)
            else:
                cell = (n, m-1)
        P.append(cell)
        n, m = cell
    if (D[n, m] == 0):
        del P[-1]
    P.reverse()
    P = np.array(P)
    return P


@jit(nopython=True)
def get_induced_segments(P):
    """Given a path, compute the induces segments

    Notebook: C7/C7S3_CommonSubsequence.ipynb

    Args:
        P: Path (list of index pairs)

    Returns
        seg_X: Induced segment of first sequence
        seg_Y: Induced segment of second sequence
    """
    seg_X = np.arange(P[0, 0], P[-1, 0] + 1)
    seg_Y = np.arange(P[0, 1], P[-1, 1] + 1)
    return seg_X, seg_Y


@jit(nopython=True)
def compute_partial_matching(S):
    """Given the score matrix, compute the accumulated score matrix
       for partial matching

    Notebook: C7/C7S3_CommonSubsequence.ipynb

    Args:
        S: Score matrix

    Returns:
        D: Accumulated score matrix
    """
    N, M = S.shape
    D = np.zeros((N+1, M+1))
    for n in range(1, N+1):
        for m in range(1, M+1):
            D[n, m] = max(D[n, m-1], D[n-1, m], D[n-1, m-1] + S[n-1, m-1])

    P = []
    n = N
    m = M
    while (n > 0) and (m > 0):
        if D[n, m] == D[n, m-1]:
            m = m - 1
        elif D[n, m] == D[n-1, m]:
            n = n - 1
        else:
            P.append((n-1, m-1))
            n = n - 1
            m = m - 1
    P.reverse()
    P = np.array(P)
    return D, P


def compute_sm_from_wav(x1, x2, Fs, N=4410, H=2205, ell=21, d=5, L_smooth=12,
                        tempo_rel_set=np.array([0.66, 0.81, 1, 1.22, 1.5]),
                        shift_set=np.array([0]), strategy='relative', scale=1,
                        thresh=0.15, penalty=-2, binarize=0):
    """Compute a similarity matrix (SM)

    Notebook: C7S3_VersionIdentification.ipynb

    Args:
        x1, x2: WAV files
        Fs: Sampling rate of WAV files
        N, H: Parameters for computing STFT-based chroma features
        ell, d: Parameters for computing CENS features
        L_smooth, tempo_rel_set, shift_set: Parameters for enhancing SM
        strategy, scale, thresh, penalty, binarize: Parameters used for thresholding SM

    Returns:
        X, Y: CENS feature sequence
        Fs_feature: Feature rate
        S_thresh, I: Similarity matrix and index matrix
    """
    # Computation of CENS features
    C1 = librosa.feature.chroma_stft(y=x1, sr=Fs, tuning=0, norm=1, hop_length=H, n_fft=N)
    C2 = librosa.feature.chroma_stft(y=x2, sr=Fs, tuning=0, norm=1, hop_length=H, n_fft=N)
    Fs_C = Fs / H
    X, Fs_feature = libfmp.c7.compute_cens_from_chromagram(C1, Fs_C, ell=ell, d=d)
    Y, Fs_feature = libfmp.c7.compute_cens_from_chromagram(C2, Fs_C, ell=ell, d=d)

    # Compute enhanced SM
    S, I = libfmp.c4.compute_sm_ti(X, Y, L=L_smooth,  tempo_rel_set=tempo_rel_set,
                                   shift_set=shift_set, direction=2)
    S_thresh = libfmp.c4.threshold_matrix(S, thresh=thresh, strategy=strategy,
                                          scale=scale, penalty=penalty, binarize=binarize)
    return X, Y, Fs_feature, S_thresh, I


def compute_prf_metrics(I, score, I_Q):
    """Compute precision, recall, F-measures and other
    evaluation metrics for document-level retrieval

    Notebook: C7/C7S3_Evaluation.ipynb

    Args:
        I: Array of items
        score: Array containig the score values of the times
        I_Q: Array of relevant (positive) items

    Returns:
        P_Q, R_Q, F_Q: Precision, recall, and F-measures sorted by rank
        BEP: Break-even point
        F_max: Maximal F-measure
        P_average: Mean average
        X_Q: Relevance function
        rank: Array of rank values
        I_sorted: Array of items sorted by rank
        rank_sorted: Array of rank values sorted by rank
    """
    # Compute rank and sort documents according to rank
    K = len(I)
    index_sorted = np.flip(np.argsort(score))
    I_sorted = I[index_sorted]
    rank = np.argsort(index_sorted) + 1
    rank_sorted = np.arange(1, K+1)

    # Compute relevance function X_Q (indexing starts with zero)
    # X_Q = np.zeros(K, dtype=bool)
    # for i in range(K):
    #     if I_sorted[i] in I_Q:
    #         X_Q[i] = True
    X_Q = np.isin(I_sorted, I_Q)
    # P_Q = np.cumsum(X_Q) / np.arange(1, K+1)

    # Compute precision and recall values (indexing starts with zero)
    M = len(I_Q)
    # P_Q = np.zeros(K)
    # R_Q = np.zeros(K)
    # for i in range(K):
    #     r = rank_sorted[i]
    #     P_Q[i] = np.sum(X_Q[:r]) / r
    #     R_Q[i] = np.sum(X_Q[:r]) / M
    P_Q = np.cumsum(X_Q) / np.arange(1, K+1)
    R_Q = np.cumsum(X_Q) / M

    # Break-even point
    BEP = P_Q[M-1]
    # Maximal F-measure
    sum_PR = P_Q + R_Q
    sum_PR[sum_PR == 0] = 1  # Avoid division by zero
    F_Q = 2 * (P_Q * R_Q) / sum_PR
    F_max = F_Q.max()
    # Average precision
    P_average = np.sum(P_Q * X_Q) / len(I_Q)

    return P_Q, R_Q, F_Q, BEP, F_max, P_average, X_Q, rank, I_sorted, rank_sorted
