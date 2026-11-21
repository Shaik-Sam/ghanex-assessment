import ast
import math
import operator
from typing import Any

import requests

from agent.registry import Tool, ToolRegistry

USER_AGENT = "ghanex-assessment-agent/1.0 (educational project)"

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
}
CONSTANTS = {"pi": math.pi, "e": math.e}
MAX_EXPRESSION_LENGTH = 200
MAX_EXPONENT = 1000


class CalculationError(ValueError):
    pass


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculationError("Only numbers are allowed.")
        return node.value
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise CalculationError(f"Unknown name '{node.id}'.")
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
        return UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise CalculationError("Exponent is too large.")
        return BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:
        if node.keywords:
            raise CalculationError("Keyword arguments are not supported.")
        return FUNCTIONS[node.func.id](*[_evaluate(arg) for arg in node.args])
    raise CalculationError("Unsupported expression.")


def calculate(expression: str) -> dict[str, Any]:
    expression = expression.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    if not expression:
        return {"error": "Expression is empty."}
    if len(expression) > MAX_EXPRESSION_LENGTH:
        return {"error": "Expression is too long."}
    try:
        tree = ast.parse(expression, mode="eval")
        value = _evaluate(tree)
    except ZeroDivisionError:
        return {"error": "Division by zero."}
    except CalculationError as exc:
        return {"error": str(exc)}
    except (SyntaxError, TypeError):
        return {"error": "Could not parse the expression."}
    except (OverflowError, ValueError) as exc:
        return {"error": f"Math error: {exc}"}
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return {"error": "Result is not a finite number."}
        value = round(value, 10)
    return {"expression": expression, "result": value}


