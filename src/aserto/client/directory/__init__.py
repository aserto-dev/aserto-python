from typing import Literal, Tuple
from aserto.client.directory.channels import Channels

__all__ = ["Channels"]

class NotFoundError(Exception):
    pass

class ConfigError(Exception):
    pass

Header = Literal["authorization", "aserto-tenant-id", "if-match", "if-none-match"]


def get_metadata(api_key, tenant_id) -> Tuple[Tuple[Header, str], ...]:
    md: Tuple[Tuple[Header, str], ...] = ()
    if api_key:
        md += (("authorization", f"basic {api_key}"),)
    if tenant_id:
        md += (("aserto-tenant-id", tenant_id),)
    return md
