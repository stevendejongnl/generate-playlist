import os
from dotenv import load_dotenv
from typing import Optional


class Config:
    basedir: str = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

    SPOTIPY_CLIENT_ID: Optional[str] = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET: Optional[str] = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI: Optional[str] = os.getenv('SPOTIPY_REDIRECT_URI')
    SPOTIPY_CACHE_PATH: str = os.getenv('SPOTIPY_CACHE_PATH', '.cache')
    CSRF_ENABLED: bool = True
    SECRET_KEY: str = 'spotify-likes-to-playlist-yo'
