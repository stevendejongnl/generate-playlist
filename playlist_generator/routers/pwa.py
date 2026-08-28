import os

from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter(tags=["pwa"])

_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_static_dir = os.path.join(_root_dir, "static")

NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}


@router.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(
        os.path.join(_static_dir, "sw.js"),
        media_type="application/javascript",
        headers=NO_CACHE_HEADERS,
    )


@router.get("/manifest.webmanifest")
async def manifest() -> FileResponse:
    return FileResponse(
        os.path.join(_static_dir, "manifest.webmanifest"),
        media_type="application/manifest+json",
        headers=NO_CACHE_HEADERS,
    )
