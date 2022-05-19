from flask import Blueprint

from lib import spotify

spotify_blueprint = Blueprint('spotify', __name__)


@spotify_blueprint.route('/authenticate')
def authenticate():
    return spotify.authenticate()


@spotify_blueprint.route('/logout')
def logout():
    spotify.logout()
