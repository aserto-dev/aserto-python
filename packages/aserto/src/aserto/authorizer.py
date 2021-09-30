import ssl
from abc import ABCMeta, abstractmethod
from typing import Mapping, Optional

from typing_extensions import Literal

from ._typing import assert_unreachable

__all__ = ["Authorizer", "EdgeAuthorizer", "HostedAuthorizer"]


ASERTO_HOSTED_AUTHORIZER_URL = "https://authorizer.prod.aserto.com"


ServiceType = Literal["gRPC", "REST"]


class Authorizer(metaclass=ABCMeta):
    @property
    @abstractmethod
    def url(self) -> str:
        ...

    @property
    @abstractmethod
    def service_type(self) -> ServiceType:
        ...

    @property
    def ssl_context(self) -> Optional[ssl.SSLContext]:
        return None

    @property
    def auth_headers(self) -> Mapping[str, str]:
        return {}


class HostedAuthorizer(Authorizer):
    def __init__(
        self,
        *,
        api_key: str,
        tenant_id: str,
        url: str = ASERTO_HOSTED_AUTHORIZER_URL,
        service_type: ServiceType,
    ):
        self._api_key = api_key
        self._tenant_id = tenant_id
        self._service_type = service_type

        if url != ASERTO_HOSTED_AUTHORIZER_URL:
            self._url = url
        elif service_type == "gRPC":
            self._url = ASERTO_HOSTED_AUTHORIZER_URL + ":8443"
        elif service_type == "REST":
            self._url = ASERTO_HOSTED_AUTHORIZER_URL
        else:
            assert_unreachable(service_type)

    @property
    def service_type(self) -> ServiceType:
        return self._service_type

    @property
    def url(self) -> str:
        return self._url

    @property
    def auth_headers(self) -> Mapping[str, str]:
        return {
            "authorization": f"basic {self._api_key}",
            "aserto-tenant-id": self._tenant_id,
        }

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def tenant_id(self) -> str:
        return self._tenant_id


class EdgeAuthorizer(Authorizer):
    def __init__(
        self,
        *,
        url: str,
        cert_file_path: Optional[str],
        service_type: ServiceType,
    ):
        self._url = url
        self._cert_file_path = cert_file_path
        self._service_type = service_type

    @property
    def service_type(self) -> ServiceType:
        return self._service_type

    @property
    def url(self) -> str:
        return self._url

    @property
    def ssl_context(self) -> Optional[ssl.SSLContext]:
        return ssl.create_default_context(cafile=self._cert_file_path)

    @property
    def cert_file_path(self) -> Optional[str]:
        return self._cert_file_path
