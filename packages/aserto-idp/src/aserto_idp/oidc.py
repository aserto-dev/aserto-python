from aiohttp import ClientSession
from jose import jwk, jwt

__all__ = ["generate_oauth_subject_from_auth_header", "AccessTokenError"]


class AccessTokenError(Exception):
    pass


async def generate_oauth_subject_from_auth_header(
    *,
    authorization_header: str,
    domain: str,
    client_id: str,
    audience: str,
) -> str:
    parts = authorization_header.split()
    if not parts:
        raise AccessTokenError("Authorization header missing")
    elif parts[0].lower() != "bearer":
        raise AccessTokenError("Authorization header must start with 'Bearer'")
    elif len(parts) == 1:
        raise AccessTokenError("Bearer token not found")
    elif len(parts) > 2:
        raise AccessTokenError("Authorization header must be a valid Bearer token")

    _, token = parts

    header = jwt.get_unverified_header(token)
    if "kid" not in header:
        raise AccessTokenError("Bearer token does not have 'kid' claim")

    kid = header["kid"]

    async with ClientSession() as session:
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        async with session.get(jwks_url) as response:
            jwks = await response.json()

    for key in jwks["keys"]:
        if key["kid"] == kid:
            rsa_key = jwk.construct(key).to_pem()
            break
    else:
        raise AccessTokenError(f"RSA public key with ID '{kid}' was not found.")

    payload = jwt.decode(token, rsa_key, algorithms=["RS256"], audience=audience)
    if payload["azp"] != client_id:
        raise AccessTokenError(f"'azp' claim '{payload['azp']}' does not match Auth0 client ID")

    if not isinstance(payload["sub"], str):
        raise AccessTokenError(f"'sub' claim '{payload['sub']}'is not a valid identity")

    return payload["sub"]
