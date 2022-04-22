import numpy as np
import sys

sys.path.append("incl/")
import ELPH_utils

def build_VAR_training_matrices(coef_runs, n_Var_steps):
    
    state = []
    target = []
    
    for r in range(len(coef_runs)):
        
        nCols = coef_runs[r].shape[1]-n_Var_steps
        nRows = coef_runs[r].shape[0]*n_Var_steps
        
        rVarMat = np.zeros((nRows,nCols))
        for j in range(nCols):
            VARcol = []
            for k in range(n_Var_steps):
                VARcol.append( coef_runs[r][:,j+k] )
            rVarMat[:,j] = np.concatenate(VARcol, axis=0)
        
        state.append(rVarMat)
        target.append(coef_runs[r][:,n_Var_steps:])

    state = np.concatenate(state, axis=1)
    target = np.concatenate(target, axis=1)
    
    return state,target


    
class SVDVAR:
    
    def __init__(self, runs, rdim = 1, n_VAR_steps = 1):
        self.runs = runs
        self.n_runs = len(runs)
        self.n_VAR_steps = n_VAR_steps
        self.rdim = rdim
        
    def __calc_reduced_coef_runs(self): 
        U,S = ELPH_utils.get_SVD_from_runs(self.runs)
        self.Uhat = U[:,:self.rdim]

        cmat = ELPH_utils.get_reduced_coef_matrix(self.runs, U, self.rdim)
    
        scmat, self.coef_mean, self.coef_std = ELPH_utils.standardize_data_matrix(cmat)

        self.coef_runs = ELPH_utils.get_coef_runs(scmat, self.n_runs)
    
    def __build_VAR_training_matrices(self):
        self.state, self.target = build_VAR_training_matrices(self.coef_runs, self.n_VAR_steps)
        
    def train(self, alpha=1e-6, rdim = 0, n_VAR_steps = 0, method='ridge'):
        
        if rdim != 0:
            self.rdim = rdim
        if n_VAR_steps != 0:
            self.n_VAR_steps = n_VAR_steps
        
        self.__calc_reduced_coef_runs()
        
        self.__build_VAR_training_matrices()
        
        if method == 'ridge':
            self.w = ELPH_utils.get_ridge_regression_weights(self.state, self.target, alpha)
        elif method == 'lstsq':
            self.w = np.asarray( np.linalg.lstsq(self.state.T, self.target.T, rcond = -1)[0] )
        else:
            print('unknown training method') 
            
        
    def predict_single_run(self, run):
        
        coef_run = self.Uhat.T @ run
        coef_run = (((coef_run.T - self.coef_mean)/self.coef_std)).T
        
        pred = np.zeros(coef_run.shape)

        for l in range(self.n_VAR_steps):
            pred[:,l] = coef_run[:,l]

        for j in range(self.n_VAR_steps,pred.shape[1]):
            VARpredList = []
            for l in range(self.n_VAR_steps):
                VARpredList.append( pred[:,j-self.n_VAR_steps+l] )
            pred[:,j] = self.w.T @ np.concatenate( VARpredList, axis=0 )
        
        pred = ELPH_utils.destandardize_data_matrix(pred, self.coef_mean, self.coef_std)
        pred = self.Uhat @ pred 
        
        return pred
    
    def get_error(self, run, pred=np.zeros(1), norm='fro'):
        if pred.size == 1:
            pred = self.predict_single_run(run)
        
        if norm == 'fro': #Frobenius norm
            err = np.linalg.norm(run-pred, ord='fro')
        elif norm == 'var2': # mean of dynamical variable wise 2-norms
            err = np.mean( np.sum( np.square(run-pred), axis = 1 ) )
        else:
            print('unknown norm')
        
        return err
    
    def print_status(self):
        print('rdim: ', self.rdim)
        print('n_VAR_steps: ', self.n_VAR_steps)
        print('state shape: ', self.state.shape)
        print('target shape: ', self.target.shape)
        print('weights shape: ', self.w.shape)
        
 
class VAR:
    
    def __init__(self, runs, n_VAR_steps = 1):
        self.runs = runs
        self.n_VAR_steps = n_VAR_steps
        
        self.state, self.target = build_VAR_training_matrices(self.runs, self.n_VAR_steps)
        
    def train(self, alpha=1e-6):
        self.w = np.linalg.inv(self.state @ self.state.T + alpha * np.identity(self.state.shape[0])) @ self.state @ self.target.T
        
    def predict_single_run(self, run):
        pred = np.zeros(run.shape)

        for l in range(self.n_VAR_steps):
            pred[:,l] = run[:,l]

        for j in range(self.n_VAR_steps,pred.shape[1]):
            VARpredList = []
            for l in range(self.n_VAR_steps):
                VARpredList.append( pred[:,j-self.n_VAR_steps+l] )
            pred[:,j] = self.w.T @ np.concatenate( VARpredList, axis=0 )
            
        return pred