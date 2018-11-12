import logging
import sys

from sanic import Sanic
from sanic_session import Session, InMemorySessionInterface
import socketio

from app.conf.config import port, debug
from app.sockets import SpeechWebsocket, namespace 


LOG = logging.getLogger(__package__)

level = logging.DEBUG if debug else logging.INFO

LOG.setLevel(level)

sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(logging.Formatter(
    fmt="[%(asctime)-15s][%(levelname)s] %(name)s: %(message)s"
    ))

sh.setLevel(level)

LOG.addHandler(sh)

sio = socketio.AsyncServer(async_mode='sanic')
app = Sanic(__package__)

session = Session(app, interface=InMemorySessionInterface())

sio.attach(app)
sio.register_namespace(SpeechWebsocket(namespace))


def create_app():
    app.run(host='0.0.0.0', port=port, debug=debug)
