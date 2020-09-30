import os
import spotipy

from flask import Flask, jsonify
from spotipy.oauth2 import SpotifyOAuth


# https://devcenter.heroku.com/articles/scheduler
app = Flask(__name__)


class Spotify:
    def __init__(self):
        self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=os.environ['SCOPE']))

    def get_saved_tracks(self):
        return self.spotify.current_user_saved_tracks()

    def get_playlists(self):
        return self.spotify.current_user_playlists()

    def get_playlist(self, id):
        return self.spotify.playlist(id)

    def generated_power(self):
        playlist_id = os.environ['GENERATED_POWER']
        saved_tracks = self.spotify.current_user_saved_tracks(30)
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
            for track in self.get_playlist(id)['tracks']['items']:
                if track['track']['id'] not in build_track_list:
                    build_track_list.append(track['track']['id'])

        self.spotify.playlist_replace_items(playlist_id, [])
        split_list = [build_track_list[x:x + spotify_limit_max_tracks] for x in range(0, len(build_track_list), spotify_limit_max_tracks)]
        for part_list in split_list:
            self.spotify.playlist_add_items(playlist_id, part_list)

        return 'OK'

        # Todo - Add playlist cover
        # self.spotify.playlist_cover_image()

        # return playlist


@app.route('/')
def index():
    spotify = Spotify()

    return spotify.generated_power()


if __name__ == '__main__':
    app.run(debug=os.environ['FLASK_DEBUG'])
