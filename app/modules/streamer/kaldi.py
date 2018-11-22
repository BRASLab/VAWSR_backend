import logging
import json

from app.conf.config import debug
from app.modules.streamer import WebsocketStream

from threading import Thread
from websocket import WebSocketApp
from urllib.parse import urlencode

LOG = logging.getLogger(__name__)


class KaldiStreamer:
    def __init__(self, url = 'ws://140.125.45.147:10388/client/ws/speech', rate = 44100):
        content_type = "audio/x-raw, layout=(string)interleaved, rate=(int){}, format=(string)S16LE, channels=(int)1".format(rate)
        url += '?' + urlencode([("content-type", content_type)])
        self.url = url
   
    def create_streamer(self, sid, stream):
        buff = WebsocketStream()
        ws = WebSocketApp(self.url,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                    )
        ws.buff = buff
        ws.stream = stream
        ws.sid = sid
        t = Thread(target=ws.run_forever)
        t.setDaemon(True)
        t.start()
        return buff


    @staticmethod 
    def on_open(ws):
        def send_data(ws, stream):
            try:
                for x in stream:
                    ws.send(x, opcode=0x2)
            except Exception as error:
                LOG.debug(error)
                ws.send('EOS')

        t = Thread(target=send_data, args=(ws, ws.stream))
        t.setDaemon(True)
        t.start()

    @staticmethod
    def on_message(ws, m):
        response = json.loads(str(m))
        if response['status'] == 0:
            if 'result' in response:
                trans = response['result']['hypotheses'][0]['transcript']
                ws.buff.write(trans)
                LOG.debug(trans)
        else:
            LOG.error("Received error from server (status {})".format(response['status']))
            if 'message' in response:
                LOG.error("Error message:", response['message'])

    @staticmethod
    def on_error(ws, error):
        LOG.error('{} kaldi websocket error'.format(ws.sid))
        LOG.error(error)

    @staticmethod
    def on_close(ws):
        LOG.info('{} kaldi websocket closed'.format(ws.sid))
        del ws.stream
        del ws.buff
        del ws.sid
