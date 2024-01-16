from datetime import datetime, timedelta
from time import monotonic
from typing import Union

__all__ = ["monotonic_time_from_deadline"]


def monotonic_time_from_deadline(deadline: Union[datetime, timedelta]) -> float:
    if isinstance(deadline, timedelta):
        duration = deadline.total_seconds()
    else:
        duration = (deadline - datetime.now()).total_seconds()

    return monotonic() + duration
