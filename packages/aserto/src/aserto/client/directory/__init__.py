from typing import List, Literal, Tuple, Any

from grpc import ChannelCredentials, ssl_channel_credentials, secure_channel


class NotFoundError(Exception):
    pass

class InvalidArgument(Exception):
    pass

class NilClient(Exception):
    pass

Header = Literal["authorization", "aserto-tenant-id", "if-match", "if-none-match"]

def validate_addresses(
    address: str,
    reader_address: str,
    writer_address: str,
    importer_address: str,
    exporter_address: str,
    model_address: str) -> Any:
    if address == "" and reader_address == "" and writer_address == "" and importer_address == "" and exporter_address == "" and model_address == "":
        return InvalidArgument
        
    return None


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
