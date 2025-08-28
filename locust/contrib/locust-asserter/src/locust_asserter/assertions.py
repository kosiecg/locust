__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"

import logging
import operator
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol, TypeGuard, get_args, overload

from locust_asserter.exception import AssertionValueIncorrectTypeError

OperatorName = Literal["lt", "gt", "eq"]


@dataclass
class AssertionResult:
    category: Annotated[str, "Assertion category: total or details('endpoint name', 'HttpMethod')"]
    name: Annotated[str, "Assertion name for given stat e.g. response_time.maximum"]
    actual_value: float | int | None
    operator_name: Annotated[OperatorName, "Comparison operator name like eq - equal, gt - greater than, lt -less than"]
    expected_value: float | int
    result: bool
    exception_info: str | None = None

    def __post_init__(self):
        # 'actual_value' float formatting with 2 places precision
        if isinstance(self.actual_value, float):
            self.actual_value = round(self.actual_value, 2)

        # 'name' formatting
        self.name = self.name.strip()


class AssertionCommandProtocol(Protocol):
    def execute(self) -> AssertionResult: ...


# Part of Command pattern
class AssertionCommandsInvoker:
    def __init__(self):
        self._commands = []

    @property
    def commands(self) -> list[AssertionCommandProtocol]:
        return self._commands

    def register(self, command: AssertionCommandProtocol):
        self.commands.append(command)

    def execute_commands(self) -> list[AssertionResult]:
        return [command.execute() for command in self.commands]


class AssertionCommand:
    def __init__(
        self,
        category: str,
        name: str,
        operator_func: Callable,
        gathered_stats_getter: Callable[[str], float | int | None],
        gathered_stats_key: str,
        expected_value: float | int,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.category = category
        self.name = name
        self.operator_func = operator_func
        self.gathered_stats_getter = gathered_stats_getter
        self.gathered_stats_key = gathered_stats_key
        self.expected_value = expected_value

    def execute(self) -> AssertionResult:
        actual_value = self.gathered_stats_getter(self.gathered_stats_key)

        if not self._is_valid_operator_name(self.operator_func.__name__):
            raise ValueError(
                f"Invalid operator name: '{self.operator_func.__name__}', Should be one of {get_args(OperatorName)}"
            )

        assertion_result = AssertionResult(
            category=self.category,
            name=self.name,
            actual_value=actual_value,
            operator_name=self.operator_func.__name__,
            expected_value=self.expected_value,
            result=False,
        )

        if assertion_result.actual_value is None:
            error_message = (
                f"No data gathered from locust stats for: {self.category} -> {self.name}\n\n"
                "Check the assertion:   Especially 'endpoint' and 'method' for correctness\n"
                "Check 'Locust' output: If any request was made for given 'endpoint' and 'method'\n"
            )
            self.logger.error(error_message)
            assertion_result.exception_info = error_message

            return assertion_result

        self.logger.info(
            "Data gathered from locust stats for: %s -> %s: %s",
            self.category,
            self.name,
            assertion_result.actual_value,
        )
        try:
            result = self.operator_func(assertion_result.actual_value, assertion_result.expected_value)

        except (TypeError, ValueError) as e:
            self.logger.exception(
                f"Error when comparing {self.category} -> {self.name} "
                f"{assertion_result.actual_value = } with expected_value = {assertion_result.expected_value}"
            )
            assertion_result.exception_info = str(e)
            return assertion_result

        assertion_result.result = result

        return assertion_result

    @staticmethod
    def _is_valid_operator_name(operator_name: str) -> TypeGuard[OperatorName]:
        return operator_name in {"lt", "gt", "eq"}


class AssertableValue:
    def __init__(
        self,
        category,
        assertions_invoker,
        gathered_stats_getter: Callable[[str], float | int | None],
        gathered_stats_key: str,
        name: str = "",  # If empty AssertionResult instance's 'name' is set to 'self._gathered_stats_key'
    ):
        self._category = category
        self._name = name
        self._assertions_invoker = assertions_invoker
        self._gathered_stats_getter = gathered_stats_getter
        self._gathered_stats_key = gathered_stats_key

    def _add_assertion_command_to_invoker(self, operator_func, expected_value: float | int) -> None:
        if not isinstance(expected_value, (float, int)):
            raise AssertionValueIncorrectTypeError(
                statistic_category=self._category,
                statistic_name=self._name,
                value_name="expected_value",
                value=expected_value,
            )

        assertion_command = AssertionCommand(
            category=self._category,
            name=self._name if self._name else self._gathered_stats_key,
            operator_func=operator_func,
            gathered_stats_getter=self._gathered_stats_getter,
            gathered_stats_key=self._gathered_stats_key,
            expected_value=expected_value,
        )

        self._assertions_invoker.register(assertion_command)

    def eq(self, expected_value: float | int) -> None:
        self._add_assertion_command_to_invoker(operator.eq, expected_value)

    def lt(self, expected_value: float | int) -> None:
        self._add_assertion_command_to_invoker(operator.lt, expected_value)

    def gt(self, expected_value: float | int) -> None:
        self._add_assertion_command_to_invoker(operator.gt, expected_value)


class StatsWithAssertableValuePropertyProtocol(Protocol):
    _category: str
    _assertions_invoker: AssertionCommandsInvoker
    _gathered_stats_getter: Callable


class AssertableValueProperty:
    """
    Property to use in classes that implement StatsWithAssertableValuePropertyProtocol for 2 purposes:
        * more DRY code
        * caching - as it benefits from fact that __dict__ is earlier in lookup chain that non-data descriptor
          And this class is a non-data descriptor

    assertable_value_name - \n\t Name that finally will be passed to AssertionResult e.g. response_time.maximum
                            \n\t assertable_value_name = group_gathered_stats_name.attribute_name
                            \n\t e.g. assertable_value_name = response_time.maximum

    :param group_gathered_stats_name: Name of the group that consists AssertableValues e.g. response_time
                                      Defaults to None.

    """

    def __init__(self, group_gathered_stats_name: str | None = None):
        self.group_gathered_stats_name = group_gathered_stats_name  # e.g. response_time

    def __set_name__(self, owner: type, name: str) -> None:
        self.attribute_name = name

        # If there is no group use simple name like 'success_ratio'
        # but with group e.g. 'response_time' use name like 'response_time.maximum'
        if self.group_gathered_stats_name:
            # e.g. response_time.maximum
            self.assertable_value_name = ".".join((self.group_gathered_stats_name, self.attribute_name))
        else:
            self.assertable_value_name = self.attribute_name

    @overload
    def __get__(self, instance: None, owner: type) -> "AssertableValueProperty": ...

    @overload
    def __get__(self, instance: StatsWithAssertableValuePropertyProtocol, owner: type) -> AssertableValue: ...

    def __get__(self, instance, owner):
        # Handle the class access case
        if instance is None:
            return self

        assertable_value = AssertableValue(
            category=instance._category,
            name=self.assertable_value_name,
            assertions_invoker=instance._assertions_invoker,
            gathered_stats_getter=instance._gathered_stats_getter,
            gathered_stats_key=self.attribute_name,
        )

        instance.__dict__[self.attribute_name] = assertable_value

        return instance.__dict__[self.attribute_name]
