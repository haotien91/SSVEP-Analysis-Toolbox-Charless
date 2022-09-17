# -*- coding: utf-8 -*-
"""
CCA based recognition methods
"""

from typing import Union, Optional, Dict, List, Tuple, Callable
from numpy import ndarray
from joblib import Parallel, delayed
from functools import partial
from copy import deepcopy
import warnings

import numpy as np
import scipy.linalg as slin
import scipy.stats as stats

from .basemodel import BaseModel
from .utils import qr_remove_mean, qr_inverse, mldivide, canoncorr, qr_list, gen_template, sort



def _r_cca_canoncorr_withUV(X: ndarray,
                            Y: List[ndarray],
                            U: ndarray,
                            V: ndarray) -> ndarray:
    """
    Calculate correlation of CCA based on canoncorr for single trial data using existing U and V

    Parameters
    ----------
    X : ndarray
        Single trial EEG data
        EEG shape: (filterbank_num, channel_num, signal_len)
    Y : List[ndarray]
        List of reference signals
    U : ndarray
        Spatial filter
        shape: (filterbank_num * stimulus_num * channel_num * n_component)
    V : ndarray
        Weights of harmonics
        shape: (filterbank_num * stimulus_num * harmonic_num * n_component)

    Returns
    -------
    R : ndarray
        Correlation
        shape: (filterbank_num * stimulus_num)
    """
    filterbank_num, channel_num, signal_len = X.shape
    if len(Y[0].shape)==2:
        harmonic_num = Y[0].shape[0]
    elif len(Y[0].shape)==3:
        harmonic_num = Y[0].shape[1]
    else:
        raise ValueError('Unknown data type')
    stimulus_num = len(Y)
    
    R = np.zeros((filterbank_num, stimulus_num))
    
    for k in range(filterbank_num):
        tmp = X[k,:,:]
        for i in range(stimulus_num):
            if len(Y[i].shape)==2:
                Y_tmp = Y[i]
            elif len(Y[i].shape)==3:
                Y_tmp = Y[i][k,:,:]
            else:
                raise ValueError('Unknown data type')
            
            A_r = U[k,i,:,:]
            B_r = V[k,i,:,:]
            
            a = A_r.T @ tmp
            b = B_r.T @ Y_tmp
            a = np.reshape(a, (-1))
            b = np.reshape(b, (-1))
            
            # r2 = stats.pearsonr(a, b)[0]
            r = stats.pearsonr(a, b)[0]
            R[k,i] = r
    return R

def _r_cca_qr_withUV(X: ndarray,
                  Y_Q: List[ndarray],
                  Y_R: List[ndarray],
                  Y_P: List[ndarray],
                  U: ndarray,
                  V: ndarray) -> ndarray:
    """
    Calculate correlation of CCA based on qr decomposition for single trial data using existing U and V

    Parameters
    ----------
    X : ndarray
        Single trial EEG data
        EEG shape: (filterbank_num, channel_num, signal_len)
    Y_Q : List[ndarray]
        Q of reference signals
    Y_R: List[ndarray]
        R of reference signals
    Y_P: List[ndarray]
        P of reference signals
    U : ndarray
        Spatial filter
        shape: (filterbank_num * stimulus_num * channel_num * n_component)
    V : ndarray
        Weights of harmonics
        shape: (filterbank_num * stimulus_num * harmonic_num * n_component)

    Returns
    -------
    R : ndarray
        Correlation
        shape: (filterbank_num * stimulus_num)
    """
    filterbank_num, channel_num, signal_len = X.shape
    harmonic_num = Y_R[0].shape[-1]
    stimulus_num = len(Y_Q)
    
    Y = [qr_inverse(Y_Q[i],Y_R[i],Y_P[i]) for i in range(len(Y_Q))]
    if len(Y[0].shape)==2: # reference
        Y = [Y_tmp.T for Y_tmp in Y]
    elif len(Y[0].shape)==3: # template
        Y = [np.transpose(Y_tmp, (0,2,1)) for Y_tmp in Y]
    else:
        raise ValueError('Unknown data type')
    
    R = np.zeros((filterbank_num, stimulus_num))
    
    for k in range(filterbank_num):
        tmp = X[k,:,:]
        X_Q, X_R, X_P = qr_remove_mean(tmp.T)
        for i in range(stimulus_num):
            if len(Y[i].shape)==2:
                Y_tmp = Y[i]
            elif len(Y[i].shape)==3:
                Y_tmp = Y[i][k,:,:]
            else:
                raise ValueError('Unknown data type')
                
            A_r = U[k,i,:,:]
            B_r = V[k,i,:,:]
            
            a = A_r.T @ tmp
            b = B_r.T @ Y_tmp
            a = np.reshape(a, (-1))
            b = np.reshape(b, (-1))
            
            # r2 = stats.pearsonr(a, b)[0]
            r = stats.pearsonr(a, b)[0]
            R[k,i] = r
    return R
    
