from typing import Tuple

import grpc

from aserto.directory.reader.v2 import ReaderStub
from aserto.directory.writer.v2 import WriterStub

class Directory:
    def __init__(self, config) -> None:
        self._api_key = config["api_key"]
        self._tenant_id = config["tenant_id"]
        self._address = config["address"]
        self._cert = config["cert"]
        self._channel = grpc.secure_channel(target=self._address, credentials=self._channel_credentials())
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)

    def _metadata(self) -> Tuple:
        md = ()
        if self._api_key:
            md += (("authorization", f"basic {self._api_key}"),)
        if self._tenant_id:
            md += (("aserto-tenant-id", self._tenant_id),)
        return md

    def _channel_credentials(self) -> grpc.ChannelCredentials:
        if self._cert:
            with open(self._cert, "rb") as f:
                return grpc.ssl_channel_credentials(f.read())
        else:
            return grpc.ssl_channel_credentials()
        
    def reader(self):
        with grpc.secure_channel(target=self._address, credentials=self._channel_credentials()) as channel:
            reader = ReaderStub(channel)
            return reader
    
    def writer(self):
        with grpc.secure_channel(target=self._address, credentials=self._channel_credentials()) as channel:
            writer = WriterStub(channel)
            return writer
