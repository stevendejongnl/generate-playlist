import base64
import spotipy
import uuid

from io import BytesIO
from flask import session, request, redirect, url_for, jsonify
from PIL import Image, ImageDraw, ImageFont
from spotipy.oauth2 import SpotifyOAuth

from call_it_magic.cache import session_cache_path

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
        if track.get('track').get('id') not in build_track_list:
            build_track_list.append(track.get('track').get('id'))

    for id in playlists:
        for track in session['spotify'].playlist(id).get('tracks').get('items')[:20]:
            if track.get('track').get('id') not in build_track_list:
                build_track_list.append(track.get('track').get('id'))

    try:
        session['spotify'].playlist_replace_items(playlist_id, [])
    except ValueError:
        return jsonify('Can\'t empty playlist: {}'.format(ValueError))

    split_list = [build_track_list[x:x + spotify_limit_max_tracks]
                  for x in range(0, len(build_track_list), spotify_limit_max_tracks)]
    for part_list in split_list:
        try:
            session['spotify'].playlist_add_items(playlist_id, part_list)
        except ValueError:
            return jsonify('Can\'t add track to playlist: {}'.format(ValueError))

    return redirect(url_for('index'))
