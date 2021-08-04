from inspect import isawaitable
from typing import Awaitable, Callable, TypeVar, Union, cast

__all__ = ["MaybeAsyncCallback", "maybe_await"]


T = TypeVar("T")
MaybeAsyncCallback = Callable[[], Union[T, Awaitable[T]]]


async def maybe_await(value: Union[T, Awaitable[T]]) -> T:
    if isawaitable(value):
        return await cast(Awaitable[T], value)
    else:
        return cast(T, value)
