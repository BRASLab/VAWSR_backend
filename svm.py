from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from modules.db.mongo import Users
import numpy as np
import pickle

ivectors = np.array([]).reshape(0,400)
labels = []


for user in Users.objects:
    if user.hasivector:
        ivector = pickle.load(user.ivector)
        ivectors = np.concatente([ivectors, ivector])
        labels = np.concatenate([labels, [ user.fbid ]*len(ivector)])


svm = SVC(kernel='linear', C=1.0, random_state=0,probability=True)

sc = StandardScaler()
X_train_std = sc.fit_transform(ivectors)

print(np.asarray(np.unique(y_train, return_counts=True)).T)
print('speaker {}'.format(len(np.unique(y))))

svm.fit(X_train_std, labels)
print('fit done')
#y_pred = svm.predict(X_test_std[:2])
#print(svm.predict(X_test_std[:2]))
#print(accuracy_score(y_test, y_pred))