def _r_cca_canoncorr(X: ndarray,
                     Y: List[ndarray],
                     n_component: int,
                     force_output_UV: Optional[bool] = False) -> Union[ndarray, Tuple[ndarray, ndarray, ndarray]]:
    """
    Calculate correlation of CCA based on canoncorr for single trial data 

    Parameters
    ----------
    X : ndarray
        Single trial EEG data
        EEG shape: (filterbank_num, channel_num, signal_len)
    Y : List[ndarray]
        List of reference signals
    n_component : int
        Number of eigvectors for spatial filters.
    force_output_UV : Optional[bool]
        Whether return spatial filter 'U' and weights of harmonics 'V'

    Returns
    -------
    R : ndarray
        Correlation
        shape: (filterbank_num * stimulus_num)
    U : ndarray
        Spatial filter
        shape: (filterbank_num * stimulus_num * channel_num * n_component)
    V : ndarray
        Weights of harmonics
        shape: (filterbank_num * stimulus_num * harmonic_num * n_component)
    """
    filterbank_num, channel_num, signal_len = X.shape
    if len(Y[0].shape)==2:
        harmonic_num = Y[0].shape[0]
    elif len(Y[0].shape)==3:
        harmonic_num = Y[0].shape[1]
    else:
        raise ValueError('Unknown data type')
    stimulus_num = len(Y)
    
    # R1 = np.zeros((filterbank_num,stimulus_num))
    # R2 = np.zeros((filterbank_num,stimulus_num))
    R = np.zeros((filterbank_num, stimulus_num))
    U = np.zeros((filterbank_num, stimulus_num, channel_num, n_component))
    V = np.zeros((filterbank_num, stimulus_num, harmonic_num, n_component))
    
    for k in range(filterbank_num):
        tmp = X[k,:,:]
        for i in range(stimulus_num):
            if len(Y[i].shape)==2:
                Y_tmp = Y[i]
            elif len(Y[i].shape)==3:
                Y_tmp = Y[i][k,:,:]
            else:
                raise ValueError('Unknown data type')
                
            if n_component == 0 and force_output_UV is False:
                D = canoncorr(tmp.T, Y_tmp.T, False)
                r = D[0]
            else:
                A_r, B_r, D = canoncorr(tmp.T, Y_tmp.T, True)
                
                a = A_r[:channel_num, :n_component].T @ tmp
                b = B_r[:harmonic_num, :n_component].T @ Y_tmp
                a = np.reshape(a, (-1))
                b = np.reshape(b, (-1))
                
                r = stats.pearsonr(a, b)[0]
                U[k,i,:,:] = A_r[:channel_num, :n_component]
                V[k,i,:,:] = B_r[:harmonic_num, :n_component]
                
            R[k,i] = r
    if force_output_UV:
        return R, U, V
    else:
        return R

def _r_cca_qr(X: ndarray,
           Y_Q: List[ndarray],
           Y_R: List[ndarray],
           Y_P: List[ndarray],
           n_component: int,
           force_output_UV: Optional[bool] = False) -> Union[ndarray, Tuple[ndarray, ndarray, ndarray]]:
    """
    Calculate correlation of CCA based on QR decomposition for single trial data 

    Parameters
    ----------
    X : ndarray
        Single trial EEG data
        EEG shape: (filterbank_num, channel_num, signal_len)
    Y_Q : List[ndarray]
        Q of reference signals
    Y_R: List[ndarray]
        R of reference signals
    Y_P: List[ndarray]
        P of reference signals
    n_component : int
        Number of eigvectors for spatial filters.
    force_output_UV : Optional[bool]
        Whether return spatial filter 'U' and weights of harmonics 'V'

    Returns
    -------
    R : ndarray
        Correlation
        shape: (filterbank_num * stimulus_num)
    U : ndarray
        Spatial filter
        shape: (filterbank_num * stimulus_num * channel_num * n_component)
    V : ndarray
        Weights of harmonics
        shape: (filterbank_num * stimulus_num * harmonic_num * n_component)
    """
    filterbank_num, channel_num, signal_len = X.shape
    harmonic_num = Y_R[0].shape[-1]
    stimulus_num = len(Y_Q)
    
    Y = [qr_inverse(Y_Q[i],Y_R[i],Y_P[i]) for i in range(len(Y_Q))]
    if len(Y[0].shape)==2: # reference
        Y = [Y_tmp.T for Y_tmp in Y]
    elif len(Y[0].shape)==3: # template
        Y = [np.transpose(Y_tmp, (0,2,1)) for Y_tmp in Y]
    else:
        raise ValueError('Unknown data type')
    
    # R1 = np.zeros((filterbank_num,stimulus_num))
    # R2 = np.zeros((filterbank_num,stimulus_num))
    R = np.zeros((filterbank_num, stimulus_num))
    U = np.zeros((filterbank_num, stimulus_num, channel_num, n_component))
    V = np.zeros((filterbank_num, stimulus_num, harmonic_num, n_component))
    
    for k in range(filterbank_num):
        tmp = X[k,:,:]
        X_Q, X_R, X_P = qr_remove_mean(tmp.T)
        for i in range(stimulus_num):
            if len(Y_Q[i].shape)==2: # reference
                Y_Q_tmp = Y_Q[i]
                Y_R_tmp = Y_R[i]
                Y_P_tmp = Y_P[i]
                Y_tmp = Y[i]
            elif len(Y_Q[i].shape)==3: # template
                Y_Q_tmp = Y_Q[i][k,:,:]
                Y_R_tmp = Y_R[i][k,:,:]
                Y_P_tmp = Y_P[i][k,:]
                Y_tmp = Y[i][k,:,:]
            else:
                raise ValueError('Unknown data type')
            svd_X = X_Q.T @ Y_Q_tmp
            if svd_X.shape[0]>svd_X.shape[1]:
                full_matrices=False
            else:
                full_matrices=True
            
            if n_component == 0 and force_output_UV is False:
                D = slin.svd(svd_X,
                             full_matrices=full_matrices,
                             compute_uv=False,
                             check_finite=False,
                             lapack_driver='gesvd')
                # r1 = D[0]
                r = D[0]
            else:
                L, D, M = slin.svd(svd_X,
                                 full_matrices=full_matrices,
                                 check_finite=False,
                                 lapack_driver='gesvd')
                M = M.T
                A = mldivide(X_R, L) * np.sqrt(signal_len - 1)
                B = mldivide(Y_R_tmp, M) * np.sqrt(signal_len - 1)
                A_r = np.zeros(A.shape)
                for n in range(A.shape[0]):
                    A_r[X_P[n],:] = A[n,:]
                B_r = np.zeros(B.shape)
                for n in range(B.shape[0]):
                    B_r[Y_P_tmp[n],:] = B[n,:]
                
                a = A_r[:channel_num, :n_component].T @ tmp
                b = B_r[:harmonic_num, :n_component].T @ Y_tmp
                a = np.reshape(a, (-1))
                b = np.reshape(b, (-1))
                
                # r2 = stats.pearsonr(a, b)[0]
                r = stats.pearsonr(a, b)[0]
                U[k,i,:,:] = A_r[:channel_num, :n_component]
                V[k,i,:,:] = B_r[:harmonic_num, :n_component]
                
            # R1[k,i] = r1
            # R2[k,i] = r2
            R[k,i] = r
    if force_output_UV:
        return R, U, V
    else:
        return R
   
