import pytest
import io
import json
from playlist_generator.spotify_functions import SpotifyManager, get_blacklist, edit_blacklist

class DummySpotify:
    def __init__(self, auth=None):
        self.auth = auth
        self.called = {}
        self._tracks = []
        self._playlists = {}
    def playlist_upload_cover_image(self, playlist_id, image):
        self.called['upload'] = (playlist_id, image)
    def playlist_replace_items(self, playlist_id, items):
        self.called['replace'] = (playlist_id, items)
    def current_user_saved_tracks(self, limit=30):
        return {'items': [{'track': {'id': '1'}}]}
    def playlist(self, playlist_id):
        return {'tracks': {'items': [{'track': {'id': '2'}}]}}
    def playlist_add_items(self, playlist_id, items):
        if 'add' not in self.called:
            self.called['add'] = []
        self.called['add'].append((playlist_id, items))

class DummySpotifyOAuth:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._cached_token = {'access_token': 'token'}
    def get_access_token(self, code):
        return {'access_token': 'token'}
    def get_cached_token(self):
        return self._cached_token
    def get_authorize_url(self):
        return '/auth-url'

class DummySession(dict):
    pass

class DummyRequest:
    def __init__(self, method='GET', args=None, json_data=None):
        self.method = method
        self.args = args or {}
        self._json_data = json_data
    def get_json(self, force=False):
        return self._json_data

class DummyRedirect:
    def __init__(self):
        self.called = []
    def __call__(self, url):
        self.called.append(url)
        return url

class DummyUrlFor:
    def __init__(self):
        self.called = []
    def __call__(self, endpoint):
        self.called.append(endpoint)
        return f'/{endpoint}'

class DummyRenderTemplate:
    def __init__(self):
        self.called = []
    def __call__(self, template, **kwargs):
        self.called.append((template, kwargs))
        return 'template'

class DummyConfig:
    SPOTIPY_CLIENT_ID = 'id'
    SPOTIPY_CLIENT_SECRET = 'secret'
    SPOTIPY_REDIRECT_URI = 'uri'
    SPOTIPY_CACHE_PATH = 'cache'

class DummyLogger:
    def __init__(self):
        self.logs = []
    def info(self, msg):
        self.logs.append(('info', msg))
    def warning(self, msg):
        self.logs.append(('warning', msg))
    def error(self, msg):
        self.logs.append(('error', msg))
    def debug(self, msg):
        self.logs.append(('debug', msg))

@pytest.fixture
def manager():
    return SpotifyManager(
        session=DummySession(),
        request=DummyRequest(),
        redirect=DummyRedirect(),
        url_for=DummyUrlFor(),
        render_template=DummyRenderTemplate(),
        spotipy_cls=DummySpotify,
        spotify_oauth_cls=DummySpotifyOAuth,
        config=DummyConfig(),
        logger=DummyLogger()
    )

def test_get_spotify_client_no_token(manager):
    manager.session.clear()
    client = manager.get_spotify_client()
    assert client is None

def test_get_spotify_client_with_token(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    client = manager.get_spotify_client()
    assert isinstance(client, DummySpotify)
    assert client.auth == 'token'

def test_authenticate_new_session(manager):
    manager.session.clear()
    manager.request = DummyRequest(args={})
    result = manager.authenticate()
    assert result == '/index'
    assert 'uuid' in manager.session

def test_authenticate_with_code(manager):
    manager.session.clear()
    manager.request = DummyRequest(args={'code': 'abc'})
    result = manager.authenticate()
    assert result == '/authenticate'
    assert 'token_info' in manager.session

def test_generate_cover_image_success(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    manager.spotipy_cls = DummySpotify
    result = manager.generate_cover_image('playlist_id')
    assert result == '/index'

def test_create_cover_image(manager):
    img = manager._create_cover_image('Test', 12, (100, 100), (0, 0, 0), (255, 255, 255))
    assert img is not None

def test_save_image(manager, tmp_path):
    img = manager._create_cover_image('Test', 12, (100, 100), (0, 0, 0), (255, 255, 255))
    filename = tmp_path / 'file.jpg'
    manager._save_image(img, str(filename))
    assert filename.exists()

def test_image_to_buffer(manager):
    img = manager._create_cover_image('Test', 12, (100, 100), (0, 0, 0), (255, 255, 255))
    buffer = manager._image_to_buffer(img)
    assert isinstance(buffer, io.BytesIO)

def test_build_playlist_success(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    result = manager.build_playlist('playlist_id', ['3'])
    assert result == '/index'

def test_validate_playlist_and_client(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    client = manager._validate_playlist_and_client('playlist_id')
    assert isinstance(client, DummySpotify)
    with pytest.raises(ValueError):
        manager._validate_playlist_and_client('')
    manager.session.clear()
    with pytest.raises(ValueError):
        manager._validate_playlist_and_client('playlist_id')

def test_clear_playlist(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    spotify_client = manager.get_spotify_client()
    manager._clear_playlist('playlist_id', spotify_client)
    assert spotify_client.called['replace'] == ('playlist_id', [])

def test_collect_tracks(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    spotify_client = manager.get_spotify_client()
    tracks = manager._collect_tracks('playlist_id', ['3'], spotify_client)
    assert '1' in tracks and '2' in tracks

def test_add_tracks_to_playlist(manager):
    manager.session['token_info'] = {'access_token': 'token'}
    spotify_client = manager.get_spotify_client()
    tracks = [str(i) for i in range(150)]
    manager._add_tracks_to_playlist('playlist_id', tracks, spotify_client)
    assert len(spotify_client.called['add']) == 2

def test_get_blacklist(tmp_path):
    fake_json = {'tracks': ['1', '2']}
    file_path = tmp_path / 'blacklist.json'
    file_path.write_text(json.dumps(fake_json))
    def open_func(path):
        return open(file_path, 'r')
    result = get_blacklist(open_func=open_func, json_load=json.load)
    assert result == fake_json

def test_edit_blacklist_get():
    def render_template_func(template, **kwargs):
        return 'template'
    def get_blacklist_func():
        return {'tracks': ['1']}
    request_obj = DummyRequest(method='GET')
    result = edit_blacklist(request_obj=request_obj, render_template_func=render_template_func, get_blacklist_func=get_blacklist_func)
    assert result == 'template'

def test_edit_blacklist_post_no_tracks():
    def render_template_func(template, **kwargs):
        return 'template'
    def get_blacklist_func():
        return {'tracks': ['1']}
    request_obj = DummyRequest(method='POST', json_data={})
    result = edit_blacklist(request_obj=request_obj, render_template_func=render_template_func, get_blacklist_func=get_blacklist_func)
    assert result == 'template'

def test_edit_blacklist_post_with_tracks(tmp_path):
    fake_json = {'tracks': ['2']}
    file_path = tmp_path / 'blacklist.json'
    file_path.write_text(json.dumps({'tracks': []}))  # Ensure file exists before opening in r+
    def open_func(path, mode):
        return open(file_path, mode)
    def render_template_func(template, **kwargs):
        return 'template'
    def get_blacklist_func():
        return {'tracks': ['1']}
    request_obj = DummyRequest(method='POST', json_data=fake_json)
    result = edit_blacklist(request_obj=request_obj, render_template_func=render_template_func, get_blacklist_func=get_blacklist_func, open_func=open_func, json_dump=json.dump)
    assert result == fake_json
    assert json.loads(file_path.read_text()) == fake_json
