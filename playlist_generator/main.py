import os
from functools import wraps
import logging
from typing import Callable, Any

from dotenv import load_dotenv
from flask import session, Flask, redirect, jsonify, url_for, render_template, send_from_directory, request, Response
from flask_session import Session

from playlist_generator.blacklist import BlacklistManager
from playlist_generator.config import Config
from playlist_generator.spotify_functions import SpotifyManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def login_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not session.get('token_info'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


class PlaylistGeneratorApp:
    app: Flask
    spotify_manager: SpotifyManager
    blacklist_manager: BlacklistManager

    def __init__(self) -> None:
        logger.info('Starting PlaylistGeneratorApp...')
        load_dotenv()
        self.app = Flask(__name__, template_folder='../templates', static_folder='../static', static_url_path='/static')
        self.app.config['SECRET_KEY'] = Config.SECRET_KEY
        self.app.config['SESSION_TYPE'] = 'filesystem'
        self.app.config['SESSION_FILE_DIR'] = './.flask_session/'
        self.app.config['SESSION_COOKIE_SECURE'] = True
        self.app.config['SESSION_COOKIE_HTTPONLY'] = True
        self.app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        self.app.config['PERMANENT_SESSION_LIFETIME'] = 31536000  # 1 year
        Session(self.app)
        self.spotify_manager = SpotifyManager()
        self.blacklist_manager = BlacklistManager()
        self.register_routes()
        logger.info('App configuration complete.')

        # Ensure .cache directory and .cache/token_cache file exist and are writable
        cache_dir = '.cache'
        cache_file = os.path.join(cache_dir, 'token_cache')
        os.makedirs(cache_dir, exist_ok=True)
        if not os.path.exists(cache_file):
            with open(cache_file, 'w') as f:
                f.write('')
            logger.info(f"Created empty cache file: {cache_file}")
        try:
            os.chmod(cache_dir, 0o777)
            os.chmod(cache_file, 0o666)
            logger.info(f"Set permissions for cache dir and file: {cache_dir}, {cache_file}")
        except Exception as e:
            logger.warning(f"Could not set permissions for cache dir or file: {e}")
        logger.info(f"Cache dir exists: {os.path.exists(cache_dir)}, writable: {os.access(cache_dir, os.W_OK)}")
        logger.info(f"Cache file exists: {os.path.exists(cache_file)}, writable: {os.access(cache_file, os.W_OK)}")

    def register_routes(self) -> None:
        app = self.app
        spotify = self.spotify_manager
        blacklist = self.blacklist_manager

        @app.route('/')
        def index() -> Response:
            logger.info('Rendering index page. Authenticated: %s', bool(session.get('token_info')))
            try:
                if not session.get('token_info'):
                    return render_template('pages/index.html', url_list=[
                        {"href": url_for('authenticate'), "text": "Authenticate"}
                    ])
                return render_template('pages/index.html', url_list=[
                    {"href": url_for('actions', action_type='generate'), "text": "Build playlist"},
                    {"href": url_for('actions', action_type='image'), "text": "Create new image"},
                    {"href": url_for('actions', action_type='blacklist'), "text": "Select tracks for blacklist"},
                    {"href": url_for('sign_out'), "text": "Sign out"}
                ])
            except Exception as e:
                logger.error(f"Error rendering index page: {e}", exc_info=True)
                return render_template('pages/error.html', message=str(e))

        @app.route('/authenticate')
        def authenticate() -> Response:
            logger.info('User requested authentication.')
            try:
                return spotify.authenticate()
            except Exception as e:
                logger.error(f"Error during authentication: {e}", exc_info=True)
                return render_template('pages/error.html', message=str(e))

        @app.route('/actions')
        @app.route('/actions/<action_type>', methods=['GET', 'POST'])
        @login_required
        def actions(action_type: str = None) -> Response:
            logger.info('Action requested: %s', action_type)
            try:
                if not action_type:
                    logger.warning('No action_type provided.')
                    return render_template('pages/actions_not-set.html')
                playlist_id: str = os.environ.get('PLAYLIST_ID', '')
                if not playlist_id:
                    logger.error('PLAYLIST_ID environment variable is not set.')
                    return render_template('pages/error.html', message="PLAYLIST_ID environment variable is not set.")
                if 'generate' in action_type:
                    logger.info('Building playlist...')
                    return spotify.build_playlist(playlist_id, blacklist.get_tracks())
                if 'image' in action_type:
                    logger.info('Generating cover image...')
                    return spotify.generate_cover_image(playlist_id)
                if action_type == 'blacklist':
                    if request.method == 'POST':
                        add_track: str = request.form.get('add_track', '')
                        delete_track: str = request.form.get('delete_track', '')
                        if add_track:
                            logger.info('Adding track to blacklist: %s', add_track)
                            blacklist.add_track(add_track)
                        if delete_track:
                            logger.info('Deleting track from blacklist: %s', delete_track)
                            blacklist.delete_track(delete_track)
                        return redirect(url_for('actions', action_type='blacklist'))
                    logger.info('Rendering blacklist editor.')
                    tracks: Any = blacklist.get_tracks()
                    return render_template('pages/actions_blacklist.html', data={'tracks': tracks})
                logger.warning('Unknown action_type: %s', action_type)
                return render_template('pages/error.html', message='If you don\'t know what you are doing, do it right!')
            except Exception as e:
                logger.error(f"Error in actions route: {e}", exc_info=True)
                return render_template('pages/error.html', message=str(e))

        @app.route('/sign_out')
        @login_required
        def sign_out() -> Response:
            logger.info('User signed out.')
            try:
                session.clear()
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"Error signing out: {e}", exc_info=True)
                return render_template('pages/error.html', message=str(e))

    def run(self) -> None:
        debug_mode: bool = os.environ.get('FLASK_DEBUG', '0') == '1'
        self.app.run(host="0.0.0.0", port=5000, debug=debug_mode)


if __name__ == '__main__':
    os.makedirs('.cache', exist_ok=True)
    PlaylistGeneratorApp().run()
