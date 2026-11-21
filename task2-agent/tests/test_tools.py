import requests

from agent.tools import build_default_registry
from tests.conftest import FakeResponse

GEO = {"results": [{"name": "Paris", "admin1": "Île-de-France", "country": "France", "latitude": 48.85, "longitude": 2.35}]}
FORECAST = {
    "current": {"temperature_2m": 12.3, "apparent_temperature": 10.0, "relative_humidity_2m": 70, "precipitation": 0.0, "weather_code": 3, "wind_speed_10m": 9.5},
    "daily": {
        "time": ["2026-11-19", "2026-11-20"],
        "weather_code": [61, 0],
        "temperature_2m_max": [14, 15],
        "temperature_2m_min": [8, 7],
        "precipitation_probability_max": [80, 10],
    },
}


def registry(http_factory, routes):
    return build_default_registry(http_factory(routes))


def test_registry_exposes_four_tools_with_schemas(http_factory):
    reg = registry(http_factory, {})
    assert set(reg.names()) == {"calculator", "get_weather", "search_wikipedia", "convert_currency"}
    for schema in reg.schemas():
        function = schema["function"]
        assert function["description"]
        assert function["parameters"]["type"] == "object"
        assert function["parameters"]["required"]


def test_weather_success(http_factory):
    reg = registry(http_factory, {"geocoding": FakeResponse(GEO), "open-meteo.com/v1/forecast": FakeResponse(FORECAST)})
    result = reg.execute("get_weather", {"location": "Paris"})
    assert result["location"] == "Paris, Île-de-France, France"
    assert result["current"]["conditions"] == "overcast"
    assert result["forecast"][0]["summary"] == "slight rain"
    assert result["temperature_unit"] == "°C"


def test_weather_unknown_place(http_factory):
    reg = registry(http_factory, {"geocoding": FakeResponse({})})
    assert "Could not find" in reg.execute("get_weather", {"location": "Nowhereville"})["error"]


def test_weather_network_failures(http_factory):
    reg = registry(http_factory, {"geocoding": requests.Timeout()})
    assert "timed out" in reg.execute("get_weather", {"location": "Paris"})["error"]
    reg = registry(http_factory, {"geocoding": requests.ConnectionError()})
    assert "connect" in reg.execute("get_weather", {"location": "Paris"})["error"]
    reg = registry(http_factory, {"geocoding": FakeResponse(status=429)})
    assert "rate limit" in reg.execute("get_weather", {"location": "Paris"})["error"]
    reg = registry(http_factory, {"geocoding": FakeResponse(None)})
    assert "unreadable" in reg.execute("get_weather", {"location": "Paris"})["error"]


def test_weather_rejects_bad_units(http_factory):
    reg = registry(http_factory, {})
    assert "must be one of" in reg.execute("get_weather", {"location": "Paris", "units": "kelvin"})["error"]


def test_wikipedia_success_and_missing(http_factory):
    page = {"query": {"pages": [{"title": "Ada Lovelace", "extract": "English mathematician.", "fullurl": "https://en.wikipedia.org/wiki/Ada_Lovelace"}]}}
    reg = registry(http_factory, {"wikipedia.org": FakeResponse(page)})
    result = reg.execute("search_wikipedia", {"query": "Ada Lovelace"})
    assert result["title"] == "Ada Lovelace"
    assert result["url"].endswith("Ada_Lovelace")
    reg = registry(http_factory, {"wikipedia.org": FakeResponse({"batchcomplete": True})})
    assert "No Wikipedia article" in reg.execute("search_wikipedia", {"query": "zzzzqqq"})["error"]


def test_currency_success(http_factory):
    reg = registry(http_factory, {"frankfurter": FakeResponse({"rates": {"INR": 83.5}, "date": "2026-11-19"})})
    result = reg.execute("convert_currency", {"amount": 100, "from_currency": "usd", "to_currency": "inr"})
    assert result["converted"] == 8350.0
    assert result["from"] == "USD"


def test_currency_accepts_numeric_strings_from_llm(http_factory):
    reg = registry(http_factory, {"frankfurter": FakeResponse({"rates": {"EUR": 0.9}, "date": "d"})})
    result = reg.execute("convert_currency", {"amount": "1,000", "from_currency": "USD", "to_currency": "EUR"})
    assert result["converted"] == 900.0


def test_currency_validation_and_failures(http_factory):
    reg = registry(http_factory, {"frankfurter": FakeResponse(status=404)})
    assert "3-letter" in reg.execute("convert_currency", {"amount": 5, "from_currency": "dollars", "to_currency": "EUR"})["error"]
    assert "negative" in reg.execute("convert_currency", {"amount": -5, "from_currency": "USD", "to_currency": "EUR"})["error"]
    assert "Unsupported" in reg.execute("convert_currency", {"amount": 5, "from_currency": "USD", "to_currency": "ZZZ"})["error"]
    same = reg.execute("convert_currency", {"amount": 5, "from_currency": "USD", "to_currency": "USD"})
    assert same["converted"] == 5


def test_registry_rejects_bad_calls(http_factory):
    reg = registry(http_factory, {})
    assert "Unknown tool" in reg.execute("hack", {})["error"]
    assert "not valid JSON" in reg.execute("calculator", "{oops")["error"]
    assert "JSON object" in reg.execute("calculator", "[1,2]")["error"]
    assert "Missing required" in reg.execute("calculator", {})["error"]
    assert "Unknown parameter" in reg.execute("calculator", {"expression": "1", "extra": 1})["error"]
    assert "must be of type" in reg.execute("calculator", {"expression": 5})["error"]
