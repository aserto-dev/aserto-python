from typing import Literal, Tuple

from grpc import RpcError, StatusCode

from aserto.client.directory.channels import Channels

__all__ = ["Channels"]


class NotFoundError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


class ConfigError(Exception):
    pass


def get_metadata(api_key, tenant_id) -> Tuple[Tuple[str, str], ...]:
    md: Tuple[Tuple[str, str], ...] = ()
    if api_key:
        md += (("authorization", f"basic {api_key}"),)
    if tenant_id:
        md += (("aserto-tenant-id", tenant_id),)
    return md


def translate_rpc_error(err: RpcError) -> None:
    if err.code() == StatusCode.NOT_FOUND:
        raise NotFoundError(err.details()) from err
    if err.code() == StatusCode.INVALID_ARGUMENT:
        raise InvalidArgumentError(err.details()) from err
