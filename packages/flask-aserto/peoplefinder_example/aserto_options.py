import os
from typing import Awaitable, Callable

from aserto import HostedAuthorizer, Identity
from aserto_idp.oidc import AccessTokenError, identity_provider as oidc_idp
from flask import request
from typing_extensions import TypedDict

ASERTO_AUTHORIZER_URL = "https://authorizer.prod.aserto.com"


__all__ = ["AsertoMiddlewareOptions", "load_aserto_options_from_environment"]


class AsertoMiddlewareOptions(TypedDict):
    authorizer: HostedAuthorizer
    policy_id: str
    policy_path_root: str
    identity_provider: Callable[[], Awaitable[Identity]]


def load_aserto_options_from_environment() -> AsertoMiddlewareOptions:
    missing_variables = []

    tenant_id = os.getenv("TENANT_ID", "")
    if not tenant_id:
        missing_variables.append("TENANT_ID")

    authorizer_api_key = os.getenv("AUTHORIZER_API_KEY", "")
    authorizer_service_url = os.getenv("AUTHORIZER_SERVICE_URL", ASERTO_AUTHORIZER_URL)

    if not authorizer_api_key:
        missing_variables.append("AUTHORIZER_API_KEY")

    oidc_issuer = os.getenv("OIDC_ISSUER", "")
    if not oidc_issuer:
        missing_variables.append("OIDC_ISSUER")

    oidc_client_id = os.getenv("OIDC_CLIENT_ID", "")
    if not oidc_client_id:
        missing_variables.append("OIDC_CLIENT_ID")

    policy_id = os.getenv("POLICY_ID", "")
    if not policy_id:
        missing_variables.append("POLICY_ID")

    policy_path_root = os.getenv("POLICY_PATH_ROOT", "")
    if not policy_path_root:
        missing_variables.append("POLICY_PATH_ROOT")

    if missing_variables:
        raise EnvironmentError(
            f"environment variables not set: {', '.join(missing_variables)}",
        )

    authorizer = HostedAuthorizer(
        api_key=authorizer_api_key,
        tenant_id=tenant_id,
        url=authorizer_service_url,
        service_type="gRPC",
    )

    idp = oidc_idp(issuer=oidc_issuer, client_id=oidc_client_id)

    async def identity_provider() -> Identity:
        authorization_header = request.headers.get("Authorization")

        if authorization_header is None:
            return Identity(type="NONE")

        try:
            identity = await idp.subject_from_jwt_auth_header(authorization_header)
        except AccessTokenError:
            return Identity(type="NONE")

        return Identity(type="SUBJECT", subject=identity)

    return AsertoMiddlewareOptions(
        authorizer=authorizer,
        policy_id=policy_id,
        policy_path_root=policy_path_root,
        identity_provider=identity_provider,
    )
