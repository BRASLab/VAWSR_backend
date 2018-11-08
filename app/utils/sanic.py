from functools import wraps
from app.modules.db.mongo import Users
from sanic.response import json

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
