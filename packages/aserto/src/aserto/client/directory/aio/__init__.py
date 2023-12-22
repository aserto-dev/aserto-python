import grpc.aio as grpc_aio
from typing import Optional
from aserto.client.directory.channels import channel_credentials, validate_addresses


def build_grpc_channel(address: str, ca_cert_path: str) -> Optional[grpc_aio.Channel]:
    if address == "":
        return None
        
    return grpc_aio.secure_channel(
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

    def get(self, address: str, default_address: str) -> Optional[grpc_aio.Channel]:
        if address != "":
            return self._channels[address]
        if default_address != "":
            return self._channels[default_address]
        
        return None


    async def close(self) -> None:
        for x in self._addresses:
            if x != "" and self._channels[x] is not None:
               await self._channels[x].close()

__all__ = ["Channels"]