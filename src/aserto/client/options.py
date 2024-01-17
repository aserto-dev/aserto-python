import ssl
from typing import Mapping, Optional

__all__ = ["AuthorizerOptions"]


ASERTO_HOSTED_AUTHORIZER_URL = "authorizer.prod.aserto.com:8443"


class AuthorizerOptions:
    def __init__(
        self,
        *,
        url: str = ASERTO_HOSTED_AUTHORIZER_URL,
        tenant_id: Optional[str] = None,
        api_key: Optional[str] = None,
        cert_file_path: Optional[str] = None,
    ):
        self._tenant_id = tenant_id
        self._api_key = api_key
        self._cert_file_path = cert_file_path
        self._url = url

    @property
    def url(self) -> str:
        return self._url

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id

    @property
    def cert(self) -> Optional[bytes]:
        if self._cert_file_path is None:
            return None

        with open(self._cert_file_path, "rb") as f:
            return f.read()

    @property
    def ssl_context(self) -> Optional[ssl.SSLContext]:
        return (
            ssl.create_default_context(cafile=self._cert_file_path)
            if self._cert_file_path
            else None
        )

    @property
    def auth_headers(self) -> Mapping[str, str]:
        headers = {}
        if self._api_key:
            headers["authorization"] = f"basic {self._api_key}"
        if self._tenant_id:
            headers["aserto-tenant-id"] = self._tenant_id

        return headers
