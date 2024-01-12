from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, Union, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from .middleware import AsertoMiddleware

from aserto.client import ResourceContext
from flask.wrappers import Response

from ._defaults import (
    IdentityMapper,
    StringMapper,
    ResourceMapper,
    ObjectMapper,
    Obj,
    AuthorizationError,
    Handler
)

@dataclass(frozen=True)
class CheckOptions:
    """
    Check options class used to create a new instance of Check Middleware
    """
    objId: Optional[str] = ""
    objType: Optional[str] = ""
    objIdMapper: Optional[StringMapper] = None
    objMapper: Optional[ObjectMapper] = None
    relationName: Optional[str] = ""
    relationMapper: Optional[StringMapper] = None
    subjType: Optional[str] = ""
    subjMapper: Optional[IdentityMapper] = None
    policyPath: Optional[str] = ""
    policyRoot: Optional[str] = ""
    policyPathMapper: Optional[StringMapper] = None



def build_resource_context_mapper(
       opts: CheckOptions
) -> ResourceMapper:

    async def resource() -> ResourceContext:
        objid = (
            opts.objId
            if opts.objId is not None
            else ""
        )
        objtype = (
            opts.objType
            if opts.objType is not None
            else ""
        )
        
        obj = (
            await opts.objMapper()
            if opts.objMapper is not None
            else Obj(id=objid, objType=objtype)
        )
         
        obj.id = (
            await opts.objIdMapper()
            if opts.objIdMapper is not None
            else obj.id
        )

        relation = (
            await opts.relationMapper()
            if opts.relationMapper is not None
            else opts.relationName
        )

        subjType = (
            opts.subjType
            if opts.subjType != ""
            else "user"
        )

        return {"relation":     relation,
		"object_type":  obj.objType,
		"object_id":    obj.id,
		"subject_type": subjType}
    
    return resource

class CheckMiddleware:
    def __init__(
        self,
        *,
        options: CheckOptions,
        aserto_middleware: "AsertoMiddleware",
    ):
        self._aserto_middleware = aserto_middleware
        
        self._identity_provider = (
            options.subjMapper
            if options.subjMapper is not None
            else aserto_middleware._identity_provider
        )

        self._resource_context_provider = build_resource_context_mapper(options)
        self._options = options

    def _with_overrides(self, **kwargs: Any) -> "CheckMiddleware":
        return (
            self
            if not kwargs
            else CheckMiddleware(
                aserto_middleware=self._aserto_middleware,
                options = CheckOptions(
                    relationName=kwargs.get("relation_name", self._options.relationName),
                    relationMapper=kwargs.get("relation_mapper", self._options.relationMapper),
                    policyPath=kwargs.get("policy_path", self._options.policyPath),
                    policyRoot=kwargs.get("policy_root", self._options.policyRoot),
                    subjMapper=kwargs.get("identity_provider", self._identity_provider),
                    objId=kwargs.get("object_id", self._options.objId),
                    objType=kwargs.get("object_type", self._options.objType),
                    objIdMapper=kwargs.get("object_id_mapper", self._options.objIdMapper),
                    objMapper=kwargs.get("object_mapper", self._options.objMapper),
                    subjType=self._options.subjType,
                    policyPathMapper=self._options.policyPathMapper,
                ),
            )
        )
    
    def _build_policy_path_mapper(self) -> StringMapper:
        async def mapper() -> str:
            policy_path = ""
            if self._options.policyPathMapper is not None:
                policy_path = await self._options.policyPathMapper()
            if policy_path == "":
                policy_path = "check"
                policy_root = self._options.policyRoot or self._aserto_middleware._policy_path_root
                if policy_root:
                    policy_path = f"{policy_root}.{policy_path}"
            return policy_path
        
        return mapper

    async def authorize(
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
        if self._aserto_middleware._policy_instance_name == None:
            raise TypeError(f"{self._aserto_middleware._policy_instance_name}() should not be None")
        
        if self._aserto_middleware._policy_instance_label == None:
            self._aserto_middleware._policy_instance_label = self._aserto_middleware._policy_instance_name

        @wraps(handler)
        async def decorated(*args: Any, **kwargs: Any) -> Response:

            policy_mapper = self._build_policy_path_mapper()
            resource_context = await self._resource_context_provider()
            decision = await self._aserto_middleware.is_allowed(
                decision="allowed",
                authorizer_options=self._aserto_middleware._authorizer_options,
                identity_provider=self._identity_provider,
                policy_instance_name=self._aserto_middleware._policy_instance_name or "",
                policy_instance_label=self._aserto_middleware._policy_instance_label or "",
                policy_path_root=self._options.policyRoot or self._aserto_middleware._policy_path_root,
                policy_path_resolver=policy_mapper,
                resource_context_provider=resource_context,
            )

            if not decision:
                raise AuthorizationError(policy_instance_name=self._aserto_middleware._policy_instance_name, policy_path=policy_mapper()) # type: ignore[arg-type]

            return await handler(*args, **kwargs)

        return cast(Handler, decorated)