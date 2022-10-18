# -*- coding: utf-8 -*-
from typing import Union, Optional, Dict, List, Tuple, Callable
from numpy import ndarray

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import scipy.stats as st

def close_fig(fig):
    """
    Close figure
    """
    plt.close(fig)

def _plot_hist(ax, 
                X : ndarray,
                bins: Optional[int] = None,
                range: Optional[tuple] = None,
                density: bool = True,
                color: Optional[Union[str,list,tuple]] = None,
                label: Optional[Union[str,list]] = None,
                alpha: float = 1,):
    X_shape = X.shape
    if len(X_shape)>1:
        X = np.reshape(X, np.prod(X.shape))
    if bins is None:
        bins = 'auto'
    if range is None:
        range = (X.min(), X.max())
    if color is None:
        color = 'blue'

    vals, bins, patches = ax.hist(X, bins = bins, range = range, density = density, 
                                    color = color, alpha = alpha, label = label)
    return vals, bins, patches

def _plot_fit_norm_line(ax, 
                        X : ndarray,
                        vals : ndarray,
                        range: Optional[tuple] = None,
                        line_points : int = 1000,
                        color: Optional[Union[str,list,tuple]] = None):
    X_shape = X.shape
    if len(X_shape)>1:
        X = np.reshape(X, np.prod(X.shape))
    if range is None:
        range = (X.min(), X.max())
    if color is None:
        color = 'blue'
    mu, std = st.norm.fit(X)
    x_line = np.linspace(range[0], range[1], line_points)
    y_line = st.norm.pdf(x_line, loc = mu, scale = std)
    ax.plot(x_line, y_line, '-', color = color)
    ax.plot([mu, mu], [0, np.max([y_line.max(), vals.max()])], '--', color = color)

