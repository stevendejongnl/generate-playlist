import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse

from playlist_generator.config import settings
from playlist_generator.database import engine, Base
from playlist_generator.routers import auth, pages, base_list, blacklist, targets, generation, cover_image, spotify_browse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_pkg_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_pkg_dir)

templates = Jinja2Templates(directory=os.path.join(_root_dir, "templates"))


def _get_version() -> str:
    """Read the app version from pyproject.toml (set by semantic-release)."""
    try:
        import importlib.metadata

        return importlib.metadata.version("generate-playlist")
    except Exception:
        return "dev"


def _format_timestamp(value: float) -> str:
    """Convert a unix timestamp to a human-readable string."""
    dt = datetime.fromtimestamp(value, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M")


APP_VERSION = _get_version()
templates.env.filters["timestamp"] = _format_timestamp
templates.env.globals["app_version"] = APP_VERSION
pages.set_templates(templates)
base_list.set_templates(templates)
blacklist.set_templates(templates)
targets.set_templates(templates)
generation.set_templates(templates)
cover_image.set_templates(templates)
spotify_browse.set_templates(templates)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (for dev/docker; production uses alembic)
    os.makedirs("data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready. Startup complete.")
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(401)
async def auth_redirect(request: Request, exc: Exception) -> HTMLResponse:
    """Redirect unauthenticated users to the landing page."""
    from starlette.responses import RedirectResponse

    return RedirectResponse(url="/", status_code=303)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="playlist_session",
    max_age=31536000,  # 1 year
)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(_root_dir, "static")),
    name="static",
)

app.include_router(auth.router)
app.include_router(base_list.router)
app.include_router(blacklist.router)
app.include_router(targets.router)
app.include_router(generation.router)
app.include_router(cover_image.router)
app.include_router(spotify_browse.router)
app.include_router(pages.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("playlist_generator.main:app", host="0.0.0.0", port=5000, reload=True)
