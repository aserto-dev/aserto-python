"""OpenID Connect Discovery

This module implments a subset of the OpenID Connect Discovery 1.0 specification
(https://openid.net/specs/openid-connect-discovery-1_0.html).

It provides the means to discover and retrieve an OpenID Connect issuer's keyset and find the signing key for
a specified JWT.
"""
import os.path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

from aiohttp import ClientSession

from aserto_idp.oidc.errors import DiscoveryError

OidcConfig = Dict[str, Union[str, List[str]]]
Key = Dict[str, str]
KeySet = Dict[str, List[Key]]


class DiscoveryClient:
    """Client implementation of the OpenID Connect Discovery 1.0 specification.

    Args:
        issuer: The OpenID Connect Issuer Identifier of the server issuing tokens.
    """

    def __init__(self, issuer: str):
        self.issuer = issuer_url(issuer)
        self.discovery_url = os.path.join(self.issuer, ".well-known/openid-configuration")
        self._keyset: Optional[KeySet] = None

    async def find_signing_key(self, key_id: str) -> Key:
        """Find and return the signing key for the specified key ID.

        Args:
            key_id: The ID of the key used by the OIDC issuer to sign a JWT being verified. Key IDs are extracted from
                the "kid" JOSE header of a JWT
                (https://datatracker.ietf.org/doc/html/draft-ietf-jose-json-web-signature#section-4.1.4).

        Returns:
            A ``dict``
        """
        for _ in range(2):
            # If we can't find the key ID in the issuer's keyset, clear the cache and try again.
            keyset = await self.keyset()
            keys = keyset.get("keys")
            if not keys:
                raise DiscoveryError("Keyset missing required field 'keys': {keys}")

            for key in keys:
                if key["kid"] == key_id:
                    return key

            self.clear_keyset_cache()

        raise DiscoveryError(f"RSA public key with ID '{key_id}' was not found.")

    async def keyset(self) -> KeySet:
        """Downloads the OIDC issuer's signing key-set.

        The key-set URL is retrieved from the "jwks_uri" field in the issuer's OIDC configuration
        (https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata).

        Returns:
            A ``dict`` containing the downloaded JOSE key-set.
        """
        if not self._keyset:
            config = await self.config()
            keyset_url = config.get("jwks_uri")
            if not keyset_url:
                raise DiscoveryError("Issuer openid-configuration missing 'jwks_uri'")

            self._keyset = await get_json(keyset_url)  # type: ignore

        return self._keyset

    async def config(self) -> OidcConfig:
        return await get_json(self.discovery_url)

    def clear_keyset_cache(self) -> None:
        self._keyset = None


def issuer_url(issuer: str) -> str:
    url = urlparse(issuer)
    if not url.scheme:
        # issuer is not a full URL
        return f"https://{issuer}"
    elif url.scheme != "https":
        raise ValueError("OIDC issuer MUST use the 'https' scheme.")
    return issuer


async def get_json(url: str) -> dict:  # type: ignore
    async with ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
