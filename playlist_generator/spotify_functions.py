import base64
import json
import os
import random
import uuid
import logging
from io import BytesIO
from typing import List, Optional, Any, Dict, Union, Tuple

import spotipy
from PIL import Image, ImageDraw, ImageFont, Image as PILImage
from flask import session, request, redirect, url_for, render_template, Response
from spotipy.oauth2 import SpotifyOAuth

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

    def get_spotify_client(self) -> Optional[spotipy.Spotify]:
        token_info: Optional[Dict[str, Any]] = session.get('token_info')
        if not token_info:
            logger.warning("No token_info in session; cannot create Spotify client.")
            return None
        logger.info("Spotify client created.")
        return spotipy.Spotify(auth=token_info['access_token'])

    def authenticate(self) -> Union[Response, str]:
        logger.info("Starting Spotify authentication flow.")
        if not session.get('uuid'):
            session['uuid'] = str(uuid.uuid4())
            logger.info(f"Generated new session UUID: {session['uuid']}")
        if not session.get('token_info'):
            auth_manager: SpotifyOAuth = SpotifyOAuth(
                client_id=Config.SPOTIPY_CLIENT_ID,
                client_secret=Config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIPY_REDIRECT_URI,
                scope=' '.join(self.scopes),
                show_dialog=True
            )
            if request.args.get("code"):
                logger.info("Received Spotify auth code; fetching access token.")
                token_info = auth_manager.get_access_token(request.args.get("code"))
                session['token_info'] = token_info
                logger.info("Spotify access token stored in session.")
                return redirect(url_for('authenticate'))
            auth_url = auth_manager.get_authorize_url()
            logger.info(f"Redirecting to Spotify auth URL: {auth_url}")
            return redirect(auth_url)
        return redirect(url_for('index'))

    def generate_cover_image(self, playlist_id: str) -> Response:
        logger.info(f"Generating cover image for playlist: {playlist_id}")
        spotify_client = self.get_spotify_client()
        if not spotify_client:
            logger.error("Spotify client not available; cannot generate cover image.")
            return redirect(url_for('index'))
        img: PILImage = self._create_cover_image("Generated Power", 120, (1500, 1500), (73, 109, 137), (255, 255, 0))
        self._save_image(img, 'generated-power.jpg')
        buffer: BytesIO = self._image_to_buffer(img)
        spotify_client.playlist_upload_cover_image(playlist_id, base64.b64encode(buffer.getvalue()))
        logger.info("Cover image uploaded to Spotify playlist.")
        return redirect(url_for('index'))

    def _get_font_path(self, font_name: str) -> str:
        root_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        font_path: str = os.path.join(root_dir, font_name)
        return font_path

    def _create_cover_image(
        self,
        text: str,
        fontsize: int,
        size: Tuple[int, int],
        bg_color: Tuple[int, int, int],
        text_color: Tuple[int, int, int],
        font_name: str = "Roboto-Black.ttf"
    ) -> PILImage:
        logger.info(f"Creating cover image with text: {text}")
        img: PILImage = Image.new('RGB', size, color=bg_color)
        draw: ImageDraw = ImageDraw.Draw(img)
        font_path: str = self._get_font_path(font_name)
        try:
            font: ImageFont = ImageFont.truetype(font_path, fontsize)
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
        img.seek(0)
        img.save(buffer, format="JPEG")
        logger.debug("Image converted to buffer.")
        return buffer

    def build_playlist(self, playlist_id: str, blacklist_tracks: List[str]) -> Response:
        logger.info(f"Building playlist: {playlist_id} with blacklist: {blacklist_tracks}")
        try:
            spotify_client = self._validate_playlist_and_client(playlist_id)
            build_track_list = self._collect_tracks(playlist_id, blacklist_tracks, spotify_client)
            self._clear_playlist(playlist_id, spotify_client)
            self._add_tracks_to_playlist(playlist_id, build_track_list, spotify_client)
            logger.info("Playlist build complete.")
        except Exception as e:
            logger.error(f"Error building playlist: {e}", exc_info=True)
            return render_template('pages/error.html', message=f'Playlist error: {e}')
        return redirect(url_for('index'))

    def _validate_playlist_and_client(self, playlist_id: str) -> spotipy.Spotify:
        if not playlist_id:
            raise ValueError("Playlist ID is required.")
        spotify_client = self.get_spotify_client()
        if not spotify_client:
            raise ValueError("Spotify client not available.")
        return spotify_client

    def _clear_playlist(self, playlist_id: str, spotify_client: spotipy.Spotify) -> None:
        logger.info(f"Clearing playlist: {playlist_id}")
        spotify_client.playlist_replace_items(playlist_id, [])
        logger.info("Playlist cleared.")

    def _collect_tracks(self, playlist_id: str, blacklist_tracks: List[str], spotify_client: spotipy.Spotify) -> List[str]:
        logger.info("Collecting tracks for playlist build.")
        saved_tracks = spotify_client.current_user_saved_tracks(limit=30)
        playlists: List[str] = [
            playlist_id,
            '2GEXzPeksIINQMTivWQ2el',
            '5J48965fCl65VnmuU3fmOj',
            '7D4rwrnwUPXxltKJhMVOHk'
        ]
        build_track_list: List[str] = []
        for track in saved_tracks.get('items'):
            track_id = track.get('track').get('id')
            if track_id not in build_track_list and track_id not in blacklist_tracks:
                build_track_list.append(track_id)
        for get_id in playlists:
            for track in spotify_client.playlist(get_id).get('tracks').get('items'):
                if track.get('track'):
                    track_id = track.get('track').get('id')
                    if track_id not in build_track_list and track_id not in blacklist_tracks:
                        build_track_list.append(track_id)
        random.shuffle(build_track_list)
        logger.info(f"Final track list for playlist: {build_track_list}")
        return build_track_list

    def _add_tracks_to_playlist(self, playlist_id: str, build_track_list: List[str], spotify_client: spotipy.Spotify) -> None:
        logger.info(f"Adding tracks to playlist {playlist_id}.")
        spotify_limit_max_tracks: int = 100
        split_list: List[List[str]] = [build_track_list[x:x + spotify_limit_max_tracks]
                      for x in range(0, len(build_track_list), spotify_limit_max_tracks)]
        for part_list in split_list:
            spotify_client.playlist_add_items(playlist_id, part_list)
            logger.info(f"Added {len(part_list)} tracks to playlist.")


def get_blacklist() -> Any:
    with open('blacklist.json') as blacklist_file:
        blacklist_file.seek(0, 0)
        return json.load(blacklist_file)


def edit_blacklist() -> Any:
    if request.method == 'POST' and request.get_json(force=True):
        new_data = request.get_json(force=True)

        if new_data.get('tracks'):
            with open('blacklist.json', 'r+') as blacklist_file:
                blacklist_file.seek(0, 0)
                json.dump(new_data, blacklist_file, indent=4)
                blacklist_file.truncate()

        return new_data

    return render_template('pages/actions_blacklist.html', data=get_blacklist())