def hist(X : Union[list, ndarray],
         bins: Optional[int] = None,
         range: Optional[tuple] = None,
         density: bool = True,
         color: Optional[Union[str,list,tuple]] = None,
         alpha: float = 1,
         fit_line: bool = True,
         line_points: int = 1000,
         x_label: Optional[str] = None,
         y_label: Optional[str] = None,
         x_ticks: Optional[List[str]] = None,
         legend: Optional[List[str]] = None,
         grid: bool = True,
         xlim: Optional[List[float]] = None,
         ylim: Optional[List[float]] = None,
         figsize: List[float] = [6.4, 4.8]):
    """
    Plot histogram
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0,0,1,1])

    if type(X) is not list:
        if type(color) is list:
            color = color[0]
        if type(legend) is list:
            legend = legend[0]
        vals, _, _ = _plot_hist(ax, X, bins = bins, range = range, density = density, 
                                         color = color, alpha = alpha, label = legend)

        if fit_line:
            _plot_fit_norm_line(ax, X, vals, range, line_points, color)
    else:
        if type(color) is not list:
            raise ValueError("The color must be a list.")
        if len(X) != len(color):
            raise ValueError("The length of color should be same as the length of X.")
        if type(legend) is not list:
            raise ValueError("The legend must be a list.")
        if len(X) != len(legend):
            raise ValueError("The length of legend should be same as the length of X.")
        vals_list = []
        for X_single_group, color_single_group, legend_single_group in zip(X, color, legend):
            vals, _, _ = _plot_hist(ax, X_single_group, bins = bins, range = range, density = density, 
                                             color = color_single_group, alpha = alpha, label = legend_single_group)
            vals_list.append(vals)
        for X_single_group, vals, color_single_group in zip(X, vals_list, color):
            _plot_fit_norm_line(ax, X_single_group, vals, range, line_points, color_single_group)

    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    if x_ticks is not None:
        ax.set_xticks(X, x_ticks)
    if legend is not None:
        ax.legend()
    ax.grid(grid)
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)

    return fig, ax

def shadowline_plot(X: Union[list, ndarray],
                    Y: ndarray,
                    fmt: str = '-',
                    x_label: Optional[str] = None,
                    y_label: Optional[str] = None,
                    x_ticks: Optional[List[str]] = None,
                    legend: Optional[List[str]] = None,
                    errorbar_type: str = 'std',
                    grid: bool = True,
                    xlim: Optional[List[float]] = None,
                    ylim: Optional[List[float]] = None,
                    figsize: List[float] = [6.4, 4.8]):
    """
    Plot shadow lines
    Line values are equal to the mean of all observations
    Shadow areas are calculated across observations
    (x axis: variable; y axis: observation)

    Parameters
    ----------
    X : ndarray
        x value of variables
    Y : ndarray
        Plot data
        Shape: (group_num, observation_num, variable_num)
    x_label: str
        Label of x axis
        Default is None
    y_label: str
        Label of y axis
        Default is None
    x_ticks: List[str]
        Ticks of x axis
        Default is None
    legend: List[str]
        Legend of groups
        Default is None
    errorbar_type: str
        Method of calculating error, including:
            - 'std': Standard derivation
            - '95ci': 95% confidence interval
        Default is 'std'
    grid: bool
        Whether plot grid
    xlim: List[float]
        Range of x axis
    ylim: List[float]
        Range of y axis
    """
    if type(X) == ndarray:
        if len(X.shape) > 2:
            raise ValueError("Dimention of X must be smaller than 3")
    if len(Y.shape) != 3:
        raise ValueError("Plot data must have 3 dimentions")
    group_num, observation_num, variable_num = Y.shape
    if x_ticks is not None:
        if len(x_ticks) != variable_num:
            raise ValueError("Length of 'x_ticks' should be equal to 3rd dimention of data")
    if legend is not None:
        if len(legend) != group_num:
            raise ValueError("Length of 'legend' should be equal to 1st dimention of data")
            
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0,0,1,1])
    colors = []
    for group_idx in range(group_num):
        Y_tmp = Y[group_idx,:,:]
        Y_mean = np.mean(Y_tmp,0)
        p = ax.plot(X,Y_mean,fmt)
        colors.append(p[0].get_color())
    for group_idx in range(group_num):
        Y_tmp = Y[group_idx,:,:]
        Y_mean = np.mean(Y_tmp,0)
        if errorbar_type.lower() == 'std':
            Y_error = np.std(Y_tmp, 0)
        elif errorbar_type.lower() == '95ci':
            Y_error = cal_CI95(Y_tmp)
        else:
            raise ValueError("Unknow 'errorbar_type'. 'errorbar_type' must be 'std' or '95ci'")
        ax.fill_between(X, Y_mean-Y_error, Y_mean+Y_error ,alpha=0.3, facecolor=colors[group_idx])
    
    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    if x_ticks is not None:
        ax.set_xticks(X, x_ticks)
    if legend is not None:
        ax.legend(labels=legend)
    ax.grid(grid)
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)

    return fig, ax


def bar_plot(Y: ndarray,
             bar_sep: float = 0.25,
             x_label: Optional[str] = None,
             y_label: Optional[str] = None,
             x_ticks: Optional[List[str]] = None,
             grid: bool = True,
             xlim: Optional[List[float]] = None,
             ylim: Optional[List[float]] = None,
             figsize: List[float] = [6.4, 4.8]):
    """
    Plot bars

    For each group, a set of bars will be ploted on all variables
    Bar heights are equal to the mean of all observations
    (x axis: variable; y axis: observation)

    Parameters
    -----------
    Y: ndarray
        Plot data
        Shape: (observation_num, variable_num)
    bar_sep: Optional[float]
        Separation between two variables
        Default is 0.25
    x_label: str
        Label of x axis
        Default is None
    y_label: str
        Label of y axis
        Default is None
    x_ticks: List[str]
        Ticks of x axis
        Default is None
    grid: bool
        Whether plot grid
    xlim: List[float]
        Range of x axis
    ylim: List[float]
        Range of y axis
    """
    if len(Y.shape) > 2:
        raise ValueError("Plot data must have 3 dimentions")
    observation_num, variable_num = Y.shape
    if x_ticks is not None:
        if len(x_ticks) != variable_num:
            raise ValueError("Length of 'x_ticks' should be equal to 3rd dimention of data")

    x_center = np.arange(1, variable_num+1, 1)
    width = (1-bar_sep)/1
    
    # colors = cm.get_cmap('hsv', group_num).colors
    
    fig = plt.figure(figsize = figsize)
    ax = fig.add_axes([0,0,1,1])
    Y_mean = np.mean(Y,0)
    ax.bar(x_center, Y_mean, width = width)

    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    if x_ticks is not None:
        ax.set_xticks(x_center, x_ticks)
    else:
        ax.set_xticks(x_center, x_center)
    ax.grid(grid)
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)

    return fig, ax


def bar_plot_with_errorbar(Y: ndarray,
             bar_sep: float = 0.25,
             x_label: Optional[str] = None,
             y_label: Optional[str] = None,
             x_ticks: Optional[List[str]] = None,
             legend: Optional[List[str]] = None,
             errorbar_type: str = 'std',
             grid: bool = True,
             xlim: Optional[List[float]] = None,
             ylim: Optional[List[float]] = None,
             figsize: List[float] = [6.4, 4.8]):
    """
    Plot bars

    For each group, a set of bars will be ploted on all variables
    Bar heights are equal to the mean of all observations
    Error bar are calculated across observations
    (x axis: variable; y axis: observation)

    Parameters
    -----------
    Y: ndarray
        Plot data
        Shape: (group_num, observation_num, variable_num)
    bar_sep: Optional[float]
        Separation between two variables
        Default is 0.25
    x_label: str
        Label of x axis
        Default is None
    y_label: str
        Label of y axis
        Default is None
    x_ticks: List[str]
        Ticks of x axis
        Default is None
    legend: List[str]
        Legend of groups
        Default is None
    errorbar_type: str
        Method of calculating error, including:
            - 'std': Standard derivation
            - '95ci': 95% confidence interval
        Default is 'std'
    grid: bool
        Whether plot grid
    xlim: List[float]
        Range of x axis
    ylim: List[float]
        Range of y axis
    """
    if len(Y.shape) == 2:
        Y = np.expand_dims(Y, axis=0)
    if len(Y.shape) != 3:
        raise ValueError("Plot data must have 3 dimentions")
    group_num, observation_num, variable_num = Y.shape
    if x_ticks is not None:
        if len(x_ticks) != variable_num:
            raise ValueError("Length of 'x_ticks' should be equal to 3rd dimention of data")
    if legend is not None:
        if len(legend) != group_num:
            raise ValueError("Length of 'legend' should be equal to 1st dimention of data")

    x_center = np.arange(1, variable_num+1, 1)
    width = (1-bar_sep)/group_num
    
    # colors = cm.get_cmap('hsv', group_num).colors
    
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0,0,1,1])
    x = x_center - 0.5 + bar_sep/2 + width/2
    for group_idx in range(group_num):
        Y_tmp = Y[group_idx,:,:]
        Y_mean = np.mean(Y_tmp,0)
        ax.bar(x, Y_mean, width = width) #, color = colors[group_idx])
        x = x + width
    x = x_center - 0.5 + bar_sep/2 + width/2
    for group_idx in range(group_num):
        Y_tmp = Y[group_idx,:,:]
        Y_mean = np.mean(Y_tmp,0)
        if errorbar_type.lower() == 'std':
            Y_error = np.std(Y_tmp, 0)
        elif errorbar_type.lower() == '95ci':
            Y_error = cal_CI95(Y_tmp)
        else:
            raise ValueError("Unknow 'errorbar_type'. 'errorbar_type' must be 'std' or '95ci'")
        ax.errorbar(x=x, y=Y_mean, yerr=Y_error, elinewidth=2,capsize=4,fmt='none',ecolor='black')
        x = x + width

    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)
    if x_ticks is not None:
        ax.set_xticks(x_center, x_ticks)
    else:
        ax.set_xticks(x_center, x_center)
    if legend is not None:
        ax.legend(labels=legend)
    ax.grid(grid)
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)

    return fig, ax
        
def cal_CI95(X: ndarray) -> ndarray:
    """
    Calculate 95% confidence interval

    Parameters
    ----------
    X : ndarray

    Returns
    -------
    CI95 : ndarray
    """
    N = X.shape[0]
    SEM = np.std(X,0)/np.sqrt(N)
    CI95 = SEM * st.t.ppf(0.95, N-1)
    
    # row_num, col_num = X.shape
    # CI95 = np.zeros((2,col_num))
    # for i in range(col_num):
    #     x_tmp = X[:,i]
    #     interval = st.t.interval(0.95, df = row_num-1, loc = np.mean(x_tmp), scale=st.sem(x_tmp))
    #     CI95[0,i] = interval[0]
    #     CI95[1,i] = interval[1]
    return CI95