from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/playlist_generator.db"
    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str = "change-me-generate-with-fernet"

    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = "http://localhost:5000/callback"
    SPOTIFY_SCOPES: str = (
        "ugc-image-upload "
        "playlist-read-collaborative "
        "playlist-modify-public "
        "playlist-read-private "
        "playlist-modify-private "
        "user-library-read"
    )

    # Optional: OpenAI for enhanced features (cover art, smart discovery, name generation)
    OPENAI_API_KEY: str = ""


settings = Settings()
