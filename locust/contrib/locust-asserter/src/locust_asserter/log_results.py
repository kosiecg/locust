__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"

import logging
from collections import defaultdict
from collections.abc import Iterable
from enum import StrEnum
from typing import Literal, Protocol

from .assertions import AssertionResult


class LoggingColors(StrEnum):
    RED = "31"
    GREEN = "32"
    MAGENTA = "35"


def logging_format_iterable(input_iterable: Iterable, iterable_name: str = "") -> str:
    """
    Function for formatting iterables for logging in a way:

    iterable_name:
                item1
                item2
    """

    iterable = "\n\t\t".join(str(item) for item in input_iterable)
    return f"\n{iterable_name}:\n\n\t\t{iterable}\n"


def logging_format_text_in_color(color: LoggingColors, input_text: str) -> str:
    return f"\033[{color}m{input_text}\033[0m"


def logging_format_header(input_text: str, total_width: int = 120, header_char="-") -> str:
    return f"\n\n{f' {input_text} ':{header_char}^{total_width}}\n"


class ResultsLoggerProtocol(Protocol):
    def __init__(self, logger: logging.Logger | None = None): ...

    def __call__(self, assertion_results: list[AssertionResult]): ...

    def log_results(self) -> None: ...

    def print_results(self) -> None: ...

    def warning_add(self, message):
        pass

    def _format_results(self, assertion_results: list[AssertionResult]) -> str | None: ...


class ResultsLogger:
    operator_text: dict[Literal["lt", "gt", "eq"], str] = {
        "lt": "less than",
        "gt": "greater than",
        "eq": "equal to",
    }

    def __init__(self, logger: logging.Logger | None = None):
        self._logger = logger if logger else logging.getLogger(self.__class__.__name__)
        self.assertion_results: str | None = None
        self.assertion_header: str = logging_format_text_in_color(
            color=LoggingColors.MAGENTA, input_text=logging_format_header("Assertions")
        )
        self.warnings: set[str] = set()

    def __call__(self, assertion_results: list[AssertionResult]) -> None:
        self.assertion_results = self._format_results(assertion_results)

    def log_results(self) -> None:
        if self.warnings:
            self._logger.warning(self._format_warnings())

        if self.assertion_results is None:
            return

        self._logger.info("".join((self.assertion_header, self.assertion_results, "\n", self.assertion_header)))

    def print_results(self) -> None:
        if self.warnings:
            print(self._format_warnings())

        if self.assertion_results is None:
            return

        print("".join((self.assertion_header, self.assertion_results, "\n", self.assertion_header)))

    def warning_add(self, message: str):
        """
        Method for gathering warning messages that will be displayed at the end of the load test in LocustAsserter scope
        under section 'Warnings'

        :param message: Message to be displayed as a warning.
        """
        message = logging_format_text_in_color(color=LoggingColors.RED, input_text=message)
        self.warnings.add(message)

    def _format_warnings(self) -> str:
        formatted_warnings: list[str] = []

        warnings_header: str = logging_format_text_in_color(
            color=LoggingColors.RED, input_text=logging_format_header("Warnings")
        )
        formatted_warnings.extend((warnings_header, "\n", "\n"))
        formatted_warnings.append("\n".join(self.warnings))
        formatted_warnings.extend(("\n", warnings_header, "\n"))

        return "".join(formatted_warnings)

    def _format_results(self, assertion_results: list[AssertionResult]) -> str | None:
        formatted_results: list[str] = []

        categorized_results: dict[str, list] = defaultdict(list)

        for assertion_result in assertion_results:
            categorized_results[assertion_result.category].append(assertion_result)

        if "total" in categorized_results:
            formatted_results.extend(
                self.__process_category_results(category="total", category_results=categorized_results["total"])
            )
            del categorized_results["total"]

        for category in categorized_results:
            formatted_results.extend(
                self.__process_category_results(category=category, category_results=categorized_results[category])
            )

        return "".join(formatted_results)

    def __process_category_results(self, category: str, category_results: list[AssertionResult]) -> list[str]:
        formatted_results: list[str] = ["\n"]

        for result in category_results:
            symbol: str = self.__get_formatted_by_result(
                result=result.result,
                text_passed="V",
                text_failed="X",
            )

            formatted_result: str = self.__get_formatted_by_result(
                result=result.result,
                text_passed="PASSED",
                text_failed="FAILED",
            )

            line = (
                f"\n{symbol} {category}: {result.name} is {self.operator_text.get(result.operator_name)} "
                f"{result.expected_value} : {formatted_result} (actual : {result.actual_value}) "
            )

            if result.exception_info:
                line += f"\n\nError info:\n{result.exception_info}"

            formatted_results.append(line)

        return formatted_results

    @staticmethod
    def __get_formatted_by_result(result: bool, text_passed: str, text_failed: str) -> str:
        if result:
            return logging_format_text_in_color(color=LoggingColors.GREEN, input_text=text_passed)
        return logging_format_text_in_color(color=LoggingColors.RED, input_text=text_failed)
