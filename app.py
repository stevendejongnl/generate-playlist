import os
from os.path import join, dirname

from dotenv import load_dotenv
from flask import Flask, render_template, make_response, jsonify
from flask_session import Session

from api.playlist import api_playlist_blueprint
from api.blacklist import api_blacklist_blueprint
from api.spotify import api_spotify_blueprint
from lib.mongo import MongoAuthentication
from routes.home import home_blueprint
from routes.spotify import spotify_blueprint
from lib import spotify
from lib.blacklist import Blacklist

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

environment = os.getenv('ENVIRONMENT')
app = Flask(__name__, template_folder='templates', static_url_path='/static')

if environment == 'production':
    app.config.from_object('config.ProductionConfig')
else:
    app.config.from_object('config.DevelopmentConfig')

client = MongoAuthentication()

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
# app.config['SESSION_TYPE'] = 'mongodb'

# app.config['SESSION_MONGODB'] = client.connect()
# app.config['SESSION_MONGODB_DB'] = 'playlistgenerator'
# app.config['SESSION_MONGODB_COLLECT'] = 'sessions'

# app.config['SESSION_PERMANENT'] = True  # if set to true, close the browser session is failure.
# app.config['SESSION_USE_SIGNER'] = False  # whether to send to the browser session cookie value to encrypt
# app.config['SESSION_KEY_PREFIX'] = 'session:'  # the prefix of the value stored in session

app.config['SECRET_KEY'] = os.urandom(64)

Session(app)

app.register_blueprint(home_blueprint)
app.register_blueprint(spotify_blueprint)
app.register_blueprint(api_playlist_blueprint)
app.register_blueprint(api_blacklist_blueprint)
app.register_blueprint(api_spotify_blueprint)


# register_blueprint(app)


@app.route('/actions')
@app.route('/actions/<action_type>', methods=['GET', 'POST'])
def actions(action_type=None):
    if not action_type:
        return render_template('pages/actions_not-set.html')

    if 'generate' in action_type:
        return spotify.build_playlist(os.environ.get('PLAYLIST_ID'))

    if 'image' in action_type:
        return spotify.generate_cover_image(os.environ.get('PLAYLIST_ID'))

    if 'blacklist_view' in action_type:
        blacklist = Blacklist()

        return make_response(jsonify({"status": "ok", "data": blacklist.get()}), 200)

    if 'blacklist_advanced' in action_type:
        # if request.method == 'POST' and request.get_json(force=True):
        #     new_data = request.get_json(force=True)
        #
        #     if new_data.get('tracks'):
        #         with open('blacklist.json', 'r+') as blacklist_file:
        #             blacklist_file.seek(0, 0)
        #             json.dump(new_data, blacklist_file, indent=4)
        #             blacklist_file.truncate()
        #
        #     # return sftp_connection('/heroku/spotify-likes-to-playlist', 'blacklist.json', 'put')
        #     return new_data

        blacklist = Blacklist()

        return render_template('pages/actions_blacklist.html', blacklist=blacklist.get())

    if 'blacklist' in action_type:
        blacklist = Blacklist()

        return make_response(jsonify(blacklist.get()), 200)

    return render_template('pages/error.html', message='If you don\'t know what you are doing, do it right!')


if __name__ == '__main__':
    app.run()
