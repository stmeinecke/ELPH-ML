import numpy as np
import matplotlib.pyplot as plt


#######################################
### get initial conditions and and calc runs
#######################################

import ELPH_dyn

def get_runs(kmax, n_kmax, inits, tmax = 5000.0, n_tmax = 1000):
  runs = []
  for k in range(len(inits)):
    print('run ', k+1, ' from ', len(inits))
    eldyn = ELPH_dyn.get_el_dynamics(inits[k], n_kmax = n_kmax, tmax = tmax, n_tmax = n_tmax)
    runs.append( eldyn )
  return runs


def get_runs_gaussian_init(kmax, n_kmax, gaussian_paras, tmax = 5000.0, n_tmax = 1000):

  runs = []

  for k in range(gaussian_paras.shape[0]):
    
    print('run ', k+1, ' from ', gaussian_paras.shape[0])
 
    p = gaussian_paras[k]
    init = ELPH_dyn.get_init_cond_gauss(kmax = kmax, n_kmax = n_kmax, max_pos = p[0], width = p[1], density = p[2])
    eldyn = ELPH_dyn.get_el_dynamics(init, n_kmax = n_kmax, tmax = tmax, n_tmax = n_tmax)

    runs.append( eldyn )

  return runs

def get_gaussian_inits(kmax, n_kmax, gaussian_paras):

  inits = []

  for k in range(gaussian_paras.shape[0]):
 
    p = gaussian_paras[k]
    inits.append( ELPH_dyn.get_init_cond_gauss(kmax = kmax, n_kmax = n_kmax, max_pos = p[0], width = p[1], density = p[2]) )

  return inits

#######################################
### KFold cross validation
#######################################

def get_KFold_runs(runs, folds=5):
    KFold_runs = np.array_split(runs, folds) #numpy returns list of ndarrays
    KFold_runs = [list(array) for array in KFold_runs] #covert ndarrays back to list such that KFold_runs is a list of lists of ndarrays (the individual runs)
    return KFold_runs
  
  
def get_KFold_CV_scores(model, runs, folds=5, seed=817, norms = ['std'], train_kwargs={}):
    
    #create shuffled copy of the runs
    rng = np.random.default_rng(seed=seed)
    sruns = runs.copy()
    rng.shuffle(sruns)
    
    #split runs into folds
    KFold_runs = get_KFold_runs(sruns, folds=folds)
    
    scores = [[] for n in range(len(norms))]  #of the individual folds - for each error norm in the norms list
    
    for k in range(folds):
        train_runs = KFold_runs.copy()
        test_runs = train_runs.pop(k) #test_runs = the kth fold, train_runs to remaining folds

        train_runs = [item for sublist in train_runs for item in sublist] #unpack the training folds into one flattened list

        #train the model on the training runs and get scores from the testing runs
        model.load_runs(train_runs) 
        model.train(**train_kwargs)
        
        #score the test runs for each error norm in the norms list
        for l,norm in enumerate(norms): 
            fold_mean_score, fold_all_scores = model.score_multiple_runs(test_runs, norm=norm)
            scores[l].append(fold_all_scores)
            
    for n in range(len(norms)):
        scores[n] = [item for sublist in scores[n] for item in sublist] #unpack the training folds into one flattened list
    
    return scores


def get_KFold_CV_scores_std_max(model, runs, folds=5, seed=817, score_kwargs = {}, train_kwargs={}):
    
    #create shuffled copy of the runs
    rng = np.random.default_rng(seed=seed)
    sruns = runs.copy()
    rng.shuffle(sruns)
    
    #split runs into folds
    KFold_runs = get_KFold_runs(sruns, folds=folds)
    
    mean_scores_std = [] #of the individual folds
    mean_scores_max = [] #of the individual folds
    
    all_scores_std = []
    all_scores_max = []
    for k in range(folds):
        train_runs = KFold_runs.copy()
        test_runs = train_runs.pop(k) #test_runs = the kth fold, train_runs to remaining folds

        train_runs = [item for sublist in train_runs for item in sublist] #unpack the training folds into one flattened list

        #train the model on the training runs and get scores from the testing runs
        model.load_runs(train_runs) 
        model.train(**train_kwargs)
        
        mean_std_score, scores_std = model.score_multiple_runs(test_runs, norm='std')
        mean_scores_std.append(mean_std_score)
        all_scores_std.append(scores_std)
        
        
        mean_max_score, scores_max = model.score_multiple_runs(test_runs, norm='max')
        mean_scores_max.append(mean_max_score)
        all_scores_max.append(scores_max)
    
    
    all_scores_std = [item for sublist in all_scores_std for item in sublist]
    all_scores_max = [item for sublist in all_scores_max for item in sublist]
    
    return mean_scores_std, mean_scores_max, all_scores_std, all_scores_max

#######################################
### save and load runs
#######################################

def save_runs(runs, filename='../runs'):
    np.savez(filename, runs)
    
def load_runs(filename='../runs.npz'):
    
    from os.path import exists

    if not exists(filename):
        print('runs file ot found')
        return None
    else:
        npz_runs = np.load(filename)
    #     print(npz_runs.files)
    #     print(type(npz_runs['arr_0']))
    #     print(npz_runs['arr_0'].shape)
        runs = np.split(npz_runs['arr_0'], npz_runs['arr_0'].shape[0], axis=0)

        for k in range(len(runs)):
            runs[k] = np.reshape(runs[k], runs[k].shape[1:])
    #     print(type(runs))
    #     print(type(runs[1]))
    #     print(runs[1].shape)
        return runs
    
    
def load_MG(filename='../MG.txt'):
    first_row = np.fromfile(filename, count=3, dtype=int, sep='\n')
    return np.loadtxt(filename,skiprows=1), first_row[0], first_row[1], first_row[2]

