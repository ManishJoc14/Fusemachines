from __future__ import annotations

import ast
import json
import math
import operator
from collections.abc import Callable
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.tools.registry import RegisteredTool

Number = int | float
MathFunction = Callable[..., Number]


def _factorial(value: Number) -> int:
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("factorial requires a whole number")
    integer = int(value)
    if integer < 0 or integer > 170:
        raise ValueError("factorial input must be between 0 and 170")
    return math.factorial(integer)


def _rounded(value: Number, decimal_places: Number = 0) -> Number:
    if isinstance(decimal_places, float) and not decimal_places.is_integer():
        raise ValueError("round decimal places must be a whole number")
    places = int(decimal_places)
    if abs(places) > 15:
        raise ValueError("round decimal places must be between -15 and 15")
    return round(value, places)


def _percentage_of(percent: Number, value: Number) -> float:
    return (percent / 100) * value


class CalculatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "Arithmetic or scientific expression, such as sqrt(81), "
            "round(pi, 3), or percentage_of(15, 200)."
        ),
    )


class SafeCalculator:
    """Evaluate arithmetic expressions without executing arbitrary Python."""

    MAX_AST_NODES = 50
    MAX_ABSOLUTE_RESULT = 1e15

    BINARY_OPERATORS: ClassVar[dict[type[ast.operator], MathFunction]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    UNARY_OPERATORS: ClassVar[dict[type[ast.unaryop], MathFunction]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }
    CONSTANTS: ClassVar[dict[str, Number]] = {
        "e": math.e,
        "pi": math.pi,
        "tau": math.tau,
    }
    # Each entry stores: function, minimum arguments, maximum arguments.
    FUNCTIONS: ClassVar[dict[str, tuple[MathFunction, int, int]]] = {
        "abs": (abs, 1, 1),
        "ceil": (math.ceil, 1, 1),
        "cos": (math.cos, 1, 1),
        "degrees": (math.degrees, 1, 1),
        "factorial": (_factorial, 1, 1),
        "floor": (math.floor, 1, 1),
        "log": (math.log, 1, 2),
        "log10": (math.log10, 1, 1),
        "max": (max, 2, 10),
        "min": (min, 2, 10),
        "percentage_of": (_percentage_of, 2, 2),
        "radians": (math.radians, 1, 1),
        "round": (_rounded, 1, 2),
        "sin": (math.sin, 1, 1),
        "sqrt": (math.sqrt, 1, 1),
        "tan": (math.tan, 1, 1),
    }

    def evaluate(self, expression: str) -> Number:
        # Step 1: Parse syntax without evaluating Python code.
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > self.MAX_AST_NODES:
            raise ValueError("Expression is too complex")

        # Step 2: Evaluate only approved numbers, operators, constants, and functions.
        result = self._evaluate_node(tree.body)

        # Step 3: Reject values that are unsafe or impractical to serialize.
        self._validate_result(result)
        return result

    def _evaluate_node(self, node: ast.AST) -> Number:
        if isinstance(node, ast.Constant):
            return self._read_number(node.value)

        if isinstance(node, ast.Name):
            return self._read_constant(node.id)

        if isinstance(node, ast.BinOp) and type(node.op) in self.BINARY_OPERATORS:
            return self._evaluate_binary(node)

        if isinstance(node, ast.UnaryOp) and type(node.op) in self.UNARY_OPERATORS:
            return self._evaluate_unary(node)

        if isinstance(node, ast.Call):
            return self._evaluate_function(node)

        raise ValueError("Expression contains an unsupported operation")

    @staticmethod
    def _read_number(value: object) -> Number:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Only numeric values are allowed")
        return value

    def _read_constant(self, name: str) -> Number:
        if name not in self.CONSTANTS:
            raise ValueError(f"Unknown constant: {name}")
        return self.CONSTANTS[name]

    def _evaluate_binary(self, node: ast.BinOp) -> Number:
        left = self._evaluate_node(node.left)
        right = self._evaluate_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("Exponent is too large")

        operation = self.BINARY_OPERATORS[type(node.op)]
        return operation(left, right)

    def _evaluate_unary(self, node: ast.UnaryOp) -> Number:
        operation = self.UNARY_OPERATORS[type(node.op)]
        return operation(self._evaluate_node(node.operand))

    def _evaluate_function(self, node: ast.Call) -> Number:
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise ValueError("Only direct function calls without keywords are allowed")

        function_spec = self.FUNCTIONS.get(node.func.id)
        if function_spec is None:
            raise ValueError(f"Unknown function: {node.func.id}")

        function, minimum_args, maximum_args = function_spec
        if not minimum_args <= len(node.args) <= maximum_args:
            raise ValueError(
                f"{node.func.id} expects between {minimum_args} "
                f"and {maximum_args} arguments"
            )

        arguments = [self._evaluate_node(argument) for argument in node.args]
        return function(*arguments)

    def _validate_result(self, result: Number) -> None:
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Result must be finite")
        if abs(result) > self.MAX_ABSOLUTE_RESULT:
            raise ValueError("Result is too large")


def calculate(input_data: BaseModel) -> str:
    calculator_input = CalculatorInput.model_validate(input_data.model_dump())
    result = SafeCalculator().evaluate(calculator_input.expression)
    return json.dumps(
        {
            "expression": calculator_input.expression,
            "result": result,
        }
    )


def create_calculator_tool() -> RegisteredTool:
    return RegisteredTool(
        name="calculator",
        description=(
            "Safely evaluate arithmetic, percentages, constants, and common "
            "scientific functions. Trigonometric functions use radians."
        ),
        input_model=CalculatorInput,
        handler=calculate,
    )
