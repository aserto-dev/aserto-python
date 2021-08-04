import re
from typing import Mapping

import aiohttp

__all__ = ["PeopleClient"]


class PeopleClient:
    """TODO: Use the official Aserto API client, when it exists ;)"""

    def __init__(
        self,
        *,
        tenant_id: str,
        authorizer_api_key: str,
        authorizer_url: str,
    ):
        self._tenant_id = tenant_id
        self._authorizer_api_key = authorizer_api_key
        self._authorizer_url = re.sub(":8443$", "", authorizer_url)

    @property
    def _headers(self) -> Mapping[str, str]:
        return {
            "Content-Type": "application/json",
            "Aserto-Tenant-Id": self._tenant_id,
            "Authorization": f"Basic {self._authorizer_api_key}",
        }

    async def list_people(self) -> object:
        url = f"{self._authorizer_url}/api/v1/dir/users?page.size=-1&fields.mask=id,display_name,picture,email"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers) as response:
                response_json = await response.json()

        return response_json["results"]

    async def get_person(self, id: str) -> object:
        url = f"{self._authorizer_url}/api/v1/dir/users/{id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers) as response:
                response_json = await response.json()

        return response_json["result"]

    async def update_person(self, id: str, properties: object) -> object:
        url = f"{self._authorizer_url}/api/v1/dir/users/{id}/attributes/properties"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=properties, headers=self._headers) as response:
                return await response.json()
