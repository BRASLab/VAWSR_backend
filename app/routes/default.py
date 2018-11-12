from app import app
from app.conf.config import allow_list, port
from sanic.exceptions import NotFound
from sanic.response import text
import logging

LOG = logging.getLogger(__name__)

@app.middleware('response')
async def prevent_xss(request, response):
    try:
        origin = request.headers.get('origin', None)
        if origin in allow_list:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = 'true'
    except Exception as err:
        LOG.debug(err)

@app.route('/')
async def index(request):
    return text('Hello')

@app.exception(NotFound)
async def ignore_404s(request, exception):
    return text('404 NotFound', 404)

