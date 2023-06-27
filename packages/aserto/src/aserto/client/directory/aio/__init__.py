from typing import Tuple

import grpc
from aserto.directory.exporter.v2 import ExporterStub
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.reader.v2 import ReaderStub
from aserto.directory.writer.v2 import WriterStub


class DirectoryAsync:
    def __init__(self):
        pass

    @classmethod
    async def create(cls, *, address: str, api_key: str, tenant_id: str, ca_cert: str):
        self = cls()
        self._channel = grpc.aio.secure_channel(
            target=address, credentials=self._channel_credentials(cert=ca_cert)
        )
        self._metadata = self._get_metadata(api_key=api_key, tenant_id=tenant_id)
        self.reader = await ReaderStub(self._channel)
        self.writer = await WriterStub(self._channel)
        self.importer = await ImporterStub(self._channel)
        self.exporter = await ExporterStub(self._channel)
        return self

    async def close_channel(self) -> None:
        """Closes the gRPC channel"""

        await self._channel.close()

    def _get_metadata(self, api_key, tenant_id) -> Tuple:
        md = ()
        if api_key:
            md += (("authorization", f"basic {api_key}"),)
        if tenant_id:
            md += (("aserto-tenant-id", tenant_id),)
        return md

    def _channel_credentials(self, cert) -> grpc.ChannelCredentials:
        if cert:
            with open(cert, "rb") as f:
                return grpc.ssl_channel_credentials(f.read())
        else:
            return grpc.ssl_channel_credentials()


# async def main():
#     config = {
#         "api_key": "api_key",
#         "tenant_id": "tenant_id",
#         "address": "address",
#         "ca_cert": "cert",
#     }
#     ds = await DirectoryAsync.create(config)
