import requests

from app import app
from app.utils.sanic import login_required
from sanic.response import json


@app.route('/sentences.json')
@login_required()
async def sentences(request):
    res = requests.get('http://more.handlino.com/sentences.json?n=3')
    return json(res.json())
