__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"

from abc import ABC, abstractmethod
from collections.abc import Callable

from locust.stats import StatsEntry

from ..assertions import AssertableValue, AssertableValueProperty, AssertionCommandsInvoker
from ..exception import AssertionValueIncorrectTypeError


def percentile_normalization(percentile: float | int) -> float | int:
    if percentile > 1:
        percentile /= 100

    return percentile


class AbstractExpectedResponseTime(ABC):
    # mypy is currently (2025.06) not fully supporting properties and even more custom descriptors,
    # so needed to expect 'AssertableValueProperty' instead of 'AssertableValue'
    # See https://github.com/python/mypy/issues/6700

    average: AssertableValueProperty
    maximum: AssertableValueProperty
    median: AssertableValueProperty
    minimum: AssertableValueProperty

    @abstractmethod
    def __init__(self, *args, **kwargs): ...

    @abstractmethod
    def percentile(self, percentile: float | int) -> AssertableValue | None: ...


class AbstractGatheredResponseTime(ABC):
    average: float
    maximum: int
    median: int
    minimum: int | None

    @abstractmethod
    def __init__(self, *args, **kwargs): ...

    @abstractmethod
    def percentile(self, percentile: float | int) -> int: ...


class ExpectedResponseTimeStats(AbstractExpectedResponseTime):
    _group_gathered_stats_key = "response_time"

    average = AssertableValueProperty(group_gathered_stats_name=_group_gathered_stats_key)
    maximum = AssertableValueProperty(group_gathered_stats_name=_group_gathered_stats_key)
    median = AssertableValueProperty(group_gathered_stats_name=_group_gathered_stats_key)
    minimum = AssertableValueProperty(group_gathered_stats_name=_group_gathered_stats_key)

    def __init__(
        self,
        category: str,
        assertions_invoker: AssertionCommandsInvoker,
        group_gathered_stats_getter: Callable[[str], AbstractGatheredResponseTime | None],
    ):
        self._category = category
        self._assertions_invoker = assertions_invoker
        self._group_gathered_stats_getter = group_gathered_stats_getter

    def percentile(self, percentile: float | int) -> AssertableValue | None:
        if not isinstance(percentile, (float, int)):
            raise AssertionValueIncorrectTypeError(
                statistic_category=self._category,
                statistic_name=self._group_gathered_stats_key + ".percentile",
                value_name="percentile",
                value=percentile,
            )

        # for output percentile in format 0-100 is needed
        percentile_for_output = int(percentile * 100) if percentile < 1 else percentile

        # for locust stats percentile in format 0-1 is needed
        percentile = percentile_normalization(percentile)

        def gathered_percentile_stats_getter(gathered_stats_key: str) -> int | None:
            """
            Custom getter callback for lazy accessing response_time.percentile
            """
            percentile_func = self._gathered_stats_getter(gathered_stats_key)

            if percentile_func is None:
                return None

            if not callable(percentile_func):
                raise TypeError(
                    f"Expected percentile function: '{gathered_stats_key}' to be callable, "
                    f"but got type: '{type(percentile_func).__name__}'"
                )

            return percentile_func(percentile)

        return AssertableValue(
            category=self._category,
            name=f"{self._group_gathered_stats_key}.{percentile_for_output}th percentile",
            assertions_invoker=self._assertions_invoker,
            gathered_stats_getter=gathered_percentile_stats_getter,
            gathered_stats_key="percentile",
        )

    def _gathered_stats_getter(self, gathered_stats_key: str) -> float | int | Callable[[float | int], int] | None:
        """
        Function used both in 'AssertableValueProperty' internals and in 'percentile' method of this class
        :param  gathered_stats_key: Name of attribute to take from response_time object e.g. 'maximum'
        :return: Value of an attribute taken from response_time object
        """

        response_time_stats: AbstractGatheredResponseTime | None = self._group_gathered_stats_getter(
            self._group_gathered_stats_key
        )

        if response_time_stats is None:
            return None

        return getattr(response_time_stats, gathered_stats_key, None)


class GatheredResponseTimeStats(AbstractGatheredResponseTime):
    def __init__(self, stats_entry: StatsEntry):
        self._stats_entry = stats_entry

        self.average = self._stats_entry.avg_response_time
        self.maximum = self._stats_entry.max_response_time
        self.median = self._stats_entry.median_response_time
        self.minimum = self._stats_entry.min_response_time

    def percentile(self, percentile: float | int) -> int:
        percentile = percentile_normalization(percentile)

        return self._stats_entry.get_response_time_percentile(percentile)