class HttpClient:
    def __init__(self, timeout: float = 10.0, session: requests.Session | None = None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def network_error(exc: Exception, service: str) -> dict[str, Any]:
    if isinstance(exc, requests.Timeout):
        return {"error": f"The {service} service timed out. Try again shortly."}
    if isinstance(exc, requests.ConnectionError):
        return {"error": f"Could not connect to the {service} service."}
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else "unknown"
        if status == 429:
            return {"error": f"The {service} service rate limit was reached. Try again later."}
        return {"error": f"The {service} service returned HTTP {status}."}
    if isinstance(exc, ValueError):
        return {"error": f"The {service} service returned an unreadable response."}
    return {"error": f"Unexpected problem contacting the {service} service."}


def make_weather_tool(http: HttpClient):
    def get_weather(location: str, units: str = "celsius") -> dict[str, Any]:
        try:
            geo = http.get_json(
                "https://geocoding-api.open-meteo.com/v1/search",
                {"name": location, "count": 1, "language": "en", "format": "json"},
            )
            matches = geo.get("results") or []
            if not matches:
                return {"error": f"Could not find a place called '{location}'."}
            place = matches[0]
            forecast = http.get_json(
                "https://api.open-meteo.com/v1/forecast",
                {
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                    "forecast_days": 3,
                    "timezone": "auto",
                    "temperature_unit": units,
                },
            )
        except Exception as exc:
            return network_error(exc, "weather")

        current = forecast.get("current", {})
        daily = forecast.get("daily", {})
        symbol = "°F" if units == "fahrenheit" else "°C"
        days = []
        for position, date in enumerate(daily.get("time", [])):
            days.append(
                {
                    "date": date,
                    "summary": WEATHER_CODES.get(daily["weather_code"][position], "unknown"),
                    "high": daily["temperature_2m_max"][position],
                    "low": daily["temperature_2m_min"][position],
                    "rain_chance_percent": daily["precipitation_probability_max"][position],
                }
            )
        return {
            "location": ", ".join(
                part for part in (place.get("name"), place.get("admin1"), place.get("country")) if part
            ),
            "temperature_unit": symbol,
            "current": {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity_percent": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "conditions": WEATHER_CODES.get(current.get("weather_code"), "unknown"),
            },
            "forecast": days,
        }

    return get_weather


def make_wikipedia_tool(http: HttpClient):
    def search_wikipedia(query: str) -> dict[str, Any]:
        try:
            data = http.get_json(
                "https://en.wikipedia.org/w/api.php",
                {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrlimit": 1,
                    "prop": "extracts|info",
                    "exintro": 1,
                    "explaintext": 1,
                    "exchars": 1200,
                    "inprop": "url",
                    "format": "json",
                    "formatversion": 2,
                },
            )
        except Exception as exc:
            return network_error(exc, "Wikipedia")

        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return {"error": f"No Wikipedia article found for '{query}'."}
        page = pages[0]
        extract = (page.get("extract") or "").strip()
        if not extract:
            return {"error": f"The Wikipedia article for '{query}' has no summary."}
        return {"title": page.get("title"), "summary": extract, "url": page.get("fullurl")}

    return search_wikipedia


def make_currency_tool(http: HttpClient):
    def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict[str, Any]:
        source = from_currency.strip().upper()
        target = to_currency.strip().upper()
        if amount < 0:
            return {"error": "Amount must not be negative."}
        if len(source) != 3 or len(target) != 3 or not source.isalpha() or not target.isalpha():
            return {"error": "Currencies must be 3-letter ISO codes such as USD or EUR."}
        if source == target:
            return {"amount": amount, "from": source, "to": target, "rate": 1.0, "converted": amount}
        try:
            data = http.get_json(
                "https://api.frankfurter.dev/v1/latest",
                {"base": source, "symbols": target},
            )
        except Exception as exc:
            if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in (404, 422):
                return {"error": f"Unsupported currency code in '{source}' or '{target}'."}
            return network_error(exc, "currency")

        rate = (data.get("rates") or {}).get(target)
        if rate is None:
            return {"error": f"No exchange rate available for {source} to {target}."}
        return {
            "amount": amount,
            "from": source,
            "to": target,
            "rate": rate,
            "converted": round(amount * rate, 2),
            "rate_date": data.get("date"),
        }

    return convert_currency


def build_default_registry(http: HttpClient | None = None) -> ToolRegistry:
    http = http or HttpClient()
    return ToolRegistry(
        [
            Tool(
                name="calculator",
                description=(
                    "Evaluate a mathematical expression exactly. Use for any arithmetic, percentages, "
                    "powers, roots or trigonometry instead of calculating mentally. Supports + - * / // % ** "
                    "parentheses, pi, e and the functions sqrt, sin, cos, tan, log, log10, exp, abs, round, floor, ceil."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The expression to evaluate, for example '(12.5 * 4) / 3 + sqrt(16)'.",
                        }
                    },
                    "required": ["expression"],
                },
                func=calculate,
            ),
            Tool(
                name="get_weather",
                description=(
                    "Get the current weather and a 3-day forecast for a city or place. "
                    "Use whenever the user asks about weather, temperature, rain or what to wear in a location."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City or place name, for example 'Hyderabad' or 'Paris, France'.",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit. Defaults to celsius.",
                        },
                    },
                    "required": ["location"],
                },
                func=make_weather_tool(http),
            ),
            Tool(
                name="search_wikipedia",
                description=(
                    "Look up a factual summary of a person, place, concept, event or organisation on Wikipedia. "
                    "Use for factual questions that may need current or detailed reference information. "
                    "Do not use for greetings, opinions or simple common knowledge."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Topic to search for, for example 'Ada Lovelace'.",
                        }
                    },
                    "required": ["query"],
                },
                func=make_wikipedia_tool(http),
            ),
            Tool(
                name="convert_currency",
                description=(
                    "Convert an amount of money between currencies using live exchange rates. "
                    "Use whenever the user asks to convert money or asks for an exchange rate."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "description": "The amount to convert."},
                        "from_currency": {
                            "type": "string",
                            "description": "Source currency as a 3-letter ISO code, for example 'USD'.",
                        },
                        "to_currency": {
                            "type": "string",
                            "description": "Target currency as a 3-letter ISO code, for example 'INR'.",
                        },
                    },
                    "required": ["amount", "from_currency", "to_currency"],
                },
                func=make_currency_tool(http),
            ),
        ]
    )
