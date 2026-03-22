import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from playlist_generator.config import Config
from playlist_generator.routers import auth, actions

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Resolve paths relative to the package root
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_pkg_dir)

templates = Jinja2Templates(directory=os.path.join(_root_dir, 'templates'))

# Inject templates into the actions router so it can render responses
actions.set_templates(templates)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_dir = '.cache'
    cache_file = os.path.join(cache_dir, 'token_cache')
    os.makedirs(cache_dir, exist_ok=True)
    if not os.path.exists(cache_file):
        with open(cache_file, 'w') as f:
            f.write('')
    try:
        os.chmod(cache_dir, 0o777)
        os.chmod(cache_file, 0o666)
    except Exception as e:
        logger.warning(f"Could not set cache permissions: {e}")
    logger.info("Startup complete.")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY, session_cookie='playlist_session', max_age=31536000)
app.mount('/static', StaticFiles(directory=os.path.join(_root_dir, 'static')), name='static')

app.include_router(auth.router)
app.include_router(actions.router)


@app.get('/')
def index(request: Request) -> Response:
    authenticated = bool(request.session.get('token_info'))
    logger.info('Rendering index page. Authenticated: %s', authenticated)
    if not authenticated:
        url_list = [{"href": "/authenticate", "text": "Authenticate"}]
    else:
        url_list = [
            {"href": "/actions/generate", "text": "Build playlist"},
            {"href": "/actions/image", "text": "Create new image"},
            {"href": "/actions/playlists", "text": "Manage playlists"},
            {"href": "/actions/blacklist", "text": "Select tracks for blacklist"},
            {"href": "/sign_out", "text": "Sign out"},
        ]
    return templates.TemplateResponse(request, 'pages/index.html', {'url_list': url_list})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('playlist_generator.main:app', host='0.0.0.0', port=5000, reload=True)
