from app import app
from app.conf.config import allow_list, port
from sanic.exceptions import NotFound
from sanic.response import text

@app.middleware('response')
async def prevent_xss(request, response):
    origin = request.headers.get('origin', None)
    if origin in allow_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = 'true'

@app.route('/')
async def index(request):
    return text('Hello')

@app.exception(NotFound)
async def ignore_404s(request, exception):
    return text('404 NotFound', 404)

