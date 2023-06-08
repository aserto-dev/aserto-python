import os
from dataclasses import dataclass
from typing import Awaitable, Callable

from aserto.client import AuthorizerOptions, Identity
from aserto_idp.oidc import AccessTokenError, identity_provider as oidc_idp
from flask import request
from typing_extensions import TypedDict

ASERTO_AUTHORIZER_URL = "https://authorizer.prod.aserto.com"


__all__ = ["AsertoMiddlewareOptions", "load_aserto_options_from_environment"]


@dataclass(frozen=True)
class AsertoMiddlewareOptions:
    tenant_id: str
    authorizer_options: AuthorizerOptions
    policy_name: str
    policy_path_root: str
    directory_url: str
    directory_api_key: str
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

    policy_name = os.getenv("POLICY_NAME", "")
    if not policy_name:
        missing_variables.append("POLICY_NAME")

    policy_path_root = os.getenv("POLICY_PATH_ROOT", "")
    if not policy_path_root:
        missing_variables.append("POLICY_PATH_ROOT")

    directory_url = os.getenv("DIRECTORY_SERVICE_URL", "")
    if not directory_url:
        missing_variables.append("DIRECTORY_SERVICE_URL")

    directory_api_key = os.getenv("DIRECTORY_API_KEY", "")
    if not directory_api_key:
        missing_variables.append("DIRECTORY_API_KEY")

    authorizer_cert_path = os.getenv("DIRECTORY_CERT_PATH", "")

    if missing_variables:
        raise EnvironmentError(
            f"environment variables not set: {', '.join(missing_variables)}",
        )

    authorizer_options = AuthorizerOptions(
        url=authorizer_service_url,
        cert_file_path=authorizer_cert_path,
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
        tenant_id=tenant_id,
        authorizer_options=authorizer_options,
        policy_name=policy_name,
        policy_path_root=policy_path_root,
        directory_url=directory_url,
        directory_api_key=directory_api_key,
        identity_provider=identity_provider,
    )
