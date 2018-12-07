import logging

from app.modules.db.mongo import Users
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from bson.binary import Binary
import numpy as np
import pickle

LOG = logging.getLogger(__name__)

X_sample = np.load('app/modules/svm/data.npy')
y_sample = np.load('app/modules/svm/label.npy')

def combine_ivector(_ivectors):
    _new = []
    if isinstance(_ivectors, np.ndarray):
        _new = _ivectors.tolist()
    else:
        _new = _ivectors[:]

    length = len(_ivectors)
    if length >=2:
        for x in range(length-1):
            _new.append(np.mean((_ivectors[x], _ivectors[x+1]), axis=0))
    if length >=3:
        for x in range(length-2):
            _new.append(np.mean((_ivectors[x], _ivectors[x+1], _ivectors[x+2]), axis=0))
    if length >=4:
        for x in range(length-3):
            _new.append(np.mean((_ivectors[x], _ivectors[x+1], _ivectors[x+2], _ivectors[x+3]), axis=0))
    
    return np.array(_new)

def build_svm_clf(ivectors, user):
    try:
        pipe_svm = Pipeline([('sc', StandardScaler()),
                        ('clf', SVC(kernel='linear', C=1.0, probability=True))])

        n_ivectors = combine_ivector(ivectors)

        X = np.concatenate((n_ivectors, X_sample))
        y = np.concatenate(([True]*len(n_ivectors), [False]*len(X_sample)))

        pipe_svm.fit(X, y)

        LOG.info('{} clf test score: {}'.format(user.name, pipe_svm.score(X, y)))
        user.clf = Binary(pickle.dumps(pipe_svm))
        user.ivectors = Binary(pickle.dumps(np.array(ivectors), protocol=2))
        user.hasivector = True
        user.processing = False
        user.save()
        return True

    except Exception as err:
        user.hasivector = False
        user.processing = False
        user.save()
        LOG.error(err)
