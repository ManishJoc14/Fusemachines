from app.tools.calculator import create_calculator_tool
from app.tools.current_time import create_current_time_tool
from app.tools.registry import ToolRegistry
from app.tools.weather import create_weather_tool


def create_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        tools=[
            create_calculator_tool(),
            create_current_time_tool(),
            create_weather_tool(),
        ]
    )
