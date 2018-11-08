import logging
import sys

from sanic import Sanic
from app.conf.config import port
from sanic_session import Session, InMemorySessionInterface


LOG = logging.getLogger(__package__)
LOG.setLevel(logging.INFO)

sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(logging.Formatter(
    fmt="[%(asctime)-15s][%(levelname)s] %(name)s: %(message)s"
    ))

sh.setLevel(logging.INFO)

LOG.addHandler(sh)

app = Sanic(__package__)
session = Session(app, interface=InMemorySessionInterface())

def create_app():
    app.run(host='0.0.0.0', port=port)