def SCCA(n_component: int = 1,
         n_jobs: Optional[int] = None,
         weights_filterbank: Optional[List[float]] = None,
         force_output_UV: bool = False,
         update_UV: bool = True,
         cca_type: str = 'qr'):
    """
    Generate sCCA model

    Parameters
    ----------
    n_component : Optional[int], optional
        Number of eigvectors for spatial filters. The default is 1.
    n_jobs : Optional[int], optional
        Number of CPU for computing different trials. The default is None.
    weights_filterbank : Optional[List[float]], optional
        Weights of spatial filters. The default is None.
    force_output_UV : Optional[bool] 
        Whether store U and V. Default is False
    update_UV: Optional[bool]
        Whether update U and V in next time of applying "predict" 
        If false, and U and V have not been stored, they will be stored
        Default is True
    cca_type : Optional[str], optional
        Methods for computing corr.
        'qr' - QR decomposition
        'canoncorr' - Canoncorr
        The default is 'qr'.

    Returns
    -------
    sCCA model: Union[SCCA_qr, SCCA_canoncorr]
        if cca_type is 'qr' -> SCCA_qr
        if cca_type is 'canoncorr' -> SCCA_canoncorr
    """
    if cca_type.lower() == 'qr':
        return SCCA_qr(n_component,
                       n_jobs,
                       weights_filterbank,
                       force_output_UV,
                       update_UV)
    elif cca_type.lower() == 'canoncorr':
        return SCCA_canoncorr(n_component,
                              n_jobs,
                              weights_filterbank,
                              force_output_UV,
                              update_UV)
    else:
        raise ValueError('Unknown cca_type')

