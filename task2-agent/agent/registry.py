import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate(self, arguments: dict[str, Any]) -> str | None:
        properties = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        for key in required:
            if key not in arguments or arguments[key] in (None, ""):
                return f"Missing required parameter '{key}'."
        type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool}
        for key, value in arguments.items():
            spec = properties.get(key)
            if spec is None:
                return f"Unknown parameter '{key}'."
            expected = type_map.get(spec.get("type"))
            if expected and (not isinstance(value, expected) or isinstance(value, bool) and spec["type"] != "boolean"):
                return f"Parameter '{key}' must be of type {spec['type']}."
            if "enum" in spec and value not in spec["enum"]:
                return f"Parameter '{key}' must be one of {spec['enum']}."
        return None

    def coerce(self, arguments: dict[str, Any]) -> dict[str, Any]:
        properties = self.parameters.get("properties", {})
        coerced = dict(arguments)
        for key, value in arguments.items():
            kind = properties.get(key, {}).get("type")
            if kind in ("number", "integer") and isinstance(value, str):
                try:
                    number = float(value.replace(",", "").strip())
                except ValueError:
                    continue
                coerced[key] = int(number) if kind == "integer" and number.is_integer() else number
        return coerced

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        arguments = self.coerce(arguments)
        problem = self.validate(arguments)
        if problem:
            return {"error": problem}
        try:
            return self.func(**arguments)
        except Exception as exc:
            return {"error": f"Tool '{self.name}' failed unexpectedly: {exc}"}


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None):
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, raw_arguments: str | dict[str, Any] | None) -> dict[str, Any]:
        tool = self.get(name)
        if tool is None:
            return {"error": f"Unknown tool '{name}'. Available tools: {', '.join(self.names())}."}
        if isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            try:
                arguments = json.loads(raw_arguments) if raw_arguments else {}
            except json.JSONDecodeError:
                return {"error": "Tool arguments were not valid JSON."}
            if not isinstance(arguments, dict):
                return {"error": "Tool arguments must be a JSON object."}
        return tool.run(arguments)
