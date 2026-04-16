from playlist_generator.encryption import encrypt, decrypt


def test_encrypt_decrypt_round_trip():
    original = "my_secret_spotify_token_abc123"
    encrypted = encrypt(original)
    assert encrypted != original
    assert decrypt(encrypted) == original


def test_encrypt_produces_different_ciphertext():
    """Fernet includes a timestamp, so encrypting the same value twice yields different ciphertext."""
    value = "same_value"
    assert encrypt(value) != encrypt(value)


def test_decrypt_returns_original():
    token = "eyJhbGciOiJIUzI1NiJ9.test_payload.signature"
    encrypted = encrypt(token)
    assert decrypt(encrypted) == token


def test_empty_string():
    encrypted = encrypt("")
    assert decrypt(encrypted) == ""
