import logging

from bson.binary import Binary
from sanic.response import json
from io import BytesIO
import pickle

from app import app
from app.modules.svm import build_svm_clf
from app.modules.ivector import ivector_pipeline
from app.modules.db.mongo import Users
from app.utils.sanic import login_required
from threading import Thread
import numpy as np


LOG = logging.getLogger(__name__)

@app.route('/registerspeaker', methods=['POST',])
@login_required()
async def registerspeaker(request):
    try:
        user = Users.objects.get(fbid=request['session']['fbid'])
        if user.processing:
            return json({'message': '您的個人模型正在建立中請稍後' } )

        ivectors = []
        if len(request.files) != 10:
            return json({'message': '註冊語句未滿10句 你似乎使用非正當手段註冊'}, 400)

        for x in request.files.values():
            b = BytesIO(x[0].body)
            ivectors.append(ivector_pipeline(b, user.name + ' ' + x[0].name))

        if np.array(ivectors).shape != (10, 400):
            return json({'message': '特徵擷取失敗，請確認是否每句都有語音'}, 400)

        user.hasivector = False
        user.processing = True
        user.save()
        t = Thread(target=build_svm_clf, args=(ivectors, user))
        t.setDaemon(True)
        t.start()
        return json({'message': '正在訓練您的個人模型中請稍後，這可能耗時1~2分鐘，請記得刷新以確認是否建立完成'})

    except Exception as err:
        LOG.error(err)
        
    
    return json({'message': '註冊語者失敗請重新傳送一次，請確認是否每句都有語音' }, 400)

@app.route('/testwav', methods=['POST',])
async def testwav(request):
    with open('test1.wav', 'wb') as f:
        f.write(request.files['test1'][0].body)

    return json({'status': True})
