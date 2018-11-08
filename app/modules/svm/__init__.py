from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.under_sampling import NearMiss
from sklearn.pipeline import Pipeline
import numpy as np
import pickle

X_sample = np.load('app/modules/svm/data.npy')
y_sample = np.load('app/modules/svm/label.npy')

def build_svm_clf(ivectors, fbid):
    pipe_svm = Pipeline([('sc', StandardScaler()),
                        ('clf', SVC(kernel='linear', C=1.0, random_state=0,probability=True))])

    X = np.concatenate((np.array(ivectors), X_sample))
    y = np.concatenate(([fbid]*len(ivectors), y_sample))

    y = np.array([ True if x == str(fbid) else False for x in y])
    
    nm2 = NearMiss(version=2)
    X, y = nm2.fit_resample(X, y)


    pipe_svm.fit(X, y)

    print(pipe_svm.score(X, y))

    return pickle.dumps(pipe_svm)
