import numpy as np


class base_dim_reducer:
    def __init__(self):
        pass
    
    def train(self):
        raise NotImplementedError
        
    def reduce(self):
        raise NotImplementedError
        
    def expand(self):
        raise NotImplementedError
        
        
class SVD(base_dim_reducer):
    def __init__(self):
        pass
    
    def train(self, data_matrix):
        self.U,self.S = np.linalg.svd(data_matrix, full_matrices=False)[:2]
        
    def reduce(self, data_matrix, rdim):
        return self.U[:,:rdim].T @ data_matrix
    
    def expand(self, coef_matrix):
        dim = coef_matrix.shape[0]
        return self.U[:,:dim] @ coef_matrix 
      
      
class FFT(base_dim_reducer):
    def __init__(self, sorted=False):
        self.sorted = sorted
        pass
    
    def train(self, data_matrix):
        self.full_dim = data_matrix.shape[0]
        
        if self.sorted:
            FT = np.fft.rfft(data_matrix, axis=0)

            real_matrix = np.zeros((FT.shape[0]*2,FT.shape[1]))

            real_matrix[::2] = np.real(FT)
            real_matrix[1::2] = np.imag(FT)

            self.mean_coefs = np.mean(real_matrix, axis=1)

            self.sort_inds = np.flip(np.argsort(np.abs(self.mean_coefs)))
            self.unsort_inds = np.argsort(self.sort_inds)
        
        
    def reduce(self, data_matrix, rdim):
        
        FT = np.fft.rfft(data_matrix, axis=0)
  
        real_matrix = np.zeros((FT.shape[0]*2,FT.shape[1]))
        
        real_matrix[::2] = np.real(FT)
        real_matrix[1::2] = np.imag(FT)
        
        if self.sorted:
            return real_matrix[self.sort_inds][:rdim]
        else:
            return real_matrix[:rdim]
    
    def expand(self, coef_matrix):
        
        if self.sorted:
            real_matrix = np.zeros((2 * self.full_dim, coef_matrix.shape[1]))
            real_matrix[:coef_matrix.shape[0]] = coef_matrix
            real_matrix = real_matrix[self.unsort_inds]
          
            complex_matrix = real_matrix[::2] + 1.j*real_matrix[1::2]  
        else:
            complex_matrix = coef_matrix[::2] + 1.j*coef_matrix[1::2]
            
        iFT = np.fft.irfft(complex_matrix, n=self.full_dim, axis=0)
        
        return iFT


from scipy.special import eval_hermite
from scipy.optimize import minimize_scalar
class Hermite(base_dim_reducer):
    def __init__(self, sample_max = 1.0, sorted=False, optimize=False, orthogonalize=False, train_rdim=None):
        self.sample_max = sample_max
        self.sorted = sorted
        self.optimize = optimize
        self.orthogonalize = orthogonalize
        self.train_rdim = train_rdim
        pass
    
    def __GramSchmidt_Rows(self, A, eps=0.0):
        M = A.shape[0]
        N = A.shape[1]
        assert(M <= N)
        Q = np.zeros((M,N))
        for k in range(0,M):
            Q[k] = A[k]
            for j in range(k):
                Q[k] = Q[k] - np.dot(Q[j],A[k])*Q[j]

            if (Q[k] > eps).any():
                Q[k] = Q[k] / np.linalg.norm(Q[k])
            else:
                Q[k] = 0.0
        return Q
    
    def __nGramSchmidt_Rows(self, matrix, n=1, eps=0.0):
        o_matrix = matrix
        for k in range(n):
            o_matrix =  self.__GramSchmidt_Rows(o_matrix, eps)
        return o_matrix
    
    
    def train(self, data_matrix):
        self.full_dim = data_matrix.shape[0]
        
        if self.train_rdim == None:
            rdim = self.full_dim
        else:
            rdim = self.train_rdim
            
        self.x = np.linspace(0,self.sample_max,self.full_dim)
        
        def get_N(n): # normalization
            if n < 100:
                return 1./np.sqrt( np.sqrt(np.pi) * (2**n) * np.math.factorial(n))
            else:
                return np.exp( -0.5 * ( n*np.log(2.) + n*np.log(n) - n + 0.5*np.log(2.*np.pi*n) + 0.5*np.log(np.pi) ) )
        
        
        self.H_matrix = np.zeros((self.full_dim, self.full_dim))
        for k in range(self.full_dim):
            self.H_matrix[k]  = eval_hermite(k,self.x) * np.exp(-0.5*self.x**2) * get_N(k)
            
        
        if self.optimize == True:
            def loss(sample_max):
                x_test = np.linspace(0,sample_max,self.full_dim)
                for k in range(self.full_dim):
                    self.H_matrix[k] = eval_hermite(k,x_test) * np.exp(-0.5*x_test**2) * get_N(k)
                
                if self.orthogonalize:
                    self.H_matrix = self.__nGramSchmidt_Rows(self.H_matrix,10)
                
                if self.sorted:
                    train_coefs = self.H_matrix @ data_matrix 
                    self.mean_coefs = np.mean(train_coefs, axis=1)
                    self.sort_inds = np.flip(np.argsort(np.abs(self.mean_coefs)))
                    self.sorted_H_matrix = self.H_matrix[self.sort_inds]
                        
                apprx = np.linalg.pinv(self.H_matrix[:rdim]) @ (self.H_matrix[:rdim] @ data_matrix)
                
                #return np.linalg.norm(data_matrix-apprx, ord='fro')
                #return np.abs(np.ravel(data_matrix-apprx)).max()
                return np.std(np.ravel(data_matrix-apprx))
              
            res = minimize_scalar(loss, bounds=(0,40))
            self.sample_max = res.x
            #print(res.x)
            
            self.x = np.linspace(0,self.sample_max,self.full_dim)
            for k in range(self.full_dim):
                self.H_matrix[k]  = eval_hermite(k,self.x) * np.exp(-0.5*self.x**2) * get_N(k)
            
        if self.orthogonalize:
            self.H_matrix = self.__nGramSchmidt_Rows(self.H_matrix,10)
        
        if self.sorted:
            train_coefs = self.H_matrix @ data_matrix 
            self.mean_coefs = np.mean(train_coefs, axis=1)
            self.sort_inds = np.flip(np.argsort(np.abs(self.mean_coefs)))
            self.sorted_H_matrix = self.H_matrix[self.sort_inds]
        
        
    def reduce(self,data_matrix,rdim):
        if self.sorted:
            return self.sorted_H_matrix[:rdim] @ data_matrix
        else:
            return self.H_matrix[:rdim] @ data_matrix
        
    def expand(self, coef_matrix):
        dim = coef_matrix.shape[0]
        if self.sorted:
            return np.linalg.pinv(self.sorted_H_matrix[:dim]) @ coef_matrix
        else:
            return np.linalg.pinv(self.H_matrix[:dim]) @ coef_matrix
        
            
        
        
        
    
  