class OACCA(BaseModel):
    """
    Online CCA based on canoncorr
    """
    def __init__(self,
                 n_jobs: Optional[int] = None,
                 weights_filterbank: Optional[List[float]] = None):
        super().__init__(ID = 'OACCA',
                         n_component = 1,
                         n_jobs = n_jobs,
                         weights_filterbank = weights_filterbank)
        self.model['U0'] = None
        self.model['U'] = None
        self.model['V'] = None

    def __copy__(self):
        copy_model = OACCA(n_jobs = self.n_jobs,
                           weights_filterbank = self.model['weights_filterbank'])
        copy_model.model = deepcopy(self.model)
        return copy_model

    def fit(self,
            freqs: Optional[List[float]] = None,
            X: Optional[List[ndarray]] = None,
            Y: Optional[List[int]] = None,
            ref_sig: Optional[List[ndarray]] = None):
        if ref_sig is None:
            raise ValueError('OACCA requires sine-cosine-based reference signal')
           
        self.model['ref_sig'] = ref_sig

        self.model['covar_mat'] = None
        self.model['Cxx'] = None
        self.model['Cxy'] = None

    def predict(self,
                X: List[ndarray]) -> List[int]:
        weights_filterbank = self.model['weights_filterbank']
        if weights_filterbank is None:
            weights_filterbank = [1 for _ in range(X[0].shape[0])]
        if type(weights_filterbank) is list:
            weights_filterbank = np.expand_dims(np.array(weights_filterbank),1).T
        else:
            if len(weights_filterbank.shape) != 2:
                raise ValueError("'weights_filterbank' has wrong shape")
            if weights_filterbank.shape[0] != 1:
                weights_filterbank = weights_filterbank.T
        if weights_filterbank.shape[0] != 1:
            raise ValueError("'weights_filterbank' has wrong shape")

        n_component = self.n_component
        Y = self.model['ref_sig']
        stimulus_num = len(Y)
        harmonic_num, _ = Y[0].shape
        # Calculate Res
        Y_pred = []
        for x_single_trial in X:
            filterbank_num, channel_num, signal_len = x_single_trial.shape
            # Calculate res of this step
            cca_r, cca_sfx, cca_sfy = _r_cca_canoncorr(x_single_trial,Y,n_component,True)
            if (self.model['U'] is not None) and (self.model['V'] is not None):
                r2 = _r_cca_canoncorr_withUV(x_single_trial,Y,self.model['U'],self.model['V'])
            else:
                r2 = 0
            if self.model['U0'] is not None:
                x_single_trial_filtered = deepcopy(x_single_trial)
                for k in range(filterbank_num):
                    x_single_trial_filtered[k,:,:] = self.model['U0'][k,0,:,:].T @ x_single_trial_filtered[k,:,:]
                r3 = _r_cca_canoncorr(x_single_trial_filtered,Y,n_component,False)
            else:
                r3 = 0
            oacca_res = int( np.argmax( weights_filterbank @ (cca_r + 
                                                                r2 +
                                                                r3)))
            cca_res = int( np.argmax( weights_filterbank @ cca_r))
            prototype_res = int( np.argmax( weights_filterbank @ (cca_r +
                                                                    r3)))
            # print([oacca_res, cca_res, prototype_res])
            # print(x_single_trial.shape)
            # raise ValueError
            Y_pred.append(oacca_res)
            # Update parameters
            if self.model['covar_mat'] is None:
                self.model['covar_mat'] = np.zeros((channel_num, channel_num, filterbank_num))
                self.model['Cxx'] = np.zeros((channel_num, channel_num, filterbank_num))
                self.model['Cxy'] = np.zeros((channel_num, harmonic_num, filterbank_num))
            for k in range(filterbank_num):
                # Calculate prototype
                if cca_res == oacca_res:
                    if self.model['U0'] is None:
                        self.model['U0'] = np.zeros((filterbank_num, stimulus_num, channel_num, n_component))
                    sf1x = cca_sfx[k,cca_res,:,:] # (filterbank_num * stimulus_num * channel_num * n_component)
                    sf1x = sf1x/np.linalg.norm(sf1x)
                    # sf1y = cca_sfy[k,cca_res,:,:]
                    # sf1y = sf1y/np.linalg.norm(sf1y)

                    self.model['covar_mat'][:,:,k] = self.model['covar_mat'][:,:,k] + sf1x @ sf1x.T
                    eig_d1, eig_v1 = slin.eig(self.model['covar_mat'][:,:,k])
                    sort_idx = np.argsort(eig_d1)[::-1]
                    eig_vec=eig_v1[:,sort_idx]
                    u0 = eig_vec[:channel_num,0]
                    if np.iscomplex(eig_vec).any():
                        warnings.warn("Warning: Imaginary part of U0 is ignored.")
                        u0 = np.real(u0)
                    
                    for class_i in range(stimulus_num):
                        self.model['U0'][k,class_i,:,0] = u0 # eig_vec[:channel_num,0]
                # Calculate multi-stimulus 
                if self.model['U'] is None:
                        self.model['U'] = np.zeros((filterbank_num, stimulus_num, channel_num, n_component))
                if self.model['V'] is None:
                        self.model['V'] = np.zeros((filterbank_num, stimulus_num, harmonic_num, n_component))
                filteredData = x_single_trial[k,:,:]
                sinTemplate = Y[prototype_res][:,:signal_len]

                self.model['Cxx'][:,:,k] = self.model['Cxx'][:,:,k] + filteredData @ filteredData.T
                self.model['Cxy'][:,:,k] = self.model['Cxy'][:,:,k] + filteredData @ sinTemplate.T

                CCyy = np.eye(harmonic_num)
                CCyx = self.model['Cxy'][:,:,k].T
                CCxx = self.model['Cxx'][:,:,k]
                CCxy = self.model['Cxy'][:,:,k]
                A1 = np.concatenate((np.zeros(CCxx.shape), CCxy), axis = 1)
                A2 = np.concatenate((CCyx, np.zeros(CCyy.shape)), axis = 1)
                A = np.concatenate((A1, A2), axis = 0)
                B1 = np.concatenate((CCxx, np.zeros(CCxy.shape)), axis = 1)
                B2 = np.concatenate((np.zeros(CCyx.shape), CCyy), axis = 1)
                B = np.concatenate((B1, B2), axis = 0)
                eig_d1, eig_v1 = slin.eig(A, B)
                sort_idx = np.argsort(eig_d1)[::-1]
                u1 = eig_v1[:channel_num,sort_idx]
                v1 = eig_v1[channel_num:,sort_idx]
                if u1[0,0] == 1:
                    warnings.warn("Warning: updated U is not meaningful and thus adjusted.")
                    u1 = np.zeros((channel_num,1))
                    u1[-3:] = 1
                u1 = u1[:,0]
                v1 = v1[:,0]
                if np.iscomplex(eig_v1).any():
                    warnings.warn("Warning: Imaginary part of U and V is ignored.")
                    u1 = np.real(u1)
                    v1 = np.real(v1)
                for class_i in range(stimulus_num):
                    self.model['U'][k,class_i,:,0] = u1 # u1[:,0]
                    self.model['V'][k,class_i,:,0] = v1 # v1[:,0]
        return Y_pred



