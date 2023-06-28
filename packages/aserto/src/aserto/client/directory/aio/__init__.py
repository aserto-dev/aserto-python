from typing import Optional, Tuple

import grpc.aio as grpc
from aserto.directory.common.v2 import ObjectTypeIdentifier, PaginationRequest
from aserto.directory.exporter.v2 import ExporterStub
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.reader.v2 import GetObjectsRequest, GetObjectsResponse, ReaderStub
from aserto.directory.writer.v2 import WriterStub
from grpc import Channel, ChannelCredentials, ssl_channel_credentials


class Directory:
    def __init__(self, channel: grpc.Channel, api_key: str, tenant_id: str) -> None:
        self._channel = channel
        self._metadata = self._get_metadata(api_key=api_key, tenant_id=tenant_id)
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    @classmethod
    async def connect(cls, *, address: str, api_key: str, tenant_id: str, ca_cert: str):
        channel = grpc.secure_channel(
            target=address, credentials=cls._channel_credentials(cert=ca_cert)
        )
        return Directory(channel, api_key, tenant_id)

    async def get_objects(
        self, object_type: Optional[str] = None, page: Optional[PaginationRequest] = None
    ) -> GetObjectsResponse:
        """Retrieve a page of directory objects by object type and page size.
        Returns a list of directory objects and a token for the next page if it exists.

        Parameters
        ----
        object_type : str
            a directory object type
        page : PaginationRequest(size: int, token: str)
            paging information — the size of the page, and the pagination
            start token

        Returns
        ----
        GetObjectsResponse
            results : list(Object)
                list of directory objects
            page : PaginationResponse(result_size: int, next_token: str)
                retrieved page information — the size of the page,
                and the next page's token
        """

        response = await self.reader.GetObjects(
            GetObjectsRequest(param=ObjectTypeIdentifier(name=object_type), page=page),
            metadata=self._metadata,
        )
        return response

    async def close(self) -> None:
        """Closes the gRPC channel"""

        await self._channel.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.close()

    @staticmethod
    def _get_metadata(api_key, tenant_id) -> Tuple:
        md = ()
        if api_key:
            md += (("authorization", f"basic {api_key}"),)
        if tenant_id:
            md += (("aserto-tenant-id", tenant_id),)
        return md

    @staticmethod
    def _channel_credentials(cert) -> ChannelCredentials:
        if cert:
            with open(cert, "rb") as f:
                return ssl_channel_credentials(f.read())
        else:
            return ssl_channel_credentials()
