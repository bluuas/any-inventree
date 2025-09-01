import pytest
import math
from utils.value_parser import parse_parameter_value

@pytest.mark.parametrize(
    "value_str,unit,expected",
    [
        ("4.7 nF", "F", ("4.7", 4.7e-9)),
        ("4.7 nF", "str", ("4.7 nF", None)),
        ("1.2 kΩ", "Ω", ("1.2", 1200)),
        ("100", "", ("100", 100)),
        ("3.3e-6", "", ("3.3e-6", 3.3e-6)),
        ("", "F", ("-", None)),
        (None, "F", ("-", None)),
        ("   ", "F", ("-", None)),
        ("10M", "Ω", ("10", 10e6)),
        ("-2.5 mA", "A", ("-2.5", -2.5e-3)),
        ("0.47uF", "F", ("0.47", 0.47e-6)),
        ("5", "str", ("5", None)),
        ("1.0", "", ("1.0", 1.0)),
        ("2.2pF", "F", ("2.2", 2.2e-12)),
        ("3.3e3", "", ("3.3e3", 3300)),
        ("not_a_number", "F", ("not_a_number", None)),
        ("7.5 μF", "F", ("7.5", 7.5e-6)),
        ("12K", "Ω", ("12", 12000)),
        ("-1.5", "", ("-1.5", -1.5)),
        ("4.7", "str", ("4.7", None)),
    ]
)
def test_parse_parameter_value_cases(value_str, unit, expected):
    result = parse_parameter_value(value_str, unit)
    # Compare display_value directly
    assert result[0] == expected[0]
    # Compare numeric_value with tolerance if both are floats, else direct
    if isinstance(result[1], float) and isinstance(expected[1], float):
        assert math.isclose(result[1], expected[1], rel_tol=1e-9, abs_tol=1e-12)
    else:
        assert result[1] == expected[1]