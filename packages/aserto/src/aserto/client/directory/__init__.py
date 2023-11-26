from typing import List, Literal, Tuple

from grpc import ChannelCredentials, ssl_channel_credentials


class NotFoundError(Exception):
    pass


Header = Literal["authorization", "aserto-tenant-id", "if-match", "if-none-match"]


def get_metadata(api_key, tenant_id) -> Tuple[Tuple[Header, str], ...]:
    md: Tuple[Tuple[Header, str], ...] = ()
    if api_key:
        md += (("authorization", f"basic {api_key}"),)
    if tenant_id:
        md += (("aserto-tenant-id", tenant_id),)
    return md


def channel_credentials(cert) -> ChannelCredentials:
    if cert:
        with open(cert, "rb") as f:
            return ssl_channel_credentials(f.read())
    else:
        return ssl_channel_credentials()