class SCCA_canoncorr(BaseModel):
    """
    Standard CCA based on canoncorr
    
    Computational time - Long
    Required memory - Small
    """
    def __init__(self,
                 n_component: int = 1,
                 n_jobs: Optional[int] = None,
                 weights_filterbank: Optional[List[float]] = None,
                 force_output_UV: bool = False,
                 update_UV: bool = True):
        """
        Special Parameters
        ----------
        force_output_UV : Optional[bool] 
            Whether store U and V. Default is False
        update_UV: Optional[bool]
            Whether update U and V in next time of applying "predict" 
            If false, and U and V have not been stored, they will be stored
            Default is True
        """
        super().__init__(ID = 'sCCA (canoncorr)',
                         n_component = n_component,
                         n_jobs = n_jobs,
                         weights_filterbank = weights_filterbank)
        self.force_output_UV = force_output_UV
        self.update_UV = update_UV
        
        self.model['U'] = None # Spatial filter of EEG
        self.model['V'] = None # Weights of harmonics
        
    def __copy__(self):
        copy_model = SCCA_canoncorr(n_component = self.n_component,
                                    n_jobs = self.n_jobs,
                                    weights_filterbank = self.model['weights_filterbank'],
                                    force_output_UV = self.force_output_UV,
                                    update_UV = self.update_UV)
        copy_model.model = deepcopy(self.model)
        return copy_model
        
    def fit(self,
            freqs: Optional[List[float]] = None,
            X: Optional[List[ndarray]] = None,
            Y: Optional[List[int]] = None,
            ref_sig: Optional[List[ndarray]] = None):
        if ref_sig is None:
            raise ValueError('sCCA requires sine-cosine-based reference signal')
           
            
        self.model['ref_sig'] = ref_sig
        
    def predict(self,
                X: List[ndarray]) -> List[int]:
        weights_filterbank = self.model['weights_filterbank']
        if weights_filterbank is None:
            weights_filterbank = [1 for _ in range(X[0].shape[0])]
        if type(weights_filterbank) is list:
            weights_filterbank = np.expand_dims(np.array(weights_filterbank),1).T
        else:
            if len(weights_filterbank.shape) != 2:
                raise ValueError("'weights_filterbank' has wrong shape")
            if weights_filterbank.shape[0] != 1:
                weights_filterbank = weights_filterbank.T
        if weights_filterbank.shape[0] != 1:
            raise ValueError("'weights_filterbank' has wrong shape")
        n_component = self.n_component
        Y = self.model['ref_sig']
        force_output_UV = self.force_output_UV
        update_UV = self.update_UV
        
        if update_UV or self.model['U'] is None or self.model['V'] is None:
            if force_output_UV or not update_UV:
                r, U, V = zip(*Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_canoncorr, n_component=n_component, Y=Y, force_output_UV=True))(a) for a in X))
                self.model['U'] = U
                self.model['V'] = V
            else:
                r = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_canoncorr, n_component=n_component, Y=Y, force_output_UV=False))(a) for a in X)
        else:
            U = self.model['U']
            V = self.model['V']
            r = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_canoncorr_withUV, Y=Y))(X=a, U=u, V=v) for a, u, v in zip(X,U,V))
        
        Y_pred = [int(np.argmax(weights_filterbank @ r_single, axis = 1)) for r_single in r]
        
        return Y_pred
     

