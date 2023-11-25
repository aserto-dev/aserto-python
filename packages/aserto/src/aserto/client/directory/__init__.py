from typing import Tuple

from grpc import ChannelCredentials, ssl_channel_credentials


class NotFoundError(Exception):
    pass


def get_metadata(api_key, tenant_id) -> Tuple[Tuple[str, str]]:
    md = ()
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
