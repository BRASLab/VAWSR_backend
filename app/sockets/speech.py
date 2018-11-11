import logging
import asyncio

from app import sio
from app.modules.db.mongo import Users
from app.modules.streamer import GoogleStreamer, WebsocketStream
from app.utils import thread_new_event_loop

from six.moves import queue
import socketio


LOG = logging.getLogger(__name__)

namespace = '/ws'

class SpeechWebsocket(socketio.AsyncNamespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = {}

    async def on_connect(self, sid, environ):
        try:
            request = environ['sanic.request']
            user = Users.objects.get(fbid=request['session']['fbid'])
            if not user or not user.hasivector:
                self.disconnect(sid)
                return

            self.streamer[sid] = {
                    'google': GoogleStreamer()
                    }

            LOG.info('User: {} connected to server'.format(user.name))
        
        except Exception as err:
            self.disconnect(sid)
            LOG.debug(err)

    async def on_disconnect(self, sid):
        if self.streamer.get(sid):
            self.on_end_stream(sid, '')
            del self.streamer[sid]

    async def on_start_stream(self, sid, data):
        stream = WebsocketStream()
        buff = queue.Queue()

        self.streamer[sid]['stream'] = stream
        self.streamer[sid]['buff'] = buff

    async def on_stop_stream(self, sid, data):
        if self.streamer.get(sid) and self.streamer[sid].get('responses'):
            self.streamer[sid]['stream'].end()
            self.streamer[sid]['responses'].cancel()
            del self.streamer[sid]['stream']
            del self.streamer[sid]['responses']

    async def on_binary_data(self, sid, data):
        if not self.streamer.get(sid):
            self.on_start_stream(sid, data)


        if not self.streamer[sid].get('responses'):
            google = self.streamer[sid]['google']
            stream = self.streamer[sid]['stream']
            responses = google.start_recognition_stream(stream.generator())
            self.streamer[sid]['responses'] = responses
            loop = thread_new_event_loop()
            asyncio.ensure_future(self.handle_google_response(sid, responses), loop=loop)

        self.streamer['stream'].write(data)
        self.streamer['buff'].put(data)
        

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

                await self.emit('google_speech_data', data, room=sid)
        except Exception as err:
            LOG.debug(err)

sio.register_namespace(SpeechWebsocket(namespace))
