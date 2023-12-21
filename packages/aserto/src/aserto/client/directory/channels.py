from grpc import secure_channel, Channel, ChannelCredentials, ssl_channel_credentials
from typing import Optional


def validate_addresses(
    address: str,
    reader_address: str,
    writer_address: str,
    importer_address: str,
    exporter_address: str,
    model_address: str) -> None:
    if address == "" and reader_address == "" and writer_address == "" and importer_address == "" and exporter_address == "" and model_address == "":
        raise ValueError("at least one directory service address must be specified")

def channel_credentials(cert) -> ChannelCredentials:
    if cert:
        with open(cert, "rb") as f:
            return ssl_channel_credentials(f.read())
    else:
        return ssl_channel_credentials()
    
def build_grpc_channel(address: str, ca_cert_path: str) -> Optional[Channel]:
    if address == "":
        return None
        
    return secure_channel(
        target=address, 
        credentials=channel_credentials(cert=ca_cert_path),
    )

class Channels:
    def __init__(
            self,
            ca_cert_path: str,
            default_address: str = "",
            reader_address: str = "",
            writer_address: str = "",
            importer_address: str = "",
            exporter_address: str = "",
            model_address: str = "",
        ) -> None:
        validate_addresses(address=default_address, reader_address=reader_address, writer_address=writer_address,
            importer_address=importer_address, exporter_address=exporter_address, model_address=model_address)
        
        self._addresses = [default_address, reader_address, writer_address, importer_address, exporter_address, model_address]
        self._channels = dict()
        for x in self._addresses:
            if x and x not in self._channels:
                self._channels[x] = build_grpc_channel(x, ca_cert_path=ca_cert_path)

    def get(self, address: str, default_address: str) -> Optional[Channel]:
        if address != "":
            return self._channels[address]
        if default_address != "":
            return self._channels[default_address]
        
        return None


    def close(self) -> None:
        for x in self._addresses:
            if x != "" and self._channels[x] is not None:
               self._channels[x].close()