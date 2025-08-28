__author__ = "Grzegorz Kosiec"
__date__ = "2025-06"


class AssertionValueIncorrectTypeError(TypeError):
    def __init__(self, statistic_category: str, statistic_name: str, value_name: str, value: float | int):
        super().__init__(
            f"'{statistic_category} -> {statistic_name}': "
            f"Invalid type '{type(value)}' of {value_name} = '{value}'"
            f"\n\nCheck the assertion: '{value_name}' can be either 'float' or 'int'.\n"
        )
