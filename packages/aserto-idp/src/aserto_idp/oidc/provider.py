from typing import Optional

from jose import jwt

from aserto_idp.oidc.discovery import DiscoveryClient
from aserto_idp.oidc.errors import AccessTokenError


class IdentityProvider:
    def __init__(
        self,
        discovery_client: DiscoveryClient,
        client_id: str,
        audience: Optional[str] = None,
    ):
        self.discovery_client: DiscoveryClient = discovery_client
        self.client_id: str = client_id
        self.audience: str = audience or client_id

    async def subject_from_jwt_auth_header(
        self,
        authorization_header: str,
        access_token: Optional[str] = None,
    ) -> str:
        token = self._parse_authorization_header(authorization_header)
        key_id = get_key_id(token)
        key = await self.discovery_client.find_signing_key(key_id)

        options = {"verify_at_hash": access_token is not None}
        claims = jwt.decode(token, key, options=options, audience=self.audience)
        if "azp" in claims and claims["azp"] != self.client_id:
            raise AccessTokenError(f"'azp' claim '{claims['azp']}' does not match client ID")

        if not isinstance(claims["sub"], str):
            raise AccessTokenError(f"'sub' claim '{claims['sub']}'is not a valid identity")

        return claims["sub"]

    @staticmethod
    def _parse_authorization_header(header: str) -> str:
        parts = header.split()
        if not parts:
            raise AccessTokenError("Authorization header missing")
        elif parts[0].lower() != "bearer":
            raise AccessTokenError("Authorization header must start with 'Bearer'")
        elif len(parts) == 1:
            raise AccessTokenError("Bearer token not found")
        elif len(parts) > 2:
            raise AccessTokenError("Authorization header must be a valid Bearer token")

        _, token = parts
        return token


def get_key_id(token: str) -> str:
    kid = jwt.get_unverified_header(token).get("kid")
    if not kid:
        raise AccessTokenError("Bearer token does not have 'kid' claim")

    return kid  # type: ignore
