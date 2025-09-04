import pytest
import math
from utils.value_parser import parse_parameter_value

@pytest.mark.parametrize(
    "value_str,unit,expected",
    [
        ("4.7 nF", "F", ("4.7e-9", 4.7e-9)),
        ("4.7 nF", "str", ("4.7 nF", None)),
        ("1.2 kΩ", "Ω", ("1200", 1200)),
        ("0.5 mm", "mm", ("0.5", 0.5)),
        ("0.5 mm", "m", ("0.0005", 0.0005)),
        ("100", "", ("100", 100)),
        ("3.3e-6", "", ("3.3e-6", 3.3e-6)),
        ("", "F", ("-", None)),
        ("", "str", ("-", None)),
        ("asdf", "str", ("asdf", None)),
        ("1μF", "F", ("1e-6", 1e-6))
    ]
)
def test_parse_parameter_value_cases(value_str, unit, expected):
    result = parse_parameter_value(value_str, unit)

    # Normalize the display values for comparison
    normalized_result = normalize_scientific(result[0])
    normalized_expected = normalize_scientific(expected[0])

    # Compare display_value directly
    assert normalized_result == normalized_expected

    # Compare numeric_value with tolerance if both are floats, else direct
    if isinstance(result[1], float) and isinstance(expected[1], float):
        assert math.isclose(result[1], expected[1], rel_tol=1e-9, abs_tol=1e-12)
    else:
        assert result[1] == expected[1]

def normalize_scientific(value):
    """Normalize scientific notation strings for comparison."""
    try:
        # Convert to float and back to string to standardize format
        return format(float(value), '.6e')
    except ValueError:
        return value  # Return the original value if conversion fails