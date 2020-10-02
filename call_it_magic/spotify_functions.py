import base64
import json
import queue
import random
import threading
import time
import uuid
from io import BytesIO

import spotipy
from PIL import Image, ImageDraw, ImageFont
from flask import session, request, redirect, url_for, render_template
from spotipy.oauth2 import SpotifyOAuth

from call_it_magic.cache import session_cache_path
from call_it_magic.sftp import sftp_connection

scopes = [
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


def authenticate():
    if not session.get('uuid'):
        session['uuid'] = str(uuid.uuid4())

    if not session.get('auth_manager'):
        session['auth_manager'] = SpotifyOAuth(scope=' '.join(scopes),
                                               cache_path=session_cache_path(),
                                               show_dialog=True)

    if request.args.get("code"):
        session['auth_manager'].get_access_token(request.args.get("code"))
        return redirect(url_for('authenticate'))

    if not session['auth_manager'].get_cached_token():
        auth_url = session['auth_manager'].get_authorize_url()
        return redirect(auth_url)

    if not session.get('spotify'):
        session['spotify'] = spotipy.Spotify(auth_manager=session['auth_manager'])

    return redirect(url_for('index'))


def generate_cover_image(playlist_id):
    if not session.get('spotify'):
        return redirect(url_for('index'))

    text = "🧨 Generated Power"
    text = "Generated Power"
    fontsize = 120

    img = Image.new('RGB', (1500, 1500), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype("Roboto-Black.ttf", fontsize)

    w, h = draw.textsize(text, font=font)
    draw.text(((1500 - w) / 2, (1500 - h) / 2), text, fill=(255, 255, 0), font=font)

    buffer = BytesIO()
    img.save('generated-power.jpg')
    img.seek(0)
    img.save(buffer, format="JPEG")

    session['spotify'].playlist_upload_cover_image(playlist_id, base64.b64encode(buffer.getvalue()))

    return redirect(url_for('index'))


def build_playlist(playlist_id):
    if not session.get('spotify'):
        return redirect(url_for('index'))

    saved_tracks = session['spotify'].current_user_saved_tracks(limit=30)
    spotify_limit_max_tracks = 100

    playlists = [
        playlist_id,
        '2GEXzPeksIINQMTivWQ2el',  # HARDCORE💥
        '5J48965fCl65VnmuU3fmOj',  # 🔥 Uptempo Release Radar
        '7D4rwrnwUPXxltKJhMVOHk'  # UPTEMPO⚡️
    ]

    build_track_list = []
    for track in saved_tracks.get('items'):
        track_id = track.get('track').get('id')
        if track_id not in build_track_list and track_id not in get_blacklist().get('tracks'):
            build_track_list.append(track_id)

    for get_id in playlists:
        for track in session['spotify'].playlist(get_id).get('tracks').get('items')[:20]:
            track_id = track.get('track').get('id')
            if track_id not in build_track_list and track_id not in get_blacklist().get('tracks'):
                build_track_list.append(track_id)

    try:
        session['spotify'].playlist_replace_items(playlist_id, [])
    except ValueError:
        return render_template('pages/error.html', message='Can\'t empty playlist: {}'.format(ValueError))

    split_list = [build_track_list[x:x + spotify_limit_max_tracks]
                  for x in range(0, len(build_track_list), spotify_limit_max_tracks)]
    for part_list in split_list:
        try:
            session['spotify'].playlist_add_items(playlist_id, part_list)
        except ValueError:
            return render_template('pages/error.html', message='Can\'t add track to playlist: {}'.format(ValueError))

    return redirect(url_for('index'))


def get_blacklist():
    sftp_connection('/heroku/spotify-likes-to-playlist', 'blacklist.json', 'get')

    with open('blacklist.json') as blacklist_file:
        blacklist_file.seek(0, 0)
        return json.load(blacklist_file)


def edit_blacklist():
    if request.method == 'POST' and request.get_json(force=True):
        new_data = request.get_json(force=True)

        if new_data.get('tracks'):
            with open('blacklist.json', 'r+') as blacklist_file:
                blacklist_file.seek(0, 0)
                json.dump(new_data, blacklist_file, indent=4)
                blacklist_file.truncate()

        return sftp_connection('/heroku/spotify-likes-to-playlist', 'blacklist.json', 'put')

    return render_template('pages/actions_blacklist.html', data=get_blacklist())


def select_blacklist():
    return sftp_connection('/heroku/spotify-likes-to-playlist', 'blacklist.json', 'get')
