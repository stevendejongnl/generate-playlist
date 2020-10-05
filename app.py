import os

from dotenv import load_dotenv
from flask import session, Flask, redirect, jsonify, url_for, render_template, send_from_directory
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_seeder import FlaskSeeder

from call_it_magic import spotify_functions
from call_it_magic.cache import session_cache_path

load_dotenv()

app = Flask(__name__, template_folder='templates', static_url_path='/static')

app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config.from_object(os.environ.get('APP_SETTINGS'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Session(app)
db = SQLAlchemy(app)
seeder = FlaskSeeder()
seeder.init_app(app, db)

from models import Blacklist


@app.route('/')
def index():
    if not session.get('auth_manager') or \
            (session.get('auth_manager') and not session['auth_manager'].get_cached_token()):
        return render_template('pages/index.html', url_list=[
            {
                "href": url_for('authenticate'),
                "text": "Authenticate"
            }
        ])

    return render_template('pages/index.html', url_list=[
        {
            "href": url_for('actions', action_type='generate'),
            "text": "Build playlist"
        }, {
            "href": url_for('actions', action_type='image'),
            "text": "Create new image"
        }, {
            "href": url_for('actions', action_type='blacklist_advanced'),
            "text": "Edit blacklist"
        }, {
            "href": url_for('actions', action_type='blacklist'),
            "text": "Select tracks for blacklist"
        }, {
            "href": url_for('sign_out'),
            "text": "Sign out"
        }
    ])


@app.route('/authenticate')
def authenticate():
    return spotify_functions.authenticate()


@app.route('/actions')
@app.route('/actions/<action_type>', methods=['GET', 'POST'])
def actions(action_type=None):
    if not action_type:
        return render_template('pages/actions_not-set.html')

    if 'generate' in action_type:
        return spotify_functions.build_playlist(os.environ.get('PLAYLIST_ID'))

    if 'image' in action_type:
        return spotify_functions.generate_cover_image(os.environ.get('PLAYLIST_ID'))

    if 'blacklist_view' in action_type:
        return spotify_functions.get_blacklist()

    if 'blacklist_advanced' in action_type:
        return spotify_functions.edit_blacklist()

    if 'blacklist' in action_type:
        return spotify_functions.select_blacklist()

    return render_template('pages/error.html', message='If you don\'t know what you are doing, do it right!')


@app.route('/sign_out')
def sign_out():
    os.remove(session_cache_path())
    session.clear()
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))

    return redirect(url_for('index'))


@app.route("/blacklist")
def get_blacklist():
    try:
        blacklist = Blacklist.query.all()
        return jsonify([e.serialize() for e in blacklist])
    except Exception as e:
        return (str(e))


@app.route("/blacklist/add", methods=['POST'])
def add_to_blacklist():
    from call_it_magic.blacklist import insert
    return insert()


if __name__ == '__main__':
    app.run()
