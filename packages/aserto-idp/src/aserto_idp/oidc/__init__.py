"""OpenID Connect Identity Provider

This module implements an OpenID Connect provider that can be used with Aserto client libraries.
"""
from typing import Optional

from .discovery import DiscoveryClient
from .errors import AccessTokenError, DiscoveryError
from .provider import IdentityProvider

__all__ = ["AccessTokenError", "DiscoveryError", "identity_provider", "IdentityProvider"]


def identity_provider(
    issuer: str, client_id: str, audience: Optional[str] = None
) -> IdentityProvider:
    """Creates a new OpenID Connect identity provider.

    Args:
        issuer: The OpenID Connect Issuer Identifier of the identity provider as defined in
            https://openid.net/specs/openid-connect-core-1_0.html#IssuerIdentifier.
        client_id: The OAuth 2.0 Client Identifier issued by the authorization server.
            See https://datatracker.ietf.org/doc/html/rfc6749#section-2.2.
        audience: An optional identifier of the audience(s) for which tokens are intended. If omitted, ``client_id``
            is used.

    Returns:
        An ``IdentityProvider`` that can validate JWT tokens created by ``issuer`` and extract subject names.
    """
    discovery = DiscoveryClient(issuer)
    return IdentityProvider(discovery, client_id, audience)
