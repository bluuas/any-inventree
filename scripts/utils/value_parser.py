"""
Value parsing utilities for handling scientific notation and units.
"""
import re
import pandas as pd
import logging

logger = logging.getLogger('InvenTreeCLI')

def parse_parameter_value(value_str, unit=''):
    """
    Parse parameter value with scientific notation and units.
    Returns (display_value, numeric_value).

    If unit/format is "str", just return the same string.

    Examples:
    - '4.7 nF' -> ('4.7', 0.0000000047)
    - '1.2 kΩ' -> ('1.2', 1200)
    - '100' -> ('100', 100)
    - '3.3e-6' -> ('3.3e-6', 0.0000033)
    """

    if pd.isna(value_str) or not str(value_str).strip():
        return '-', None

    if unit == "str":
        return value_str, None
    
    value_str = str(value_str).strip()

    # SI prefixes mapping
    si_prefixes = {
        'T': 1e12, 'G': 1e9, 'M': 1e6, 'k': 1e3, 'K': 1e3,
        'm': 1e-3, 'μ': 1e-6, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15
    }

    # Pattern to match number with optional unit and prefix
    pattern = r'^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([μumkKMGTnpf]?)([A-Za-zΩ°%]*)$'
    match = re.match(pattern, value_str)

    if not match:
        # If no pattern match, try to extract just the number
        number_pattern = r'^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
        number_match = re.match(number_pattern, value_str)
        if number_match:
            try:
                numeric_value = float(number_match.group(1))
                return number_match.group(1), numeric_value
            except ValueError:
                pass
        return value_str, None

    try:
        base_value = float(match.group(1))
        prefix = match.group(2)
        unit_part = match.group(3)

        # Apply SI prefix multiplier
        multiplier = si_prefixes.get(prefix, 1.0)
        numeric_value = base_value * multiplier

        # Only return the numeric part as display_value
        return match.group(1), numeric_value

    except (ValueError, TypeError):
        return value_str, None

def convert_to_base_unit(value, from_unit, to_unit=''):
    """
    Convert a value from one unit to another.
    Useful for normalizing values to base units.
    
    Args:
        value: Numeric value to convert
        from_unit: Source unit (e.g., 'nF', 'kΩ')
        to_unit: Target unit (default: base unit)
    
    Returns:
        Converted numeric value
    """
    if pd.isna(value) or value is None:
        return None
        
    # This is a placeholder for more complex unit conversion
    # For now, just return the value as-is
    return float(value)

def format_value_with_unit(numeric_value, unit='', precision=None):
    """
    Format a numeric value with appropriate SI prefix and unit.
    
    Args:
        numeric_value: The numeric value to format
        unit: Base unit (e.g., 'F', 'Ω', 'H')
        precision: Number of decimal places (auto if None)
    
    Returns:
        Formatted string (e.g., '4.7 nF', '1.2 kΩ')
    """
    if numeric_value is None or pd.isna(numeric_value):
        return '-'
    
    value = float(numeric_value)
    
    # SI prefixes for formatting
    prefixes = [
        (1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'k'),
        (1, ''), (1e-3, 'm'), (1e-6, 'μ'), (1e-9, 'n'), 
        (1e-12, 'p'), (1e-15, 'f')
    ]
    
    # Find appropriate prefix
    for threshold, prefix in prefixes:
        if abs(value) >= threshold:
            scaled_value = value / threshold
            if precision is not None:
                formatted_value = f"{scaled_value:.{precision}f}"
            else:
                # Auto precision: remove trailing zeros
                formatted_value = f"{scaled_value:g}"
            return f"{formatted_value} {prefix}{unit}".strip()
    
    # Fallback for very small values
    if precision is not None:
        return f"{value:.{precision}e} {unit}".strip()
    else:
        return f"{value:g} {unit}".strip()
