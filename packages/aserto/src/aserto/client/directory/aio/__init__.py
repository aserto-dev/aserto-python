from typing import Optional, Tuple

import grpc
from aserto.directory.common.v2 import ObjectTypeIdentifier, PaginationRequest
from aserto.directory.exporter.v2 import ExporterStub
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.reader.v2 import GetObjectsRequest, GetObjectsResponse, ReaderStub
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
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)
        return self

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
#         "api_key": api_key,
#         "tenant_id": tenant_id,
#         "address": address,
#         "ca_cert": cert,
#     }
#     ds = await DirectoryAsync.create(**config)
#     response = await ds.get_objects(object_type="user", page=PaginationRequest(size=10))
#     print(response)


# asyncio.run(main())
