__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"

from collections.abc import Callable
from typing import Protocol

from locust.stats import StatsEntry

from ..assertions import AssertableValueProperty, AssertionCommandsInvoker
from .response_time import (
    AbstractExpectedResponseTime,
    AbstractGatheredResponseTime,
    ExpectedResponseTimeStats,
    GatheredResponseTimeStats,
)


class ExpectedStatsProtocol(Protocol):
    # mypy is currently (2025.06) not fully supporting properties and even more custom descriptors,
    # so needed to expect 'AssertableValueProperty' instead of 'AssertableValue'
    # See https://github.com/python/mypy/issues/6700

    fail_ratio: AssertableValueProperty
    success_ratio: AssertableValueProperty

    failures_per_second: AssertableValueProperty
    requests_per_second: AssertableValueProperty

    failures_number: AssertableValueProperty
    requests_number: AssertableValueProperty

    response_time: AbstractExpectedResponseTime

    def __init__(self, *args, **kwargs): ...


class GatheredStatsProtocol(Protocol):
    fail_ratio: float
    success_ratio: float

    failures_per_second: float
    requests_per_second: float

    failures_number: int
    requests_number: int

    response_time: AbstractGatheredResponseTime

    def __init__(self, *args, **kwargs): ...


class ExpectedStats:
    fail_ratio = AssertableValueProperty()
    success_ratio = AssertableValueProperty()

    failures_per_second = AssertableValueProperty()
    requests_per_second = AssertableValueProperty()

    failures_number = AssertableValueProperty()
    requests_number = AssertableValueProperty()

    def __init__(
        self,
        category: str,
        assertions_invoker: AssertionCommandsInvoker,
        gathered_stats_getter: Callable[[str], float | int | AbstractGatheredResponseTime | None],
        expected_response_time_class: type[AbstractExpectedResponseTime] = ExpectedResponseTimeStats,
    ):
        self._category = category
        self._assertions_invoker = assertions_invoker
        self._gathered_stats_getter = gathered_stats_getter

        self.response_time = expected_response_time_class(
            category=category,
            assertions_invoker=self._assertions_invoker,
            group_gathered_stats_getter=self._gathered_stats_getter,
        )


class GatheredStats:
    def __init__(
        self,
        stats_entry: StatsEntry,
        response_time_class: type[AbstractGatheredResponseTime] = GatheredResponseTimeStats,
    ):
        self._stats_entry = stats_entry

        self.fail_ratio: float = self._stats_entry.fail_ratio
        self.success_ratio: float = 1 - self.fail_ratio

        self.failures_per_second: float = self._stats_entry.total_fail_per_sec
        self.requests_per_second: float = self._stats_entry.total_rps

        self.failures_number: int = self._stats_entry.num_failures
        self.requests_number: int = self._stats_entry.num_requests

        self.response_time: AbstractGatheredResponseTime = response_time_class(self._stats_entry)
