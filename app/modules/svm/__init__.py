import logging

from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.under_sampling import NearMiss
from sklearn.pipeline import Pipeline
import numpy as np
import pickle

LOG = logging.getLogger(__name__)
X_sample = np.load('app/modules/svm/data.npy')
#y_sample = np.load('app/modules/svm/label.npy')

def build_svm_clf(ivectors, fbid):
    pipe_svm = Pipeline([('sc', StandardScaler()),
                        ('clf', SVC(kernel='linear', C=1.0, random_state=0,probability=True))])

    X = np.concatenate((np.array(ivectors), X_sample))
    y = np.concatenate(([True]*len(ivectors), [False]*len(X_sample)))

    nm2 = NearMiss(version=2)
    X_train, y_train = nm2.fit_resample(X, y)


    pipe_svm.fit(X_train, y_train)

    LOG.info('{} clf score: {}'.format(fbid, pipe_svm.score(X, y)))

    return pickle.dumps(pipe_svm)
