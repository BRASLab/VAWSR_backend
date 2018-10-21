from sanic import Sanic
from sanic.response import json, text
from sanic.exceptions import abort
from sanic_session import Session, InMemorySessionInterface
from modules.db.mongo import Users
from utils import login_required
import requests
from modules.ivector import ivector_pipeline
from io import BytesIO

from bson.binary import Binary
import pickle

app = Sanic()

session = Session(app, interface=InMemorySessionInterface())

allow_list = ["http://localhost:3000", "https://sean2525.github.io"]

@app.middleware('response')
async def prevent_xss(request, response):
    if request.headers['origin'] in allow_list:
        response.headers["Access-Control-Allow-Origin"] = request.headers['origin']
        response.headers["Access-Control-Allow-Credentials"] = 'true'

@app.route('/')
async def index(request):
    return text('Hello')

@app.route('/auth')
async def auth(request):
    if not request['session'].get('fbid'):
        return json({'status': 'not_authorized'}, 401)
    user = Users.objects(fbid=int(request['session']['fbid']))
    if user:
        user = user[0]
    else:
        return json({'status': 'not_authorized'}, 401)

    return json({'name':user.name, 'fbid':user.fbid, 'email': user.email , 'hasivector': user.hasivector })

@app.route('/sentences.json')
@login_required()
async def sentences(request):
    res = requests.get('http://more.handlino.com/sentences.json?n=3')
    return json(res.json())

@app.route('/logout')
@login_required()
async def logout(request):
    del request['session']['fbid']
    return json({'success':True})

@app.route('/login', methods=['POST',])
async def login(request):
    data = request.json
    fb = requests.get('https://graph.facebook.com/me?access_token={}'.format(data.get('token'))).json()
    if str(fb['id']) != str(data.get('fbid')):
        abort(401)
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


@app.route('/registerspeaker', methods=['POST',])
@login_required()
async def registerspeaker(request):
    try:
        user = Users.objects.get(fbid=request['session']['fbid'])
        ivectors = []
        for x in request.files.values():
            b = BytesIO(x[0].body)
            ivectors.append(ivector_pipeline(b, user.name + ' ' + x[0].name))
        user.ivector = Binary(pickle.dumps(ivectors, protocol=2))
        user.hasivector = True
        user.save()
        return json({'status': True})
    except Exception as err:
        print(err)
        
    
    return json({'status': 'error'}, 403)

@app.route('/sr', methods=['POST',])
@login_required()
async def sr(request):
    try:
        user = Users.objects.get(fbid=request['session']['fbid'])
        wav = BytesIO(request.files.get('file', None).body)
        ivector = ivector_pipeline(wav, user.name)
        return json({'status': True})
    except Exception as err:
        print(err)
    
    return json({'status': 'error'}, 403)

def create_app():
    app.run(host='0.0.0.0', port=8000)

if __name__ == '__main__':
    create_app()
