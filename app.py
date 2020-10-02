import os

from flask import session, Flask, redirect, jsonify, url_for
from flask_session import Session

from call_it_magic import spotify_functions
from call_it_magic.cache import session_cache_path

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)


@app.route('/')
def index():
    if not session.get('auth_manager') or \
            (session.get('auth_manager') and not session['auth_manager'].get_cached_token()):
        return "<a href='{authenticate}'>Authenticate</a>".format(authenticate=url_for('authenticate'))

    return """
<ul>
    <li><a href="{action_generate}">Generate</a></li>
    <li><a href="{action_image}">Create Image</a></li>
    <li><a href="{sign_out}">Sign out</a></li>
</ul>
    """.format(
        action_generate=url_for('actions', action_type='generate'),
        action_image=url_for('actions', action_type='image'),
        sign_out=url_for('sign_out'))


@app.route('/authenticate')
def authenticate():
    return spotify_functions.authenticate()


@app.route('/actions')
@app.route('/actions/<action_type>')
def actions(action_type=None):
    if not action_type:
        return """
<style>
body {
    margin: 0;
    padding: 0;
}
.container {
    position: relative;
    width: 100%;
    height: 0;
    padding-bottom: 56.25%;
}
iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}
</style>
<div class="container">
<iframe width="560" height="315" src="https://www.youtube.com/embed/jVCy-gDUosA?autoplay=1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>
        """

    if 'generate' in action_type:
        return spotify_functions.build_playlist(os.environ.get('PLAYLIST_ID'))

    if 'image' in action_type:
        return spotify_functions.generate_cover_image(os.environ.get('PLAYLIST_ID'))

    return jsonify('If you don\'t know what you are doing, do it right!')


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


if __name__ == '__main__':
    app.run()
