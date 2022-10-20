from asyncio import TimeoutError
from datetime import datetime, timedelta
from typing import Awaitable, Collection, Dict, Mapping, Optional, Union, cast

from aiohttp import (
    ClientError,
    ClientSession,
    ClientTimeout,
    ServerTimeoutError,
    TCPConnector,
)
from grpc import RpcError, Status
from typing_extensions import Literal

from ..._deadline import monotonic_time_from_deadline
from ..._typing import assert_unreachable
from ...options import AuthorizerOptions
from ...identity import Identity
from ...resource_context import ResourceContext
from ._protocol import AuthorizerClientProtocol, DecisionTree


class AuthorizerRestClient(AuthorizerClientProtocol):
    def __init__(
        self,
        *,
        identity: Identity,
        options: AuthorizerOptions,
    ):
        self._options = options

        self._identity_context_field: Mapping[str, str] = {
            "type": identity.type_field,
        }

        if identity.identity_field is not None:
            self._identity_context_field["identity"] = identity.identity_field

    @property
    def _authorizer_api_url_base(self) -> str:
        return f"{self._options.url}/api/v1/authz"

    @property
    def _headers(self) -> Mapping[str, str]:
        headers = {"Content-Type": "application/json", **self._options.auth_headers}

        return headers

    def _authorizer_session(self, deadline: Optional[Union[datetime, timedelta]]) -> ClientSession:
        connector = None
        if self._options.ssl_context is not None:
            connector = TCPConnector(ssl_context=self._options.ssl_context)

        return ClientSession(
            connector=connector,
            timeout=ClientTimeout(
                total=(monotonic_time_from_deadline(deadline) if deadline is not None else None),
            ),
        )

    @staticmethod
    def _policy_path_separator_field(
        policy_path_separator: Literal["DOT", "SLASH"],
    ) -> Literal["PATH_SEPARATOR_DOT", "PATH_SEPARATOR_SLASH"]:
        if policy_path_separator == "DOT":
            return "PATH_SEPARATOR_DOT"
        elif policy_path_separator == "SLASH":
            return "PATH_SEPARATOR_SLASH"
        else:
            assert_unreachable(policy_path_separator)

    async def decision_tree(
        self,
        *,
        policy_path_root: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str] = None,
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        policy_path_separator: Optional[Literal["DOT", "SLASH"]] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> DecisionTree:
        options = {}
        if policy_path_separator is not None:
            options["pathSeparator"] = self._policy_path_separator_field(policy_path_separator)

        body = {
            "policyContext": {
                "path": policy_path_root,
                "decisions": tuple(decisions),
            },
            "identityContext": self._identity_context_field,
            "resourceContext": resource_context,
            "options": options,
            "policyInstance": {
                "name": policy_instance_name,
                "instanceLabel": policy_instance_label,
            },
        }

        async with self._authorizer_session(deadline=deadline) as session:
            url = f"{self._authorizer_api_url_base}/decisiontree"

            try:
                async with session.post(url, headers=self._headers, json=body) as response:
                    response_json = await cast(Awaitable[object], response.json())
            except ServerTimeoutError as error:
                # ServerTimeoutError is a TimeoutError but we only want to expose the latter
                raise TimeoutError(*error.args)  # type: ignore[misc]
            except ClientError as error:
                raise ConnectionError(*error.args) from error  # type: ignore[misc]

        return self._validate_decision_tree_response(response_json)

    @staticmethod
    def _raise_if_server_error(response: Mapping[object, object]) -> None:
        if response.keys() == {"code", "message", "details"}:
            raise RpcError(
                Status(response["code"]),
                (str(response["message"]) if response["message"] is not None else None),
                response["details"],
            )

    @classmethod
    def _validate_decision_tree_response(cls, response: object) -> DecisionTree:
        error = TypeError("Received unexpected response data", response)

        if not isinstance(response, dict):
            raise error

        if "path" not in response:
            cls._raise_if_server_error(response)
            raise error

        tree = response["path"]

        if not isinstance(tree, dict):
            raise error

        for path, decisions in tree.items():
            if not isinstance(path, str):
                raise error

            if not isinstance(decisions, dict):
                raise error

            for name, decision in decisions.items():
                if not isinstance(name, str):
                    raise error

                if not isinstance(decision, bool):
                    raise error

        return cast(DecisionTree, tree)

    async def decisions(
        self,
        *,
        policy_path: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str] = None,
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        body = {
            "policyContext": {
                "path": policy_path,
                "decisions": list(decisions),
            },
            "identityContext": self._identity_context_field,
            "resourceContext": resource_context,
            "policyInstance": {
                "name": policy_instance_name,
                "instanceLabel": policy_instance_label,
            },
        }

        async with self._authorizer_session(deadline=deadline) as session:
            url = f"{self._authorizer_api_url_base}/is"

            try:
                async with session.post(url, headers=self._headers, json=body) as response:
                    response_json = await cast(Awaitable[object], response.json())
            except ServerTimeoutError as error:
                # ServerTimeoutError is a TimeoutError but we only want to expose the latter
                raise TimeoutError(*error.args)  # type: ignore[misc]
            except ClientError as error:
                raise ConnectionError(*error.args) from error  # type: ignore[misc]

        return self._validate_decision_response(response_json)

    @classmethod
    def _validate_decision_response(cls, response: object) -> Dict[str, bool]:
        error = TypeError("Received unexpected response data")

        if not isinstance(response, dict):
            raise error

        if "decisions" not in response:
            cls._raise_if_server_error(response)
            raise error

        decisions = response["decisions"]

        if not isinstance(decisions, list):
            raise error

        result = {}
        for decision_json in decisions:
            if not isinstance(decision_json, dict):
                raise error

            if "decision" not in decision_json:
                raise error

            if not isinstance(decision_json["decision"], str):
                raise error

            if not isinstance(decision_json["is"], bool):
                raise error

            result[decision_json["decision"]] = decision_json["is"]

        return result
