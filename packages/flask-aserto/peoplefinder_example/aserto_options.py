import os
from typing import Awaitable, Callable

from aserto import HostedAuthorizer, Identity
from aserto_idp.auth0 import AccessTokenError, provide_identity
from flask import request
from typing_extensions import TypedDict

ASERTO_AUTHORIZER_URL = "https://authorizer.prod.aserto.com"


__all__ = ["AsertoMiddlewareOptions", "load_aserto_options_from_environment"]


class AsertoMiddlewareOptions(TypedDict):
    tenant_id: str
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

    auth0_domain = os.getenv("REACT_APP_DOMAIN", "")
    if not auth0_domain:
        missing_variables.append("REACT_APP_DOMAIN")

    auth0_client_id = os.getenv("REACT_APP_CLIENT_ID", "")
    if not auth0_client_id:
        missing_variables.append("REACT_APP_CLIENT_ID")

    auth0_audience = os.getenv("REACT_APP_AUDIENCE", "")
    if not auth0_audience:
        missing_variables.append("REACT_APP_AUDIENCE")

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
        url=authorizer_service_url,
        service_type="gRPC",
    )

    async def identity_provider() -> Identity:
        authorization_header = request.headers.get("Authorization")

        if authorization_header is None:
            return Identity(type="NONE")

        try:
            identity = await provide_identity(
                authorization_header=authorization_header,
                domain=auth0_domain,
                client_id=auth0_client_id,
                audience=auth0_audience,
            )
        except AccessTokenError:
            return Identity(type="NONE")

        return Identity(type="SUBJECT", subject=identity)

    return dict(
        tenant_id=tenant_id,
        authorizer=authorizer,
        policy_id=policy_id,
        policy_path_root=policy_path_root,
        identity_provider=identity_provider,
    )
