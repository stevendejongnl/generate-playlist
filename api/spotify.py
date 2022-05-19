from flask import Blueprint

from lib.spotify import generate, create_cover

api_spotify_blueprint = Blueprint('api_spotify', __name__, url_prefix='/api')


@api_spotify_blueprint.route('/spotify/generate', methods=['POST'])
def spotify_generate_post():
    return generate()


@api_spotify_blueprint.route('/spotify/create_cover', methods=['POST'])
def spotify_create_cover_post():
    return create_cover()
