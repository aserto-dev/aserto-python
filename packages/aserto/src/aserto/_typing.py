from typing import NoReturn as Nothing


def assert_unreachable(value: Nothing) -> Nothing:
    raise AssertionError(f"Unexpectedly reached code with unhandled value: {value}")
