import numpy
import h5py
import h5py._hl
from sklearn.svm import SVC

class SVCImpex(SVC):
    params_to_save = ['_sparse', 'shape_fit_', 'support_vectors_',
                          'n_support_', 'dual_coef_', '_intercept_',
                          '_label', 'probA_', 'probB_', '_gamma', 
                          'classes_', 'support_', 'gamma', 'kernel']
                          
    def save(self, file_name):
        if isinstance(file_name, (str,)):
            with h5py.File(file_name, 'w') as hf:
                for param in self.params_to_save:
                    data = getattr(self, param)
                    hf.create_dataset(param, data=data)
        elif isinstance(file_name, (h5py._hl.group.Group, h5py._hl.files.File)):
            for param in self.params_to_save:
                data = getattr(self, param)
                file_name.create_dataset(param, data=data)
        else:
            raise IOError('SVCImpex.save(): file_name is not a string nor a h5py group handle...')
     
    @classmethod
    def load(cls, file_name):
        new_svm = cls()
        if isinstance(file_name, (str,)):
            with h5py.File(file_name, 'r') as hf:
                for param in cls.params_to_save:
                    data = hf[param].value
                    setattr(new_svm, param, data)
        elif isinstance(file_name, (h5py._hl.group.Group, h5py._hl.files.File)):
            for param in cls.params_to_save:
                data = file_name[param].value
                setattr(new_svm, param, data)
        else:
            raise IOError('SVCImpex.load(): file_name is not a string nor a h5py group handle...')
         
        return new_svm
            
class TestSVCImpex(object):
    def __init__(self):
        X = numpy.random.rand(300,3)
        X[:100,:] *= 2
        y = (numpy.random.rand(300) > 0.5).astype('uint8') + 1
        s = SVCImpex(gamma=0.0001, kernel='rbf', probability=True, C=100)
        s.fit(X,y)
        s.save('svc_save_h5')
        t1 = SVCImpex.load('svc_save_h5')
        assert numpy.all(s.predict(X) == t1.predict(X))
        
        with h5py.File('svc_save_h5', 'r') as hf:
            grp = hf['/']
            t1 = SVCImpex.load(grp)
            assert numpy.all(s.predict(X) == t1.predict(X))

TestSVCImpex()        
    
