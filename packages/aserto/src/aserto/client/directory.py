from typing import Tuple

import grpc

from aserto.directory.reader.v2 import ReaderStub
from aserto.directory.writer.v2 import WriterStub

class Directory:
    def __init__(self, config) -> None:
        self._config = config
        self._channel = grpc.secure_channel(target=self._config["address"], credentials=self._channel_credentials())
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)

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