class SCCA_qr(BaseModel):
    """
    Standard CCA based on qr decomposition
    
    Computational time - Short
    Required memory - Large
    """
    def __init__(self,
                 n_component: int = 1,
                 n_jobs: Optional[int] = None,
                 weights_filterbank: Optional[List[float]] = None,
                 force_output_UV: bool = False,
                 update_UV: bool = True):
        """
        Special Parameters
        ----------
        force_output_UV : Optional[bool] 
            Whether store U and V. Default is False
        update_UV: Optional[bool]
            Whether update U and V in next time of applying "predict" 
            If false, and U and V have not been stored, they will be stored
            Default is True
        """
        super().__init__(ID = 'sCCA (qr)',
                         n_component = n_component,
                         n_jobs = n_jobs,
                         weights_filterbank = weights_filterbank)
        self.force_output_UV = force_output_UV
        self.update_UV = update_UV
        
        self.model['U'] = None # Spatial filter of EEG
        self.model['V'] = None # Weights of harmonics
        
    def __copy__(self):
        copy_model = SCCA_qr(n_component = self.n_component,
                                    n_jobs = self.n_jobs,
                                    weights_filterbank = self.model['weights_filterbank'],
                                    force_output_UV = self.force_output_UV,
                                    update_UV = self.update_UV)
        copy_model.model = deepcopy(self.model)
        return copy_model
        
    def fit(self,
            freqs: Optional[List[float]] = None,
            X: Optional[List[ndarray]] = None,
            Y: Optional[List[int]] = None,
            ref_sig: Optional[List[ndarray]] = None):
        if ref_sig is None:
            raise ValueError('sCCA requires sine-cosine-based reference signal')
            
        ref_sig_Q, ref_sig_R, ref_sig_P = qr_list(ref_sig)
            
        self.model['ref_sig_Q'] = ref_sig_Q
        self.model['ref_sig_R'] = ref_sig_R
        self.model['ref_sig_P'] = ref_sig_P
        
    def predict(self,
                X: List[ndarray]) -> List[int]:
        weights_filterbank = self.model['weights_filterbank']
        if weights_filterbank is None:
            weights_filterbank = [1 for _ in range(X[0].shape[0])]
        if type(weights_filterbank) is list:
            weights_filterbank = np.expand_dims(np.array(weights_filterbank),1).T
        else:
            if len(weights_filterbank.shape) != 2:
                raise ValueError("'weights_filterbank' has wrong shape")
            if weights_filterbank.shape[0] != 1:
                weights_filterbank = weights_filterbank.T
        if weights_filterbank.shape[0] != 1:
            raise ValueError("'weights_filterbank' has wrong shape")
        n_component = self.n_component
        Y_Q = self.model['ref_sig_Q']
        Y_R = self.model['ref_sig_R']
        Y_P = self.model['ref_sig_P']
        force_output_UV = self.force_output_UV
        update_UV = self.update_UV
        
        if update_UV or self.model['U'] is None or self.model['V'] is None:
            if force_output_UV or not update_UV:
                r, U, V = zip(*Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr, n_component=n_component, Y_Q=Y_Q, Y_R=Y_R, Y_P=Y_P, force_output_UV=True))(a) for a in X))
                self.model['U'] = U
                self.model['V'] = V
            else:
                r = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr, n_component=n_component, Y_Q=Y_Q, Y_R=Y_R, Y_P=Y_P, force_output_UV=False))(a) for a in X)
        else:
            U = self.model['U']
            V = self.model['V']
            r = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr_withUV, Y_Q=Y_Q, Y_R=Y_R, Y_P=Y_P))(X=a, U=u, V=v) for a, u, v in zip(X,U,V))
        
        Y_pred = [int(np.argmax(weights_filterbank @ r_single, axis = 1)) for r_single in r]
        
        return Y_pred
    
    
    
