import base64
import json
import os
import random
import uuid
import logging
from io import BytesIO
from typing import List, Optional, Any, Dict, Union, Tuple

from PIL import Image, ImageDraw, ImageFont, Image as PILImage
from flask import session, request, redirect, url_for, render_template, Response

from playlist_generator.config import Config

logger = logging.getLogger(__name__)


class SpotifyManager:
    def __init__(
        self,
        session,
        request,
        redirect,
        url_for,
        render_template,
        spotipy_cls,
        spotify_oauth_cls,
        config,
        logger=logger
    ):
        self.session = session
        self.request = request
        self.redirect = redirect
        self.url_for = url_for
        self.render_template = render_template
        self.spotipy_cls = spotipy_cls
        self.spotify_oauth_cls = spotify_oauth_cls
        self.config = config
        self.logger = logger
        self.scopes = [
            'ugc-image-upload',
            'playlist-read-collaborative',
            'playlist-modify-public',
            'playlist-read-private',
            'playlist-modify-private',
            'user-library-modify',
            'user-library-read'
        ]

    def get_spotify_client(self) -> Optional[Any]:
        token_info: Optional[Dict[str, Any]] = self.session.get('token_info')
        if not token_info:
            self.logger.warning("No token_info in session; cannot create Spotify client.")
            return None
        self.logger.info("Spotify client created.")
        return self.spotipy_cls(auth=token_info['access_token'])

    def authenticate(self) -> Union[Any, str]:
        self.logger.info("Starting Spotify authentication flow.")
        if not self.session.get('uuid'):
            self.session['uuid'] = str(uuid.uuid4())
            self.logger.info(f"Generated new session UUID: {self.session['uuid']}")
        if not self.session.get('token_info'):
            auth_manager = self.spotify_oauth_cls(
                client_id=self.config.SPOTIPY_CLIENT_ID,
                client_secret=self.config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=self.config.SPOTIPY_REDIRECT_URI,
                scope=' '.join(self.scopes),
                show_dialog=True,
                cache_path=self.config.SPOTIPY_CACHE_PATH
            )
            if self.request.args.get("code"):
                self.logger.info("Received Spotify auth code; fetching access token.")
                token_info = auth_manager.get_access_token(self.request.args.get("code"))
                self.session['token_info'] = token_info
                self.logger.info("Spotify access token stored in session.")
                return self.redirect(self.url_for('authenticate'))
            if not auth_manager.get_cached_token():
                auth_url = auth_manager.get_authorize_url()
                self.logger.info(f"Redirecting to Spotify auth URL: {auth_url}")
                return self.redirect(auth_url)
            token_info = auth_manager.get_cached_token()
            self.session['token_info'] = token_info
            self.logger.info("Cached Spotify token stored in session.")
        return self.redirect(self.url_for('index'))

    def generate_cover_image(self, playlist_id: str) -> Response:
        self.logger.info(f"Generating cover image for playlist: {playlist_id}")
        spotify_client = self.get_spotify_client()
        if not spotify_client:
            self.logger.error("Spotify client not available; cannot generate cover image.")
            return self.redirect(self.url_for('index'))
        img: PILImage = self._create_cover_image("Generated Power", 120, (1500, 1500), (73, 109, 137), (255, 255, 0))
        self._save_image(img, 'generated-power.jpg')
        buffer: BytesIO = self._image_to_buffer(img)
        spotify_client.playlist_upload_cover_image(playlist_id, base64.b64encode(buffer.getvalue()))
        self.logger.info("Cover image uploaded to Spotify playlist.")
        return self.redirect(self.url_for('index'))

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
        self.logger.info(f"Creating cover image with text: {text}")
        img: PILImage = Image.new('RGB', size, color=bg_color)
        draw: ImageDraw = ImageDraw.Draw(img)
        font_path: str = self._get_font_path(font_name)
        try:
            font: ImageFont = ImageFont.truetype(font_path, fontsize)
        except OSError:
            self.logger.warning(f"Font not found: {font_path}. Using default font.")
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size[0] - w) / 2, (size[1] - h) / 2), text, fill=text_color, font=font)
        return img

    def _save_image(self, img: PILImage, filename: str) -> None:
        img.save(filename)
        self.logger.info(f"Image saved to file: {filename}")

    def _image_to_buffer(self, img: PILImage) -> BytesIO:
        buffer: BytesIO = BytesIO()
        img.seek(0)
        img.save(buffer, format="JPEG")
        self.logger.debug("Image converted to buffer.")
        return buffer

    def build_playlist(self, playlist_id: str, blacklist_tracks: List[str]) -> Response:
        self.logger.info(f"Building playlist: {playlist_id} with blacklist: {blacklist_tracks}")
        try:
            spotify_client = self._validate_playlist_and_client(playlist_id)
            build_track_list = self._collect_tracks(playlist_id, blacklist_tracks, spotify_client)
            self._clear_playlist(playlist_id, spotify_client)
            self._add_tracks_to_playlist(playlist_id, build_track_list, spotify_client)
            self.logger.info("Playlist build complete.")
        except Exception as e:
            self.logger.error(f"Error building playlist: {e}", exc_info=True)
            return self.render_template('pages/error.html', message=f'Playlist error: {e}')
        return self.redirect(self.url_for('index'))

    def _validate_playlist_and_client(self, playlist_id: str) -> Any:
        if not playlist_id:
            raise ValueError("Playlist ID is required.")
        spotify_client = self.get_spotify_client()
        if not spotify_client:
            raise ValueError("Spotify client not available.")
        return spotify_client

    def _clear_playlist(self, playlist_id: str, spotify_client: Any) -> None:
        self.logger.info(f"Clearing playlist: {playlist_id}")
        spotify_client.playlist_replace_items(playlist_id, [])
        self.logger.info("Playlist cleared.")

    def _collect_tracks(self, playlist_id: str, blacklist_tracks: List[str], spotify_client: Any) -> List[str]:
        self.logger.info("Collecting tracks for playlist build.")
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
        self.logger.info(f"Final track list for playlist: {build_track_list}")
        return build_track_list

    def _add_tracks_to_playlist(self, playlist_id: str, build_track_list: List[str], spotify_client: Any) -> None:
        self.logger.info(f"Adding tracks to playlist {playlist_id}.")
        spotify_limit_max_tracks: int = 100
        split_list: List[List[str]] = [build_track_list[x:x + spotify_limit_max_tracks]
                      for x in range(0, len(build_track_list), spotify_limit_max_tracks)]
        for part_list in split_list:
            spotify_client.playlist_add_items(playlist_id, part_list)
            self.logger.info(f"Added {len(part_list)} tracks to playlist.")


def get_blacklist(open_func=open, json_load=json.load) -> Any:
    with open_func('blacklist.json') as blacklist_file:
        blacklist_file.seek(0, 0)
        return json_load(blacklist_file)


def edit_blacklist(request_obj=None, render_template_func=None, get_blacklist_func=None, open_func=open, json_dump=json.dump):
    if request_obj is None:
        from flask import request as request_obj
    if render_template_func is None:
        from flask import render_template as render_template_func
    if get_blacklist_func is None:
        get_blacklist_func = get_blacklist
    if request_obj.method == 'POST' and request_obj.get_json(force=True):
        new_data = request_obj.get_json(force=True)
        if new_data.get('tracks'):
            with open_func('blacklist.json', 'r+') as blacklist_file:
                blacklist_file.seek(0, 0)
                json_dump(new_data, blacklist_file, indent=4)
                blacklist_file.truncate()
        return new_data
    return render_template_func('pages/actions_blacklist.html', data=get_blacklist_func())
