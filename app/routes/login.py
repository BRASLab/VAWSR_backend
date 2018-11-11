import logging
import requests

from app import app
from sanic.response import json
from app.modules.db.mongo import Users
from app.utils.sanic import login_required

@app.route('/auth')
async def auth(request):
    if not request['session'].get('fbid', None):
        return json({'status': 'not_authorized'}, 401)

    user = Users.objects(fbid=int(request['session']['fbid']))

    if user:
        user = user[0]
    else:
        return json({'status': 'not_authorized'}, 401)

    return json({'name':user.name, 'fbid':user.fbid, 'email': user.email , 'hasivector': user.hasivector })


@app.route('/login', methods=['POST', ])
async def login(request):
    data = request.json
    try:
        fb = requests.get('https://graph.facebook.com/me?access_token={}'.format(data.get('token'))).json()
        if str(fb['id']) != str(data.get('fbid')):
            return json({'status': False}, 401)
    except Exception as err:
        return json({'status': False}, 401)

    user = Users.objects(fbid=data.get('fbid'))

    if not user:
        user = Users(fbid=data.get('fbid'))
    else:
        user = user[0]

    user.email = data.get('email', user.email)
    user.name = data.get('name', user.name)
    user.token = data.get('token', user.token)
    user.signed = data.get('signed', user.signed)
    user.save()
    request['session']['fbid'] = user.fbid

    return json({'name':user.name, 'fbid':user.fbid, 'email': user.email, 'hasivector':user.hasivector })


@app.route('/logout')
@login_required()
async def logout(request):
    del request['session']['fbid']
    return json({'success': True})
