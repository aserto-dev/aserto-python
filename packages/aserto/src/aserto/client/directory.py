from typing import Tuple

import grpc

from aserto.directory.reader.v2 import ReaderStub
from aserto.directory.writer.v2 import WriterStub
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.exporter.v2 import ExporterStub

class Directory:
    def __init__(self, *, address: str, api_key: str, tenant_id: str, ca_cert: str) -> None:
        self._config = { "address": address, "api_key": api_key, "tenant_id": tenant_id, "cert": ca_cert }
        self._channel = grpc.secure_channel(target=self._config["address"], credentials=self._channel_credentials())
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    def _metadata(self) -> Tuple:
        md = ()
        if self._config["api_key"]:
            md += (("authorization", f"basic {self._config['api_key']}"),)
        if self._config["tenant_id"]:
            md += (("aserto-tenant-id", self._config["tenant_id"]),)
        return md

    def _channel_credentials(self) -> grpc.ChannelCredentials:
        if self._config["cert"]:
            with open(self._config["cert"], "rb") as f:
                return grpc.ssl_channel_credentials(f.read())
        else:
            return grpc.ssl_channel_credentials()
