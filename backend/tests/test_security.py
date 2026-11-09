from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret12345")
    assert hashed != "secret12345"
    assert verify_password("secret12345", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_contains_claims() -> None:
    token, jti, _expires = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        role="admin",
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert payload["jti"] == jti
