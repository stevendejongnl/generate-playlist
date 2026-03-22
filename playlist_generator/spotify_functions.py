import base64
import os
import random
import uuid
import logging
from io import BytesIO
from typing import List, Optional, Any, Dict, Union

import spotipy
from PIL import Image, ImageDraw, ImageFont, Image as PILImage
from spotipy.oauth2 import SpotifyOAuth
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates

from playlist_generator.config import Config

logger = logging.getLogger(__name__)


class SpotifyManager:
    scopes: List[str] = [
        'ugc-image-upload',
        'playlist-read-collaborative',
        'playlist-modify-public',
        'playlist-read-private',
        'playlist-modify-private',
        'user-library-modify',
        'user-library-read'
    ]

    def get_spotify_client(self, request: Request) -> Optional[spotipy.Spotify]:
        token_info: Optional[Dict[str, Any]] = request.session.get('token_info')
        if not token_info:
            logger.warning("No token_info in session; cannot create Spotify client.")
            return None
        logger.info("Spotify client created.")
        return spotipy.Spotify(auth=token_info['access_token'])

    def authenticate(self, request: Request) -> Response:
        logger.info("Starting Spotify authentication flow.")
        if not request.session.get('uuid'):
            request.session['uuid'] = str(uuid.uuid4())
            logger.info(f"Generated new session UUID: {request.session['uuid']}")
        if not request.session.get('token_info'):
            auth_manager: SpotifyOAuth = SpotifyOAuth(
                client_id=Config.SPOTIPY_CLIENT_ID,
                client_secret=Config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIPY_REDIRECT_URI,
                scope=' '.join(self.scopes),
                show_dialog=True
            )
            code = request.query_params.get("code")
            if code:
                logger.info("Received Spotify auth code; fetching access token.")
                token_info = auth_manager.get_access_token(code)
                request.session['token_info'] = token_info
                logger.info("Spotify access token stored in session.")
                return RedirectResponse(url='/authenticate')
            auth_url = auth_manager.get_authorize_url()
            logger.info(f"Redirecting to Spotify auth URL: {auth_url}")
            return RedirectResponse(url=auth_url)
        return RedirectResponse(url='/')

    def generate_cover_image(self, request: Request, playlist_manager: Any = None) -> Response:
        playlist_id = self._get_playlist_id(playlist_manager)
        logger.info(f"Generating cover image for playlist: {playlist_id}")
        spotify_client = self.get_spotify_client(request)
        if not spotify_client:
            logger.error("Spotify client not available; cannot generate cover image.")
            return RedirectResponse(url='/')
        img: PILImage = self._create_cover_image("Generated Power", 120, (1500, 1500), (73, 109, 137), (255, 255, 0))
        self._save_image(img, 'generated-power.jpg')
        buffer: BytesIO = self._image_to_buffer(img)
        spotify_client.playlist_upload_cover_image(playlist_id, base64.b64encode(buffer.getvalue()))
        logger.info("Cover image uploaded to Spotify playlist.")
        return RedirectResponse(url='/')

    def _get_playlist_id(self, playlist_manager: Any = None) -> str:
        if playlist_manager is not None:
            target = playlist_manager.get_target()
            if target:
                return target
        return os.environ.get('PLAYLIST_ID', '')

    def _get_font_path(self, font_name: str) -> str:
        root_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root_dir, font_name)

    def _create_cover_image(
        self,
        text: str,
        fontsize: int,
        size: tuple,
        bg_color: tuple,
        text_color: tuple,
        font_name: str = "Roboto-Black.ttf"
    ) -> PILImage:
        logger.info(f"Creating cover image with text: {text}")
        img: PILImage = Image.new('RGB', size, color=bg_color)
        draw: ImageDraw = ImageDraw.Draw(img)
        font_path: str = self._get_font_path(font_name)
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except OSError:
            logger.warning(f"Font not found: {font_path}. Using default font.")
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size[0] - w) / 2, (size[1] - h) / 2), text, fill=text_color, font=font)
        return img

    def _save_image(self, img: PILImage, filename: str) -> None:
        img.save(filename)
        logger.info(f"Image saved to file: {filename}")

    def _image_to_buffer(self, img: PILImage) -> BytesIO:
        buffer: BytesIO = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        logger.debug("Image converted to buffer.")
        return buffer

    def build_playlist(self, request: Request, blacklist_tracks: List[str], source_ids: Optional[List[str]] = None, playlist_manager: Any = None) -> Response:
        playlist_id = self._get_playlist_id(playlist_manager)
        logger.info(f"Building playlist: {playlist_id}")
        try:
            spotify_client = self._validate_playlist_and_client(playlist_id, request)
            build_track_list = self._collect_tracks(playlist_id, blacklist_tracks, spotify_client, source_ids)
            self._clear_playlist(playlist_id, spotify_client)
            self._add_tracks_to_playlist(playlist_id, build_track_list, spotify_client)
            logger.info("Playlist build complete.")
        except Exception as e:
            logger.error(f"Error building playlist: {e}", exc_info=True)
            raise
        return RedirectResponse(url='/')

    def _validate_playlist_and_client(self, playlist_id: str, request: Request) -> spotipy.Spotify:  # noqa: E501
        if not playlist_id:
            raise ValueError("No target playlist configured. Set one in Manage Playlists or set PLAYLIST_ID env var.")
        spotify_client = self.get_spotify_client(request)
        if not spotify_client:
            raise ValueError("Spotify client not available.")
        return spotify_client

    def _clear_playlist(self, playlist_id: str, spotify_client: spotipy.Spotify) -> None:
        logger.info(f"Clearing playlist: {playlist_id}")
        spotify_client.playlist_replace_items(playlist_id, [])

    def _collect_tracks(
        self,
        playlist_id: str,
        blacklist_tracks: List[str],
        spotify_client: spotipy.Spotify,
        source_ids: Optional[List[str]] = None
    ) -> List[str]:
        logger.info("Collecting tracks for playlist build.")
        saved_tracks = spotify_client.current_user_saved_tracks(limit=30)
        playlists: List[str] = source_ids if source_ids is not None else [playlist_id]
        build_track_list: List[str] = []
        for track in saved_tracks.get('items', []):
            track_id = track.get('track', {}).get('id')
            if track_id and track_id not in build_track_list and track_id not in blacklist_tracks:
                build_track_list.append(track_id)
        for get_id in playlists:
            for track in spotify_client.playlist(get_id).get('tracks', {}).get('items', []):
                if track.get('track'):
                    track_id = track.get('track', {}).get('id')
                    if track_id and track_id not in build_track_list and track_id not in blacklist_tracks:
                        build_track_list.append(track_id)
        random.shuffle(build_track_list)
        logger.info(f"Collected {len(build_track_list)} tracks for playlist.")
        return build_track_list

    def _add_tracks_to_playlist(self, playlist_id: str, build_track_list: List[str], spotify_client: spotipy.Spotify) -> None:
        logger.info(f"Adding {len(build_track_list)} tracks to playlist {playlist_id}.")
        chunk_size: int = 100
        for i in range(0, len(build_track_list), chunk_size):
            chunk = build_track_list[i:i + chunk_size]
            spotify_client.playlist_add_items(playlist_id, chunk)
            logger.info(f"Added {len(chunk)} tracks to playlist.")
