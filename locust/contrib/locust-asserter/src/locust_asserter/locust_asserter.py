__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"

import logging
import os
import sys

from locust import events
from locust.env import Environment
from locust.runners import WorkerRunner
from locust.stats import RequestStats

from .assertions import AssertionCommandsInvoker, AssertionResult
from .enum_http_method import HttpMethod
from .log_results import (
    LoggingColors,
    ResultsLogger,
    ResultsLoggerProtocol,
    logging_format_header,
    logging_format_iterable,
    logging_format_text_in_color,
)
from .stats.stats import ExpectedStats, ExpectedStatsProtocol, GatheredStats, GatheredStatsProtocol


class LocustAsserter:
    def __init__(
        self,
        expected_stats_class: type[ExpectedStatsProtocol] = ExpectedStats,
        gathered_stats_class: type[GatheredStatsProtocol] = GatheredStats,
        assertions_invoker_class: type[AssertionCommandsInvoker] = AssertionCommandsInvoker,
        result_logger_class: type[ResultsLoggerProtocol] = ResultsLogger,
    ):
        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)

        # Initial setup
        events.quitting.add_listener(self)
        self._gathered_stats_class = gathered_stats_class
        self._expected_stats_class = expected_stats_class
        self._result_logger = result_logger_class(self._logger)

        # Store data from user
        self._assertions_invoker = assertions_invoker_class()

        self.total = self._expected_stats_class(
            category="total",
            assertions_invoker=self._assertions_invoker,
            gathered_stats_getter=lambda key: getattr(self._gathered_total, key, None),  # for lazy access
        )
        self._expected_endpoints: set[tuple[str, str]] = set()

        # Store data from locust stats - added later in __call__
        self._gathered_total: GatheredStatsProtocol | None = None
        self._gathered_details: dict[tuple[str, str], GatheredStatsProtocol] | None = None

    def details(self, endpoint: str, method: str | HttpMethod) -> ExpectedStatsProtocol:
        def gathered_details_stats_getter(gathered_stats_key):
            gathered_endpoint_details = self._gathered_details.get((endpoint, method), None)
            if gathered_endpoint_details is None:
                return None

            return getattr(gathered_endpoint_details, gathered_stats_key, None)

        if isinstance(method, str):
            try:
                method = HttpMethod[method.upper()]
            except KeyError:
                self._result_logger.warning_add(
                    f"Added assertion for {endpoint=} with custom {method=}. "
                    "In case of problems check carefully method name."
                )

        self._expected_endpoints.add((endpoint, method))

        return self._expected_stats_class(
            category=f"details('{endpoint}', '{method}')",
            assertions_invoker=self._assertions_invoker,
            gathered_stats_getter=gathered_details_stats_getter,
        )

    def __call__(self, environment: Environment, **kwargs) -> None:
        if not environment.runner or isinstance(environment.runner, WorkerRunner):
            return

        stats: RequestStats = environment.runner.stats
        self._gathered_total = self._gathered_stats_class(stats.total)

        self._gathered_details = self.__gathered_details_prepare(stats)

        assertion_results: list[AssertionResult] = self._do_checks()

        # Log LocustAsserter's assertion results
        self._result_logger(assertion_results)
        self._result_logger.log_results()

        self.__exit_with_proper_code(environment, assertion_results)

    def _do_checks(self) -> list[AssertionResult]:
        if self._logger.isEnabledFor(logging.INFO):  # Guard for lazy evaluation
            self._logger.info(
                logging_format_text_in_color(
                    color=LoggingColors.GREEN,
                    input_text=logging_format_header(f"{self.__class__.__name__}: Starting checks"),
                )
            )

        assertion_results: list[AssertionResult] = self._assertions_invoker.execute_commands()

        if self._logger.isEnabledFor(logging.DEBUG):  # Guard for lazy evaluation
            self._logger.debug(
                logging_format_iterable(iterable_name="Assertion Results", input_iterable=assertion_results)
            )

        return assertion_results

    def __gathered_details_prepare(self, stats: RequestStats) -> dict[tuple[str, str], GatheredStatsProtocol]:
        endpoints_intersection_expected_gathered = self._expected_endpoints & set(stats.entries.keys())

        return {
            endpoint: self._gathered_stats_class(stats.entries[endpoint])
            for endpoint in endpoints_intersection_expected_gathered
        }

    @staticmethod
    def __exit_with_proper_code(environment, assertion_results: list[AssertionResult]) -> None:
        """
        Should be always invoked as  last step in Locust Asserter

        Pycharm is not taking into account locust graceful shutdown procedure with setting exit code via
        environment.process_exit_code

        So if any of assertion failed immediate program termination with exit code 1 is invoked
            -> so at least exit code is matching between console and Pycharm.
        """
        if not all(assertion_result.result for assertion_result in assertion_results):
            environment.process_exit_code = 1

            if "PYCHARM_HOSTED" in os.environ:
                sys.exit(1)
            return
        environment.process_exit_code = 0
