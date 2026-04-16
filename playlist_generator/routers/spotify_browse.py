"""Spotify browse API — returns HTML partials for HTMX-powered browsing."""
import asyncio
import logging
from typing import Annotated

import spotipy
from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from playlist_generator.dependencies import get_current_user, get_spotify
from playlist_generator.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spotify", tags=["spotify-browse"])

templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


@router.get("/my-playlists")
async def my_playlists(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    action: str = "add-source",
    offset: int = 0,
    limit: int = 20,
) -> Response:
    """Browse the user's own Spotify playlists."""
    assert templates is not None
    results = await asyncio.to_thread(
        spotify.current_user_playlists, limit=limit, offset=offset
    )
    playlists = [
        {
            "id": p["id"],
            "name": p["name"],
            "track_count": p["tracks"]["total"],
            "image_url": p["images"][0]["url"] if p.get("images") else None,
            "owner": p.get("owner", {}).get("display_name", ""),
        }
        for p in results.get("items", [])
    ]
    has_more = results.get("next") is not None
    return templates.TemplateResponse(
        request,
        "partials/browse_playlists.html",
        {
            "playlists": playlists,
            "action": action,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
        },
    )


@router.get("/my-tracks")
async def my_tracks(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    source: str = "liked",
    action: str = "add-source",
    offset: int = 0,
    limit: int = 20,
) -> Response:
    """Browse the user's liked or top tracks."""
    assert templates is not None
    if source == "top":
        results = await asyncio.to_thread(
            spotify.current_user_top_tracks, limit=limit, offset=offset
        )
        items = results.get("items", [])
    else:
        results = await asyncio.to_thread(
            spotify.current_user_saved_tracks, limit=limit, offset=offset
        )
        items = [item["track"] for item in results.get("items", []) if item.get("track")]

    tracks = [
        {
            "id": t["id"],
            "name": t["name"],
            "artist": ", ".join(a["name"] for a in t.get("artists", [])),
            "duration_ms": t.get("duration_ms", 0),
            "image_url": t.get("album", {}).get("images", [{}])[-1].get("url") if t.get("album", {}).get("images") else None,
        }
        for t in items
        if t and t.get("id")
    ]
    has_more = results.get("next") is not None
    return templates.TemplateResponse(
        request,
        "partials/browse_tracks.html",
        {
            "tracks": tracks,
            "action": action,
            "source": source,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
        },
    )


@router.get("/playlist-tracks/{playlist_id}")
async def playlist_tracks(
    request: Request,
    playlist_id: str,
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    action: str = "add-blacklist",
    offset: int = 0,
    limit: int = 20,
) -> Response:
    """Browse tracks inside a specific playlist (for blacklisting)."""
    assert templates is not None
    results = await asyncio.to_thread(
        spotify.playlist_tracks,
        playlist_id,
        fields="items(track(id,name,artists,duration_ms,album(images))),next",
        limit=limit,
        offset=offset,
    )
    tracks = [
        {
            "id": t["id"],
            "name": t["name"],
            "artist": ", ".join(a["name"] for a in t.get("artists", [])),
            "duration_ms": t.get("duration_ms", 0),
            "image_url": t.get("album", {}).get("images", [{}])[-1].get("url") if t.get("album", {}).get("images") else None,
        }
        for item in results.get("items", [])
        if (t := item.get("track")) and t.get("id")
    ]
    has_more = results.get("next") is not None
    return templates.TemplateResponse(
        request,
        "partials/browse_tracks.html",
        {
            "tracks": tracks,
            "action": action,
            "source": f"playlist:{playlist_id}",
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
        },
    )


@router.get("/search")
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    user: Annotated[User, Depends(get_current_user)],
    spotify: Annotated[spotipy.Spotify, Depends(get_spotify)],
    type: str = "track",
    action: str = "add-blacklist",
    limit: int = 10,
) -> Response:
    """Search Spotify for tracks or playlists."""
    assert templates is not None
    results = await asyncio.to_thread(
        spotify.search, q=q, type=type, limit=limit
    )

    if type == "track":
        items = results.get("tracks", {}).get("items", [])
        tracks = [
            {
                "id": t["id"],
                "name": t["name"],
                "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                "duration_ms": t.get("duration_ms", 0),
                "image_url": t.get("album", {}).get("images", [{}])[-1].get("url") if t.get("album", {}).get("images") else None,
            }
            for t in items
            if t.get("id")
        ]
        return templates.TemplateResponse(
            request,
            "partials/browse_tracks.html",
            {"tracks": tracks, "action": action, "source": "search", "offset": 0, "limit": limit, "has_more": False},
        )
    else:
        items = results.get("playlists", {}).get("items", [])
        playlists = [
            {
                "id": p["id"],
                "name": p["name"],
                "track_count": p.get("tracks", {}).get("total", 0),
                "image_url": p["images"][0]["url"] if p.get("images") else None,
                "owner": p.get("owner", {}).get("display_name", ""),
            }
            for p in items
            if p and p.get("id")
        ]
        return templates.TemplateResponse(
            request,
            "partials/browse_playlists.html",
            {"playlists": playlists, "action": action, "offset": 0, "limit": limit, "has_more": False},
        )
