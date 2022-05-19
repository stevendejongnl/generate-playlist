from flask import Blueprint, session, render_template, url_for

home_blueprint = Blueprint('home', __name__)


@home_blueprint.route('/')
def index():
    if not session.get('auth_manager') or \
            (session.get('auth_manager') and not session['auth_manager'].get_cached_token()):
        return render_template('pages/index.html', url_list=[
            {
                "href": url_for('spotify.authenticate'),
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
            "href": url_for('spotify.logout'),
            "text": "Logout"
        }
    ])