class ECCA(BaseModel):
    """
    eCCA
    """
    def __init__(self,
                 n_component: int = 1,
                 n_jobs: Optional[int] = None,
                 weights_filterbank: Optional[List[float]] = None,
                 # force_output_UV: Optional[bool] = False,
                 update_UV: bool = True):
        """
        Special Parameters
        ----------
        update_UV: Optional[bool]
            Whether update U and V in next time of applying "predict" 
            If false, and U and V have not been stored, they will be stored
            Default is True
        """
        super().__init__(ID = 'eCCA',
                         n_component = n_component,
                         n_jobs = n_jobs,
                         weights_filterbank = weights_filterbank)
        # self.force_output_UV = force_output_UV
        self.update_UV = update_UV
        
        self.model['U1'] = None
        self.model['V1'] = None
        
        self.model['U2'] = None
        self.model['V2'] = None
        
        self.model['U3'] = None
        self.model['V3'] = None
        
    def __copy__(self):
        copy_model = ECCA(n_component = self.n_component,
                            n_jobs = self.n_jobs,
                            weights_filterbank = self.model['weights_filterbank'],
                            update_UV = self.update_UV)
        copy_model.model = deepcopy(self.model)
        return copy_model
        
    def fit(self,
            freqs: Optional[List[float]] = None,
            X: Optional[List[ndarray]] = None,
            Y: Optional[List[int]] = None,
            ref_sig: Optional[List[ndarray]] = None):
        if ref_sig is None:
            raise ValueError('eCCA requires sine-cosine-based reference signal')
        if Y is None:
            raise ValueError('eCCA requires training label')
        if X is None:
            raise ValueError('eCCA requires training data')
            
        # generate reference realted QR
        ref_sig_Q, ref_sig_R, ref_sig_P = qr_list(ref_sig) # List of shape: (stimulus_num,);
                                                           # Template shape: (harmonic_num, signal_len)
        self.model['ref_sig_Q'] = ref_sig_Q # List of shape: (stimulus_num,);
        self.model['ref_sig_R'] = ref_sig_R
        self.model['ref_sig_P'] = ref_sig_P
        
        # generate template related QR
        template_sig = gen_template(X, Y) # List of shape: (stimulus_num,); 
                                           # Template shape: (filterbank_num, channel_num, signal_len)
        template_sig_Q, template_sig_R, template_sig_P = qr_list(template_sig)
        self.model['template_sig_Q'] = template_sig_Q # List of shape: (stimulus_num,);
        self.model['template_sig_R'] = template_sig_R
        self.model['template_sig_P'] = template_sig_P
        
        # spatial filters of template and reference: U3 and V3
        #   U3: (filterbank_num * stimulus_num * channel_num * n_component)
        #   V3: (filterbank_num * stimulus_num * harmonic_num * n_component)
        filterbank_num = template_sig[0].shape[0]
        stimulus_num = len(template_sig)
        channel_num = template_sig[0].shape[1]
        harmonic_num = ref_sig[0].shape[0]
        n_component = self.n_component
        U3 = np.zeros((filterbank_num, stimulus_num, channel_num, n_component))
        V3 = np.zeros((filterbank_num, stimulus_num, harmonic_num, n_component))
        for filterbank_idx in range(filterbank_num):
            U, V, _ = zip(*Parallel(n_jobs=self.n_jobs)(delayed(partial(canoncorr, force_output_UV = True))(X=template_sig_single[filterbank_idx,:,:].T, 
                                                                                                            Y=ref_sig_single.T) 
                                                        for template_sig_single, ref_sig_single in zip(template_sig,ref_sig)))
            for stim_idx, (u, v) in enumerate(zip(U,V)):
                U3[filterbank_idx, stim_idx, :, :] = u[:channel_num,:n_component]
                V3[filterbank_idx, stim_idx, :, :] = v[:harmonic_num,:n_component]
        self.model['U3'] = U3
        self.model['V3'] = V3
            
        
    def predict(self,
                X: List[ndarray]) -> List[int]:
        weights_filterbank = self.model['weights_filterbank']
        if weights_filterbank is None:
            weights_filterbank = [1 for _ in range(X[0].shape[0])]
        if type(weights_filterbank) is list:
            weights_filterbank = np.expand_dims(np.array(weights_filterbank),1).T
        else:
            if len(weights_filterbank.shape) != 2:
                raise ValueError("'weights_filterbank' has wrong shape")
            if weights_filterbank.shape[0] != 1:
                weights_filterbank = weights_filterbank.T
        if weights_filterbank.shape[0] != 1:
            raise ValueError("'weights_filterbank' has wrong shape")
        n_component = self.n_component
        update_UV = self.update_UV
        
        ref_sig_Q = self.model['ref_sig_Q']
        ref_sig_R = self.model['ref_sig_R']
        ref_sig_P = self.model['ref_sig_P']
        
        template_sig_Q = self.model['template_sig_Q'] 
        template_sig_R = self.model['template_sig_R'] 
        template_sig_P = self.model['template_sig_P'] 
        
        U3 = self.model['U3'] 
        V3 = self.model['V3'] 
        
        # r1
        if update_UV or self.model['U1'] is None or self.model['V1'] is None:
            r1, U1, V1 = zip(*Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr, n_component=n_component, Y_Q=ref_sig_Q, Y_R=ref_sig_R, Y_P=ref_sig_P, force_output_UV=True))(a) for a in X))
            self.model['U1'] = U1
            self.model['V1'] = V1
        else:
            U1 = self.model['U1']
            V1 = self.model['V1']
            r1 = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr_withUV, Y_Q=ref_sig_Q, Y_R=ref_sig_R, Y_P=ref_sig_P))(X=a, U=u, V=v) for a, u, v in zip(X,U1,V1))
        
        # r2
        if update_UV or self.model['U2'] is None:
            _, U2, _ = zip(*Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr, n_component=n_component, Y_Q=template_sig_Q, Y_R=template_sig_R, Y_P=template_sig_P, force_output_UV=True))(a) for a in X))
            self.model['U2'] = U2
        r2 = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr_withUV, Y_Q=template_sig_Q, Y_R=template_sig_R, Y_P=template_sig_P))(X=a, U=u, V=v) for a, u, v in zip(X,U2,U2))
        
        # r3
        r3 = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr_withUV, Y_Q=template_sig_Q, Y_R=template_sig_R, Y_P=template_sig_P))(X=a, U=u, V=v) for a, u, v in zip(X,U1,U1))
        
        # r4
        r4 = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_qr_withUV, Y_Q=template_sig_Q, Y_R=template_sig_R, Y_P=template_sig_P, U=U3, V=U3))(X=a) for a in X)
        
        
        Y_pred = [int( np.argmax( weights_filterbank @ (np.sign(r1_single) * np.square(r1_single) + 
                                                        np.sign(r2_single) * np.square(r2_single) +
                                                        np.sign(r3_single) * np.square(r3_single) +
                                                        np.sign(r4_single) * np.square(r4_single)))) for r1_single, r2_single, r3_single, r4_single in zip(r1, r2, r3, r4)]
        
        return Y_pred

