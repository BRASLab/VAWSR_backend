from functools import wraps
from modules.db.mongo import Users
from sanic.response import json
from scipy.spatial.distance import cosine
import numpy as np

def login_required():
    def decorator(f):
        @wraps(f)
        async def auth_function(request, *args, **kwargs):
            if not request['session'].get('fbid'):
                return json({'status': 'not_authorized'}, 401)
            
            if Users.objects(fbid=request['session']['fbid']):
                return await f(request, *args, **kwargs)
            
            return json({'status': 'not_authorized'}, 401)
        return auth_function
    return decorator

def cosine_prob(ivector, ivector2):
   mean1, mean2 = np.mean(ivector), np.mean(ivector2)
   ivector -= mean1
   ivector2 -= mean2
   return cosine(ivector, ivector2)
