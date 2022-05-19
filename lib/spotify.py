import base64
import json
import os
import queue
import random
import threading
import time
import uuid
from io import BytesIO
from pprint import pprint

import spotipy
from PIL import Image, ImageDraw, ImageFont
from flask import session, request, redirect, url_for, render_template, jsonify, abort
from spotipy.oauth2 import SpotifyOAuth

from lib.blacklist import Blacklist

from lib.mongo import MongoAuthentication

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


caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def spotify_cache():
    cache_file = caches_folder + session['uuid']

    # if os.path.exists(cache_file):
    return cache_file

    # try:
    #     client = MongoAuthentication()
    #     collection = client.connect()
    #     cache_collection = collection.spotify_cache
    #
    #     cache_session = cache_collection.find_one({'uuid': session['uuid']})
    #
    #     if not cache_session:
    #         cache_session = {
    #             'uuid': session['uuid']
    #         }
    #         cache_collection.insert_one(cache_session)
    #
    #     return cache_file
    # except Exception as error:
    #     return jsonify({
    #         "message": str(error)
    #     }), 500


def authenticate():
    if not session.get('uuid'):
        session['uuid'] = str(uuid.uuid4())

    if not session.get('auth_manager'):
        session['auth_manager'] = SpotifyOAuth(scope=' '.join(scopes),
                                               cache_path=spotify_cache(),
                                               show_dialog=True)

    if request.args.get("code"):
        session['auth_manager'].get_access_token(request.args.get("code"))
        return redirect(url_for('spotify.authenticate'))

    if not session['auth_manager'].get_cached_token():
        auth_url = session['auth_manager'].get_authorize_url()
        return redirect(auth_url)

    if not session.get('spotify'):
        session['spotify'] = spotipy.Spotify(auth_manager=session['auth_manager'])

    return redirect(url_for('home.index'))


def logout():
    os.remove(spotify_cache())
    session.clear()
    try:
        os.remove(spotify_cache())
    except OSError as error:
        print("Error: %s - %s." % (error.filename, error.strerror))

    return redirect(url_for('home.index'))


def _track_not_on_blacklist(track, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids):
    track_id = track.get('id')
    album_id = track.get('album').get('id')
    artists = track.get('artists')

    track_deny = track_id in track_blacklist_ids
    album_deny = album_id in album_blacklist_ids
    artist_deny = False
    for artist in artists:
        if artist.get('id') in artist_blacklist_ids:
            artist_deny = True

    if not track_deny and not album_deny and not artist_deny:
        return track_id

    return None


def _get_saved_tracks(saved_tracks, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids):
    track_list = []
    for track in saved_tracks.get('items'):
        track = track.get('track')

        track_id = _track_not_on_blacklist(track, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids)

        if not track_id:
            continue

        track_list.append(track_id)

    return track_list


def _get_playlist_tracks(playlists, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids):
    track_list = []
    for playlist_id in playlists:
        playlist = session['spotify'].playlist(playlist_id)
        playlist_tracks = playlist.get('tracks').get('items')
        tracks = [track.get('track') for track in playlist_tracks]

        for track in tracks:
            track_id = _track_not_on_blacklist(track, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids)

            if not track_id:
                continue

            track_list.append(track_id)

    return track_list


def _randomize_tracks(track_list):
    random.shuffle(track_list)
    return track_list


def _split_track_list(track_list, spotify_limit_max_tracks):
    return [track_list[x:x + spotify_limit_max_tracks] for x in range(0, len(track_list), spotify_limit_max_tracks)]


def create_cover():
    session['auth_manager'] = SpotifyOAuth(scope=' '.join(scopes),
                                           cache_path=caches_folder + 'c21f422f-c68c-4670-9f27-a8a2768f65a7',
                                           show_dialog=True)
    session['spotify'] = spotipy.Spotify(auth_manager=session['auth_manager'])

    if not session.get('spotify'):
        return abort(jsonify(message="Unauthorized"))

    playlist_id = request.json.get('playlist_id')
    title = request.json.get('title')
    fontsize = request.json.get('fontsize')

    img = Image.new('RGB', (1500, 1500), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype("Roboto-Black.ttf", fontsize)

    w, h = draw.textsize(title, font=font)
    draw.text(((1500 - w) / 2, (1500 - h) / 2), title, fill=(255, 255, 0), font=font)

    buffer = BytesIO()
    img.save('cover_image.jpg')
    img.seek(0)
    img.save(buffer, format="JPEG")

    session['spotify'].playlist_upload_cover_image(playlist_id, base64.b64encode(buffer.getvalue()))

    return jsonify('ok')


def generate():
    session['auth_manager'] = SpotifyOAuth(scope=' '.join(scopes),
                                           cache_path=caches_folder + 'c21f422f-c68c-4670-9f27-a8a2768f65a7',
                                           show_dialog=True)
    session['spotify'] = spotipy.Spotify(auth_manager=session['auth_manager'])

    if not session.get('spotify'):
        return abort(jsonify(message="Unauthorized"))

    playlist_id = request.json.get('playlist_id')
    additional_playlist_ids = request.json.get('additional_playlist_ids', [])
    use_total_saved_tracks = request.json.get('use_total_saved_tracks', 0)

    saved_tracks = session['spotify'].current_user_saved_tracks(limit=use_total_saved_tracks)
    spotify_limit_max_tracks = 100

    playlists = [
        playlist_id,
        *additional_playlist_ids
    ]
    # playlists = [
    #     playlist_id,
    #     '2GEXzPeksIINQMTivWQ2el',  # HARDCORE💥
    #     '5J48965fCl65VnmuU3fmOj',  # 🔥 Uptempo Release Radar
    #     '7D4rwrnwUPXxltKJhMVOHk'  # UPTEMPO⚡️
    # ]

    track_blacklist = Blacklist().get('track')
    track_blacklist_ids = [track.id for track in track_blacklist]
    album_blacklist = Blacklist().get('album')
    album_blacklist_ids = [album.id for album in album_blacklist]
    artist_blacklist = Blacklist().get('artist')
    artist_blacklist_ids = [artist.id for artist in artist_blacklist]

    track_list = [
        *_get_saved_tracks(saved_tracks, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids),
        *_get_playlist_tracks(playlists, track_blacklist_ids, album_blacklist_ids, artist_blacklist_ids)
    ]

    try:
        session['spotify'].playlist_replace_items(playlist_id, [])
    except ValueError as error:
        return abort(jsonify(message=f"Can\'t empty playlist: {error}"))

    track_list = _randomize_tracks(track_list)
    track_list_split_up = _split_track_list(track_list, spotify_limit_max_tracks)

    for part_list in track_list_split_up:
        try:
            session['spotify'].playlist_add_items(playlist_id, part_list)
        except ValueError as error:
            return abort(jsonify(message=f"Can\t add tracks to playlist: {error}"))

    return jsonify('ok')
