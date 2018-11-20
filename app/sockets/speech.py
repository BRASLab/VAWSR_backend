import logging
import requests

from app import sio
from app.modules.db.mongo import Users
from app.modules.streamer import GoogleStreamer, WebsocketStream
from app.modules.ivector import ivector_pipeline
from app.utils import thread_run_until_complete, byte2wav

from io import BytesIO
from functools import wraps
import pickle
import socketio


LOG = logging.getLogger(__name__)

namespace = '/ws'

class SpeechWebsocket(socketio.AsyncNamespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = {}
        self.google = GoogleStreamer(rate=44100)

    def sanic_auth(func):
        @wraps(func)
        async def wrapper(self, sid, data):
            if not self.streamer[sid]['auth']:
                return await self.disconnect(sid)
            else:
                return await func(self, sid, data)

        return wrapper

    async def on_connect(self, sid, environ):
        try:
            request = environ['sanic.request']
            user = Users.objects.get(fbid=request['session']['fbid'])
            if not user or not user.hasivector:
                raise ValueError('user.hasivector must be true')

            clf = pickle.loads(user.ivector)
            self.streamer[sid] = {'auth': True, 'clf': clf }

            LOG.info('User: {} connected to server'.format(user.name))
        
        except Exception as err:
            self.streamer[sid] = {'auth': False}
            LOG.debug(err)

    async def on_disconnect(self, sid):
        await self.on_stop_stream(sid, '')
        del self.streamer[sid]
        LOG.info('client disconnect')


    @sanic_auth
    async def on_start_stream(self, sid, data):
        stream = WebsocketStream()
        buff = BytesIO()

        self.streamer[sid]['stream'] = stream
        self.streamer[sid]['buff'] = buff
        LOG.info('{} start stream'.format(sid))

    async def on_stop_stream(self, sid, data):
        LOG.info('{} stop stream'.format(sid))
        if self.streamer[sid].get('stream'):
            self.streamer[sid]['stream'].end()
            del self.streamer[sid]['stream']

        if self.streamer[sid].get('responses'):
            self.streamer[sid]['responses'].cancel()
            del self.streamer[sid]['responses']
            proba = 0
            result = {
                    'text': '',
                    'url': ''
                    }

            if self.streamer[sid].get('clf'):
                try:
                    wav = byte2wav(self.streamer[sid]['buff'], 44100)
                    del self.streamer[sid]['buff']
                    ivector = ivector_pipeline(wav , sid)
                    clf = self.streamer[sid]['clf']
                    if clf.predict(ivector.reshape(1, -1))[0]:
                        result = requests.get('http://140.125.45.147:8080/get?speech={}'.format(self.streamer[sid]['google'])).json()

                    proba = clf.predict_proba(ivector.reshape(1, -1))
                    LOG.debug(proba)
                    proba = proba[0][1]

                except Exception as err:
                    LOG.error(err)

            data = {
                    'proba': proba,
                    'result': result
                    }

            await self.emit('stop_stream', data, room=sid)
            return

        await self.emit('stop_stream', { 'proba': 0, 'result': '' }, room=sid)

    @sanic_auth
    async def on_binary_data(self, sid, data):
        if not self.streamer[sid].get('stream'):
            await self.on_start_stream(sid, data)

        if not self.streamer[sid].get('responses'):
            stream = self.streamer[sid]['stream']
            responses = self.google.start_recognition_stream(stream.generator())
            self.streamer[sid]['responses'] = responses
            thread_run_until_complete(self.handle_google_response(sid, responses))
            LOG.info('{} start google recognition'.format(sid))

        self.streamer[sid]['stream'].write(data)
        self.streamer[sid]['buff'].write(data)
        

    async def handle_google_response(self, sid, responses):
        try:
            for res in responses:
                if not res.results:
                    continue

                result = res.results[0]

                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript

                data = {'transcript': transcript , 'is_final': False }
                if result.is_final:
                    data['is_final'] = True

                self.streamer[sid]['google'] = transcript
                LOG.debug(data)
                await self.emit('google_speech_data', data, room=sid)
        except Exception as err:
            LOG.debug(err)

sio.register_namespace(SpeechWebsocket(namespace))