class MSCCA(BaseModel):
    """
    ms-CCA
    """
    def __init__(self,
                 n_neighbor: int = 12,
                 n_component: int = 1,
                 n_jobs: Optional[int] = None,
                 weights_filterbank: Optional[List[float]] = None):
        """
        Special parameter
        ------------------
        n_neighbor: int
            Number of neighbors considered for computing spatical filter
        """
        super().__init__(ID = 'ms-CCA',
                         n_component = n_component,
                         n_jobs = n_jobs,
                         weights_filterbank = weights_filterbank)
        self.n_neighbor = n_neighbor
        
        self.model['U'] = None
        self.model['V'] = None
        
    def __copy__(self):
        copy_model = MSCCA(n_neighbor = self.n_neighbor,
                            n_component = self.n_component,
                            n_jobs = self.n_jobs,
                            weights_filterbank = self.model['weights_filterbank'])
        copy_model.model = deepcopy(self.model)
        return copy_model
        
    def fit(self,
            freqs: Optional[List[float]] = None,
            X: Optional[List[ndarray]] = None,
            Y: Optional[List[int]] = None,
            ref_sig: Optional[List[ndarray]] = None):
        if freqs is None:
            raise ValueError('ms-CCA requires the list of stimulus frequencies')
        if ref_sig is None:
            raise ValueError('ms-CCA requires sine-cosine-based reference signal')
        if Y is None:
            raise ValueError('ms-CCA requires training label')
        if X is None:
            raise ValueError('ms-CCA requires training data')
        
        # save reference
        self.model['ref_sig'] = ref_sig

        # generate template 
        template_sig = gen_template(X, Y) # List of shape: (stimulus_num,); 
                                           # Template shape: (filterbank_num, channel_num, signal_len)
        self.model['template_sig'] = template_sig

        # spatial filters of template and reference: U3 and V3
        #   U3: (filterbank_num * stimulus_num * channel_num * n_component)
        #   V3: (filterbank_num * stimulus_num * harmonic_num * n_component)
        filterbank_num = template_sig[0].shape[0]
        stimulus_num = len(template_sig)
        channel_num = template_sig[0].shape[1]
        harmonic_num = ref_sig[0].shape[0]
        n_component = self.n_component
        n_neighbor = self.n_neighbor
        # construct reference and template signals for ms-cca
        d0 = int(np.floor(n_neighbor/2))
        U = np.zeros((filterbank_num, stimulus_num, channel_num, n_component))
        V = np.zeros((filterbank_num, stimulus_num, harmonic_num, n_component))
        _, freqs_idx, return_freqs_idx = sort(freqs)
        ref_sig_sort = [ref_sig[i] for i in freqs_idx]
        template_sig_sort = [template_sig[i] for i in freqs_idx]
        ref_sig_mscca = []
        template_sig_mscca = []
        for class_idx in range(1,stimulus_num+1):
            if class_idx <= d0:
                start_idx = 0
                end_idx = n_neighbor
            elif class_idx > d0 and class_idx < (stimulus_num-d0+1):
                start_idx = class_idx - d0 - 1
                end_idx = class_idx + (n_neighbor-d0-1)
            else:
                start_idx = stimulus_num - n_neighbor
                end_idx = stimulus_num
            ref_sig_tmp = [ref_sig_sort[i] for i in range(start_idx, end_idx)]
            ref_sig_mscca.append(np.concatenate(ref_sig_tmp, axis = -1))
            template_sig_tmp = [template_sig_sort[i] for i in range(start_idx, end_idx)]
            template_sig_mscca.append(np.concatenate(template_sig_tmp, axis = -1))
        for filterbank_idx in range(filterbank_num):
            U_tmp, V_tmp, _ = zip(*Parallel(n_jobs=self.n_jobs)(delayed(partial(canoncorr, force_output_UV = True))(X=template_sig_single[filterbank_idx,:,:].T, 
                                                                                                                    Y=ref_sig_single.T) 
                                                        for template_sig_single, ref_sig_single in zip(template_sig_mscca,ref_sig_mscca)))
            for stim_idx, (u, v) in enumerate(zip(U_tmp,V_tmp)):
                U[filterbank_idx, stim_idx, :, :] = u[:channel_num,:n_component]
                V[filterbank_idx, stim_idx, :, :] = v[:harmonic_num,:n_component]
        self.model['U'] = U[:, return_freqs_idx, :, :]
        self.model['V'] = V[:, return_freqs_idx, :, :]
        
        
    def predict(self,
                X: List[ndarray]) -> List[int]:
        weights_filterbank = self.model['weights_filterbank']
        if weights_filterbank is None:
            weights_filterbank = [1 for _ in range(X[0].shape[0])]
        if type(weights_filterbank) is list:
            weights_filterbank = np.expand_dims(np.array(weights_filterbank),1).T
        else:
            if len(weights_filterbank.shape) != 2:
                raise ValueError("'weights_filterbank' has wrong shape")
            if weights_filterbank.shape[0] != 1:
                weights_filterbank = weights_filterbank.T
        if weights_filterbank.shape[0] != 1:
            raise ValueError("'weights_filterbank' has wrong shape")

        ref_sig = self.model['ref_sig']
        template_sig = self.model['template_sig']
        U = self.model['U']
        V = self.model['V']

        r1 = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_canoncorr_withUV, Y=ref_sig, U=U, V=V))(X=a) for a in X)
        r2 = Parallel(n_jobs=self.n_jobs)(delayed(partial(_r_cca_canoncorr_withUV, Y=template_sig, U=U, V=U))(X=a) for a in X)
        
        Y_pred = [int( np.argmax( weights_filterbank @ (np.sign(r1_single) * np.square(r1_single) + 
                                                        np.sign(r2_single) * np.square(r2_single)))) for r1_single, r2_single in zip(r1, r2)]
        
        return Y_pred
