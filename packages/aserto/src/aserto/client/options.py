import ssl
from typing import Mapping, Optional

from typing_extensions import Literal

from ._typing import assert_unreachable

__all__ = ["AuthorizerOptions"]


ASERTO_HOSTED_AUTHORIZER_URL = "https://authorizer.prod.aserto.com"


ServiceType = Literal["gRPC", "REST"]


class AuthorizerOptions:
    def __init__(
        self,
        *,
        url: str = ASERTO_HOSTED_AUTHORIZER_URL,
        tenant_id: Optional[str] = None,
        api_key: Optional[str] = None,
        cert_file_path: Optional[str] = None,
        service_type: ServiceType = "gRPC",
    ):
        self._tenant_id = tenant_id
        self._api_key = api_key
        self._cert_file_path = cert_file_path
        self._service_type = service_type

        if not url.endswith("aserto.com"):
            self._url = url
        elif service_type == "gRPC":
            self._url = f"{url}:8443"
        elif service_type == "REST":
            self._url = url
        else:
            assert_unreachable(service_type)

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
    def service_type(self) -> ServiceType:
        return self._service_type

    @property
    def cert(self) -> Optional[bytes]:
        if self._cert_file_path is None:
            return None

        with open(self._cert_file_path, "rb") as f:
            return f.read()

    @property
    def ssl_context(self) -> Optional[ssl.SSLContext]:
        return ssl.create_default_context(cafile=self._cert_file_path) if self._cert_file_path else None

    @property
    def auth_headers(self) -> Mapping[str, str]:
        headers = {}
        if self._api_key:
            headers["authorization"] = f"basic {self._api_key}"
        if self._tenant_id:
            headers["aserto-tenant-id"] = self._tenant_id

        return headers
