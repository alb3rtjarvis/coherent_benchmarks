#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

# Root mean squared error
def RMSE(truth, est, edge=True):
    """
    Compute root mean squared error

    Parameters
    ----------
    truth : np.ndarray
        truth values.
    est : np.ndarray
        estimated values.
    edge : bool
        boolean that decides if edge values are considered.

    Returns
    -------
    float
        root mean squared error.

    """
    assert truth.shape == est.shape
    if edge:
        n = truth.size
    else:
        truth = np.squeeze(truth)
        est = np.squeeze(est)
        slices = tuple(slice(1, -1) for _ in range(truth.ndim))
        truth = truth[slices]
        est = est[slices]
        n = truth.size
        
    return np.sqrt(np.sum((truth - est)**2)/n)

# Mean absolute error
def MAE(truth, est, edge=True):
    """
    Compute mean absolute error.

    Parameters
    ----------
    truth : np.ndarray
        truth values.
    est : np.ndarray
        estimated values.
    edge : bool
        boolean that decides if edge values are considered.       

    Returns
    -------
    float
        mean absolute error.

    """
    assert truth.shape == est.shape
    if edge:
        n = truth.size
    else:
        truth = np.squeeze(truth)
        est = np.squeeze(est)
        slices = tuple(slice(1, -1) for _ in range(truth.ndim))
        truth = truth[slices]
        est = est[slices]
        n = truth.size
        
    return np.sum(np.abs(truth - est))/n

# Symmetric mean absolute percentage error
def sMAPE(truth, est, edge=True):
    """
    Compute symmetric mean absolute percentage error. In this form,
    truth and est are assumed to be strictly positive.

    Parameters
    ----------
    truth : np.ndarray
        truth values.
    est : np.ndarray
        estimated values.
    edge : bool
        boolean that decides if edge values are considered.            

    Returns
    -------
    float
        symmetric mean absolute percentage error.

    """
    assert truth.shape == est.shape
    if edge:
        n = truth.size
    else:
        truth = np.squeeze(truth)
        est = np.squeeze(est)
        slices = tuple(slice(1, -1) for _ in range(truth.ndim))
        truth = truth[slices]
        est = est[slices]
        n = truth.size
        
    return np.sum(np.divide(abs(truth - est), truth + est))*(200/n)
