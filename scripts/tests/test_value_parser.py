import pytest
import math
from utils.value_parser import parse_parameter_value

@pytest.mark.parametrize(
    "value_str,unit,expected",
    [
        ("4.7 nF", "F", ("4.7e-9", 4.7e-9)),
        ("4.7 nF", "str", ("4.7 nF", None)),
        ("1.2 kΩ", "Ω", ("1200", 1200)),
        ("0.5 mm", "mm", ("0.5", 0.5e-3)),
        ("100", "", ("100", 100)),
        ("3.3e-6", "", ("3.3e-6", 3.3e-6)),
        ("", "F", ("-", None)),
        ("", "str", ("", None)),
        ("asdf", "str", ("asdf", None)),
        ("1μF", "F", ("1e-6", 1e-6))
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