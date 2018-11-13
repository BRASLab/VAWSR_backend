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


LOG = logging.getLogger(__name__)


@app.route('/registerspeaker', methods=['POST',])
@login_required()
async def registerspeaker(request):
    try:
        user = Users.objects.get(fbid=request['session']['fbid'])
        ivectors = []
        for x in request.files.values():
            b = BytesIO(x[0].body)
            ivectors.append(ivector_pipeline(b, user.name + ' ' + x[0].name))

        clf = build_svm_clf(ivectors, user.fbid)
        user.ivector = Binary(clf)
        user.hasivector = True
        user.save()
        return json({'status': True})
    except Exception as err:
        LOG.error(err)
        
    
    return json({'status': 'error'}, 403)


