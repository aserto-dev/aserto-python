from asyncio import gather
from dataclasses import dataclass
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union, cast, overload

from aserto import Identity, ResourceContext
from aserto.api.authorizer import AuthorizerClient
from aserto.authorizer import Authorizer
from flask import Flask, jsonify
from flask.wrappers import Response

from ._defaults import (
    DEFAULT_DISPLAY_STATE_MAP_ENDPOINT,
    DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_DISPLAY_STATE_MAP,
    DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_ENDPOINT,
    create_default_policy_path_resolver,
)
from ._maybe_async import MaybeAsyncCallback, maybe_await

__all__ = ["AsertoMiddleware", "AuthorizationError"]


@dataclass(frozen=True)
class AuthorizationError(Exception):
    policy_id: str
    policy_path: str


Handler = TypeVar("Handler", bound=Callable[..., Union[Response, Awaitable[Response]]])


class AsertoMiddleware:
    def __init__(
        self,
        *,
        authorizer: Authorizer,
        policy_id: str,
        policy_path_root: str,
        identity_provider: MaybeAsyncCallback[Identity],
        policy_path_resolver: Optional[MaybeAsyncCallback[str]] = None,
        resource_context_provider: Optional[MaybeAsyncCallback[ResourceContext]] = None,
    ):
        self._authorizer = authorizer
        self._identity_provider = identity_provider
        self._policy_id = policy_id
        self._policy_path_root = policy_path_root

        self._policy_path_resolver = (
            policy_path_resolver
            if policy_path_resolver is not None
            else create_default_policy_path_resolver(policy_path_root)
        )

        self._resource_context_provider = (
            resource_context_provider
            if resource_context_provider is not None
            else DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_ENDPOINT
        )

    async def _generate_client(self) -> AuthorizerClient:
        identity = await maybe_await(self._identity_provider())

        return AuthorizerClient(
            authorizer=self._authorizer,
            identity=identity,
        )

    def _with_overrides(self, **kwargs: Any) -> "AsertoMiddleware":
        return (
            self
            if not kwargs
            else AsertoMiddleware(
                authorizer=kwargs.get("authorizer", self._authorizer),
                identity_provider=kwargs.get("identity_provider", self._identity_provider),
                policy_id=kwargs.get("policy_id", self._policy_id),
                policy_path_root=kwargs.get("policy_path_root", self._policy_path_root),
                policy_path_resolver=kwargs.get("policy_path_resolver", self._policy_path_resolver),
                resource_context_provider=kwargs.get(
                    "resource_context_provider", self._resource_context_provider
                ),
            )
        )

    @overload
    async def check(self, decision: str) -> bool:
        ...

    @overload
    async def check(
        self,
        decision: str,
        *,
        authorizer: Authorizer = ...,
        identity_provider: MaybeAsyncCallback[Identity] = ...,
        policy_id: str = ...,
        policy_path_root: str = ...,
        policy_path_resolver: MaybeAsyncCallback[str] = ...,
        resource_context_provider: MaybeAsyncCallback[ResourceContext] = ...,
    ) -> bool:
        ...

    async def check(self, decision: str, **kwargs: Any) -> bool:
        return await self._with_overrides(**kwargs)._check(decision)

    async def _check(self, decision: str) -> bool:
        client, resource_context, policy_path = await gather(
            self._generate_client(),
            maybe_await(self._resource_context_provider()),
            maybe_await(self._policy_path_resolver()),
        )
        decisions = await client.decisions(
            decisions=(decision,),
            policy_id=self._policy_id,
            policy_path=policy_path,
            resource_context=resource_context,
        )
        return decisions[decision]

    @overload
    def authorize(self, handler: Handler) -> Handler:
        ...

    @overload
    def authorize(
        self,
        *,
        authorizer: Authorizer = ...,
        identity_provider: MaybeAsyncCallback[Identity] = ...,
        policy_id: str = ...,
        policy_path_root: str = ...,
        policy_path_resolver: MaybeAsyncCallback[str] = ...,
    ) -> Callable[[Handler], Handler]:
        ...

    def authorize(  # type: ignore[misc]
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Union[Handler, Callable[[Handler], Handler]]:
        arguments_error = TypeError(
            f"{self.authorize.__name__}() expects either exactly 1 callable"
            " 'handler' argument or at least 1 'options' argument"
        )

        handler: Optional[Handler] = None

        if not args and kwargs.keys() == {"handler"}:
            handler = kwargs["handler"]
        elif not kwargs and len(args) == 1:
            (handler,) = args

        if handler is not None:
            if not callable(handler):
                raise arguments_error
            return self._authorize(handler)

        if args:
            raise arguments_error

        return self._with_overrides(**kwargs)._authorize

    def _authorize(self, handler: Handler) -> Handler:
        @wraps(handler)
        async def decorated(*args: Any, **kwargs: Any) -> Response:
            client, policy_path, resource_context = await gather(
                self._generate_client(),
                maybe_await(self._policy_path_resolver()),
                maybe_await(self._resource_context_provider()),
            )

            decisions = await client.decisions(
                decisions=("allowed",),
                policy_id=self._policy_id,
                policy_path=policy_path,
                resource_context=resource_context,
            )

            if not decisions["allowed"]:
                raise AuthorizationError(policy_id=self._policy_id, policy_path=policy_path)

            return await maybe_await(handler(*args, **kwargs))

        return cast(Handler, decorated)

    def register_display_state_map(
        self,
        app: Flask,
        *,
        endpoint: str = DEFAULT_DISPLAY_STATE_MAP_ENDPOINT,
        resource_context_provider: Optional[MaybeAsyncCallback[ResourceContext]] = None,
    ) -> Flask:
        @app.route(endpoint, methods=["GET", "POST"])
        async def __displaystatemap() -> Response:
            nonlocal resource_context_provider
            if resource_context_provider is None:
                resource_context_provider = DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_DISPLAY_STATE_MAP

            client, resource_context = await gather(
                self._generate_client(),
                maybe_await(resource_context_provider()),
            )

            display_state_map = await client.decision_tree(
                decisions=["visible", "enabled"],
                policy_id=self._policy_id,
                policy_path_root=self._policy_path_root,
                resource_context=resource_context,
                policy_path_separator="SLASH",
            )
            return jsonify(display_state_map)

        return app
