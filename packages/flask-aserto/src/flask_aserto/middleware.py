from functools import wraps
from typing import Any, Callable, Optional, Union, cast, overload

from aserto.client import AuthorizerOptions
from aserto.client.authorizer import AuthorizerClient
from flask import Flask, jsonify
from flask.wrappers import Response

from ._defaults import (
    DEFAULT_DISPLAY_STATE_MAP_ENDPOINT,
    DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_DISPLAY_STATE_MAP,
    DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_ENDPOINT,
    create_default_policy_path_resolver,
    IdentityMapper,
    StringMapper,
    ResourceMapper,
    ObjectMapper,
    AuthorizationError,
    Handler
)

from .check import CheckMiddleware, CheckOptions

class AsertoMiddleware:
    def __init__(
        self,
        *,
        authorizer_options: AuthorizerOptions,
        policy_path_root: str,
        identity_provider: IdentityMapper,
        policy_instance_name: Optional[str]= None,
        policy_instance_label: Optional[str]= None,
        policy_path_resolver: Optional[StringMapper] = None,
        resource_context_provider: Optional[ResourceMapper] = None,
    ):
        self._authorizer_options = authorizer_options
        self._identity_provider = identity_provider
        self._policy_instance_name = policy_instance_name
        self._policy_instance_label = policy_instance_label
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

    def _generate_client(self) -> AuthorizerClient:
        identity = self._identity_provider()

        return AuthorizerClient(
            identity=identity,
            options=self._authorizer_options,
        )

    def _with_overrides(self, **kwargs: Any) -> "AsertoMiddleware":
        return (
            self
            if not kwargs
            else AsertoMiddleware(
                authorizer_options=kwargs.get("authorizer", self._authorizer_options),
                policy_path_root=kwargs.get("policy_path_root", self._policy_path_root),
                identity_provider=kwargs.get("identity_provider", self._identity_provider),
                policy_instance_name=kwargs.get("policy_instance_name", self._policy_instance_name),
                policy_instance_label=kwargs.get("policy_instance_label", self._policy_instance_label),
                policy_path_resolver=kwargs.get("policy_path_resolver", self._policy_path_resolver),
                resource_context_provider=kwargs.get(
                    "resource_context_provider", self._resource_context_provider
                ),
            )
        )

    @overload
    def is_allowed(self, decision: str) -> bool:
        ...

    @overload
    def is_allowed(
        self,
        decision: str,
        *,
        authorizer_options: AuthorizerOptions = ...,
        identity_provider: IdentityMapper = ...,
        policy_instance_name: str = ...,
        policy_instance_label: str = ...,
        policy_path_root: str = ...,
        policy_path_resolver: StringMapper = ...,
        resource_context_provider: ResourceMapper = ...,
    ) -> bool:
        ...

    def is_allowed(self, decision: str, **kwargs: Any) -> bool:
        return self._with_overrides(**kwargs)._is_allowed(decision)

    def _is_allowed(self, decision: str) -> bool:
        client = self._generate_client()
        resource_context = self._resource_context_provider()
        policy_path = self._policy_path_resolver()
        
        decisions = client.decisions(
            policy_path=policy_path,
            decisions=(decision,),
            policy_instance_name=self._policy_instance_name,
            policy_instance_label=self._policy_instance_label,
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
        authorizer_options: AuthorizerOptions = ...,
        identity_provider: IdentityMapper = ...,
        policy_instance_name: str = ...,
        policy_instance_label: str = ...,
        policy_path_root: str = ...,
        policy_path_resolver: StringMapper = ...,
    ) -> Callable[[Handler], Handler]:
        ...

    def authorize(
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
        if self._policy_instance_name == None:
            raise TypeError(f"{self._policy_instance_name}() should not be None")
        
        if self._policy_instance_label == None:
            self._policy_instance_label = self._policy_instance_name

        @wraps(handler)
        def decorated(*args: Any, **kwargs: Any) -> Response:
            client = self._generate_client()
            resource_context = self._resource_context_provider()
            policy_path = self._policy_path_resolver()

            decisions = client.decisions(
                policy_path=policy_path,
                decisions=("allowed",),
                policy_instance_name=self._policy_instance_name,
                policy_instance_label=self._policy_instance_label,
                resource_context=resource_context,
            )

            if not decisions["allowed"]:
                raise AuthorizationError(policy_instance_name=self._policy_instance_name, policy_path=policy_path) # type: ignore[arg-type]

            return handler(*args, **kwargs)

        return cast(Handler, decorated)
    
    def check(
        self, 
        objId: Optional[str] = "",
        objType: Optional[str] = "",
        objIdMapper: Optional[StringMapper] = None,
        objMapper: Optional[ObjectMapper] = None,
        relationName: Optional[str] = "",
        relationMapper: Optional[StringMapper] = None,
        subjType: Optional[str] = "",
        subjMapper: Optional[IdentityMapper] = None,
        policyPath: Optional[str] = "",
        policyRoot: Optional[str] = "",
        policyPathMapper: Optional[StringMapper] = None,
    ) -> CheckMiddleware:
        opts = CheckOptions(
            objId=objId, objType=objType,objIdMapper=objIdMapper,
            objMapper=objMapper, relationName=relationName, relationMapper=relationMapper,
            subjType=subjType, subjMapper=subjMapper, policyRoot=policyRoot,
            policyPath=policyPath, policyPathMapper=policyPathMapper)
        return CheckMiddleware(options=opts, aserto_middleware=self)

    def register_display_state_map(
        self,
        app: Flask,
        *,
        endpoint: str = DEFAULT_DISPLAY_STATE_MAP_ENDPOINT,
        resource_context_provider: Optional[ResourceMapper] = None,
    ) -> Flask:
        @app.route(endpoint, methods=["GET", "POST"])
        def __displaystatemap() -> Response:
            nonlocal resource_context_provider
            if resource_context_provider is None:
                resource_context_provider = DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_DISPLAY_STATE_MAP

            client = self._generate_client()
            resource_context = resource_context_provider()

            display_state_map = client.decision_tree(
                policy_path_root=self._policy_path_root,
                decisions=["visible", "enabled"],
                policy_instance_name=self._policy_instance_name,
                policy_instance_label=self._policy_instance_label,
                resource_context=resource_context,
                policy_path_separator="SLASH",
            )
            return jsonify(display_state_map)

        return app
