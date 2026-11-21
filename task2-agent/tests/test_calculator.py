import pytest

from agent.tools import calculate


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("2 + 2", 4),
        ("(12.5 * 4) / 3 + sqrt(16)", round(50 / 3 + 4, 10)),
        ("2 ^ 10", 1024),
        ("18 / 100 * 2450", 441.0),
        ("-5 + 3", -2),
        ("10 % 3", 1),
        ("17 // 5", 3),
        ("round(pi, 2)", 3.14),
        ("abs(-7.5)", 7.5),
        ("12 × 3 ÷ 4", 9.0),
    ],
)
def test_valid_expressions(expression, expected):
    assert calculate(expression)["result"] == expected


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo hi')",
        "open('/etc/passwd')",
        "().__class__.__bases__",
        "[x for x in range(3)]",
        "lambda: 1",
        "'a' * 5",
        "True + 1",
        "9 ** 9 ** 9",
        "10 ** 5000",
        "1 / 0",
        "sqrt(-1)",
        "2 +",
        "unknown_name * 2",
        "",
        "1" * 300,
        "abs(x=3)",
    ],
)
def test_unsafe_or_invalid_expressions_return_errors(expression):
    result = calculate(expression)
    assert "error" in result
    assert "result" not in result
