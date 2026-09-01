from __future__ import annotations

import ast
import json
import math
import operator
from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.tools.registry import RegisteredTool, ToolRegistry


class CalculatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str = Field(min_length=1, max_length=200)


class CurrentTimeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafeCalculator:
    """Evaluate arithmetic expressions without executing arbitrary Python."""

    BINARY_OPERATORS: ClassVar = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    UNARY_OPERATORS: ClassVar = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(self, expression: str) -> int | float:
        # Step 1: Parse syntax without evaluating Python code.
        tree = ast.parse(expression, mode="eval")

        # Step 2: Recursively allow only numeric nodes and approved operators.
        result = self._evaluate_node(tree.body)

        # Step 3: Reject values that are unsafe or impractical to serialize.
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Result must be finite")
        if abs(result) > 1e15:
            raise ValueError("Result is too large")
        return result

    def _evaluate_node(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError("Only numeric values are allowed")
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in self.BINARY_OPERATORS:
            left = self._evaluate_node(node.left)
            right = self._evaluate_node(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent is too large")
            operation = self.BINARY_OPERATORS[type(node.op)]
            return operation(left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in self.UNARY_OPERATORS:
            operation = self.UNARY_OPERATORS[type(node.op)]
            return operation(self._evaluate_node(node.operand))

        raise ValueError("Expression contains an unsupported operation")


def calculate(input_data: BaseModel) -> str:
    calculator_input = CalculatorInput.model_validate(input_data.model_dump())
    result = SafeCalculator().evaluate(calculator_input.expression)
    return json.dumps({"result": result})


def current_utc_time(_: BaseModel) -> str:
    return json.dumps({"utc_time": datetime.now(UTC).isoformat()})


def create_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        tools=[
            RegisteredTool(
                name="calculator",
                description="Safely evaluate a mathematical expression.",
                input_model=CalculatorInput,
                handler=calculate,
            ),
            RegisteredTool(
                name="current_utc_time",
                description="Return the current date and time in UTC.",
                input_model=CurrentTimeInput,
                handler=current_utc_time,
            ),
        ]
    )
