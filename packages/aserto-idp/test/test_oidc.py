import pytest

from aserto_idp.oidc import AccessTokenError, identity_provider

ISSUER = "issuer"
CLIENT_ID = "client_id"


@pytest.fixture
def idp():
    return identity_provider(issuer=ISSUER, client_id=CLIENT_ID)


def test_create(idp):
    assert idp.discovery_client.issuer == f"https://{ISSUER}"
    assert idp.client_id == idp.audience == CLIENT_ID


def test_parse_empty_header(idp):
    for token in ("", " ", "\t", "   "):
        with pytest.raises(AccessTokenError, match="Authorization header missing"):
            idp._parse_authorization_header(token)


def test_not_bearer_token(idp):
    for token in ("basic xyz", "xyz"):
        with pytest.raises(AccessTokenError, match="Authorization header must start with 'Bearer'"):
            idp._parse_authorization_header(token)


def test_empty_bearer(idp):
    with pytest.raises(AccessTokenError, match="Bearer token not found"):
        idp._parse_authorization_header("bearer ")


def test_too_many_header_parts(idp):
    with pytest.raises(AccessTokenError, match="Authorization header must be a valid Bearer token"):
        idp._parse_authorization_header("bearer xyz 123")
