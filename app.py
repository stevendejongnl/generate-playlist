import base64
import os
import unicodedata
from io import BytesIO

import spotipy
import uuid

from flask import Flask, session, request, redirect, jsonify
from flask_session import Session
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw, ImageFont


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get('uuid')


def authenticate(scopes):
    if not session.get('uuid'):
        session['uuid'] = str(uuid.uuid4())

    auth_manager = spotipy.oauth2.SpotifyOAuth(scope=' '.join(scopes),
                                               cache_path=session_cache_path(),
                                               show_dialog=True)

    if request.args.get("code"):
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.get_cached_token():
        auth_url = auth_manager.get_authorize_url()
        return {
            ''
        }

    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return spotify


class Spotify:
    def __init__(self):
        self.scopes = [
            # Images
            'ugc-image-upload',
            # Playlists
            'playlist-read-collaborative',
            'playlist-modify-public',
            'playlist-read-private',
            'playlist-modify-private',
            # Library
            'user-library-modify',
            'user-library-read'
        ]

        self.spotify = authenticate(self.scopes)

    def generate_cover_image(self, playlist_id):
        text = "🧨 Generated Power"
        text = "Generated Power"
        fontsize = 120

        img = Image.new('RGB', (1500, 1500), color=(73, 109, 137))
        draw = ImageDraw.Draw(img)

        font = ImageFont.truetype("Roboto-Black.ttf", fontsize)

        w, h = draw.textsize(text, font=font)
        draw.text(((1500 - w) / 2, (1500 - h) / 2), text, fill=(255, 255, 0), font=font)

        buffer = BytesIO()
        img.save(buffer, format="JPEG")

        return self.spotify.playlist_upload_cover_image(playlist_id, base64.b64encode(buffer.getvalue()))

    def get_saved_tracks(self):
        return self.spotify.current_user_saved_tracks()

    def get_playlists(self):
        return self.spotify.current_user_playlists()

    def get_playlist(self, id):
        return self.spotify.playlist(id)

    def generated_power(self):
        playlist_id = os.environ.get('GENERATED_POWER')
        saved_tracks = self.spotify.current_user_saved_tracks(limit=30)
        spotify_limit_max_tracks = 100

        playlists = [
            playlist_id,
            '2GEXzPeksIINQMTivWQ2el',  # HARDCORE💥
            '5J48965fCl65VnmuU3fmOj',  # 🔥 Uptempo Release Radar
            '7D4rwrnwUPXxltKJhMVOHk'  # UPTEMPO⚡️
        ]

        build_track_list = []
        for track in saved_tracks['items']:
            if track['track']['id'] not in build_track_list:
                build_track_list.append(track['track']['id'])

        for id in playlists:
            for track in self.get_playlist(id)['tracks']['items'][:20]:
                if track['track']['id'] not in build_track_list:
                    build_track_list.append(track['track']['id'])

        self.spotify.playlist_replace_items(playlist_id, [])
        split_list = [build_track_list[x:x + spotify_limit_max_tracks]
                      for x in range(0, len(build_track_list), spotify_limit_max_tracks)]
        for part_list in split_list:
            self.spotify.playlist_add_items(playlist_id, part_list)

        return jsonify('OK')


@app.route('/')
def index():
    spotify = Spotify()

    return spotify.generated_power()


@app.route('/image')
def image():
    spotify = Spotify()

    spotify.generate_cover_image(os.environ.get('GENERATED_POWER'))

    return jsonify('OK')


@app.route('/sign_out')
def sign_out():
    os.remove(session_cache_path())
    session.clear()
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG'))
