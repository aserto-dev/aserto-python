from typing import Dict, Optional, cast

from typing_extensions import Literal, overload

from ._typing import assert_unreachable

__all__ = ["Identity", "IdentityType"]


IdentityType = Literal[
    "NONE",
    "SUBJECT",
    "JWT",
]

IdentityTypeField = Literal[
    "IDENTITY_TYPE_NONE",
    "IDENTITY_TYPE_SUB",
    "IDENTITY_TYPE_JWT",
    "IDENTITY_TYPE_UNKNOWN",
]


class Identity:
    @overload
    def __init__(self, *, type: Literal["NONE"]):
        ...

    @overload
    def __init__(self, *, type: Literal["SUBJECT"], subject: str):
        ...

    @overload
    def __init__(self, *, type: Literal["JWT"], token: str):
        ...

    def __init__(
        self,
        *,
        type: IdentityType,
        subject: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self._type = type

        if self._type == "NONE":
            self._identity = None
        elif self._type == "SUBJECT":
            self._identity = subject
        elif self._type == "JWT":
            self._identity = token
        else:
            assert_unreachable(self._type)

    @property
    def type(self) -> IdentityType:
        return self._type

    @property
    def type_field(self) -> IdentityTypeField:
        if self._type == "NONE":
            return "IDENTITY_TYPE_NONE"
        elif self._type == "SUBJECT":
            return "IDENTITY_TYPE_SUB"
        elif self._type == "JWT":
            return "IDENTITY_TYPE_JWT"
        else:
            assert_unreachable(self._type)

    @property
    def identity_field(self) -> Optional[str]:
        return self._identity

    def __repr__(self) -> str:
        fields: Dict[str, str] = {"type": self._type}

        if self._type == "NONE":
            pass
        elif self._type == "SUBJECT":
            fields["subject"] = cast(str, self._identity)
        elif self._type == "JWT":
            fields["token"] = cast(str, self._identity)
        else:
            assert_unreachable(self._type)

        fields_string = ", ".join(f"{name}={value}" for name, value in fields.items())
        return f"IdentityContext({fields_string})"
