import os
import time

# Generate a real Fernet key and set ALL env vars BEFORE any app imports
from cryptography.fernet import Fernet

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ.setdefault("SPOTIFY_CLIENT_ID", "test_client_id")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:5000/callback")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from playlist_generator.database import Base


@pytest.fixture(autouse=True)
def _reset_encryption_cache():
    """Reset the cached Fernet instance between tests."""
    import playlist_generator.encryption as enc
    enc._fernet = None
    yield
    enc._fernet = None


@pytest_asyncio.fixture
async def db_session():
    """Provide an async SQLAlchemy session backed by an in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession):
    """Create and return a sample user in the test database."""
    from playlist_generator.encryption import encrypt
    from playlist_generator.models import User

    user = User(
        spotify_user_id="spotify_test_user",
        display_name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.jpg",
        access_token=encrypt("fake_access_token"),
        refresh_token=encrypt("fake_refresh_token"),
        token_expires_at=time.time() + 3600,
        token_scopes="playlist-read-private user-library-read",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
