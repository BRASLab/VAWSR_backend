import logging
import requests

from app import sio
from app.modules.db.mongo import Users
from app.modules.streamer import GoogleStreamer, KaldiStreamer, WebsocketStream
from app.modules.ivector import ivector_pipeline
from app.utils import thread_run_until_complete, byte2wav
from app.conf.config import google_disable, kaldi_disable, debug

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
        self.kaldi = KaldiStreamer(rate=44100)

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

            clf = pickle.loads(user.clf)
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
        g_stream = WebsocketStream()
        k_stream = WebsocketStream()
        buff = BytesIO()

        self.streamer[sid]['g_stream'] = g_stream
        self.streamer[sid]['k_stream'] = k_stream
        self.streamer[sid]['buff'] = buff
        LOG.info('{} start stream'.format(sid))

    async def on_stop_stream(self, sid, data):
        LOG.info('{} stop stream'.format(sid))
        if self.streamer[sid].get('g_stream') and self.streamer[sid].get('k_stream'):
            self.streamer[sid]['g_stream'].end()
            self.streamer[sid]['k_stream'].end()
            del self.streamer[sid]['g_stream']
            del self.streamer[sid]['k_stream']

        if self.streamer[sid].get('g_responses') or self.streamer[sid].get('k_responses'):
            google = ''
            kaldi = ''
            proba = 0
            result = {
                    'text': 'Not authorized',
                    'url': ''
                    }

            if not google_disable:
                self.streamer[sid]['g_responses'].cancel()
                del self.streamer[sid]['g_responses']
                google = self.streamer[sid].get('google', '')
                if google:
                    LOG.info('google {} has no speechData'.format(sid))
                    del self.streamer[sid]['google']


            if not kaldi_disable:
                self.streamer[sid]['k_responses'].cancel()
                del self.streamer[sid]['k_responses']
                kaldi = self.streamer[sid].get('kaldi', '')
                if kaldi:
                    del self.streamer[sid]['kaldi']
                else:
                    LOG.info('kaldi {} has no speechData'.format(sid))
                    del self.streamer[sid]['buff']

            clf = self.streamer[sid].get('clf')
            if clf:
                try:
                    wav = byte2wav(self.streamer[sid]['buff'], 44100)
                    del self.streamer[sid]['buff']
                    if debug:
                        with open('test.wav', 'wb') as f:
                            f.write(wav.getvalue())

                    ivector = ivector_pipeline(wav , sid)
                    proba = clf.predict_proba(ivector.reshape(1, -1))
                    proba = float('{0:.3f}'.format(proba[0][1]))

                    LOG.debug(proba)
                    if proba >= 0.5 and google:
                        result = requests.get('https://vawsr.mino.tw/nlp/get?speech={}'.format(google)).json()

                except Exception as err:
                    LOG.debug(err)

            data = {
                    'google': google,
                    'kaldi': kaldi,
                    'proba': proba,
                    'result': result
                    }

            await self.emit('stop_stream', data, room=sid)

    @sanic_auth
    async def on_binary_data(self, sid, data):
        if not self.streamer[sid].get('g_stream'):
            await self.on_start_stream(sid, data)

            if not google_disable:
                g_stream = self.streamer[sid]['g_stream']
                g_responses = self.google.start_recognition_stream(g_stream.generator())
                self.streamer[sid]['g_responses'] = g_responses
                thread_run_until_complete(self.handle_google_response(sid, g_responses))

            if not kaldi_disable:
                k_stream = self.streamer[sid]['k_stream']
                k_responses = self.kaldi.create_streamer(sid, k_stream.generator())
                self.streamer[sid]['k_responses'] = k_responses
                thread_run_until_complete(self.handle_kaldi_response(sid, k_responses.generator()))
            

            LOG.info('{} start recognition'.format(sid))

        self.streamer[sid]['g_stream'].write(data)
        self.streamer[sid]['k_stream'].write(data)
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
    
    async def handle_kaldi_response(self, sid, responses):
        try:
            for res in responses:
                if res is not None:
                    data = {'transcript': res }
                    self.streamer[sid]['kaldi'] = res
                    LOG.debug(res)
                    await self.emit('kaldi_speech_data', data, room=sid)
        except Exception as err:
            LOG.debug(err)
        
sio.register_namespace(SpeechWebsocket(namespace))
