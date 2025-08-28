__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"

# Turning off inspection because of Pycharm issue:
# https://youtrack.jetbrains.com/issue/PY-80565/False-warning-auto-not-assignable-to-StrEnum
from enum import StrEnum, auto


# noinspection PyEnum
class HttpMethod(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:
        return name

    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()
    HEAD = auto()
    OPTIONS = auto()
    TRACE = auto()
    CONNECT = auto()
