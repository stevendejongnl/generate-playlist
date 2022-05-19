from flask import Blueprint, jsonify, make_response

from lib.playlist import Playlist

api_playlist_blueprint = Blueprint('api_playlist', __name__, url_prefix='/api')


@api_playlist_blueprint.route('/playlist')
def playlist():
    return make_response(jsonify(Playlist().get()), 200)


@api_playlist_blueprint.route('/playlist', methods=['POST'])
def playlist_post():
    return Playlist().post()
