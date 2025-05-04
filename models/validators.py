from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime
from typing import Union


def validate_date(date_str: str) -> None:
    """
    Validate that the given string is a valid date in YYYY-MM-DD format.

    Args:
        date_str (str): The date string to validate.

    Raises:
        ValueError: If the string is not a valid date in the expected format.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")


def parse_decimal(value: Union[str, float, Decimal]) -> Decimal:
    """
    Convert a given value into a Decimal rounded to 2 decimal places.
    Accepts comma or dot as a decimal separator.

    Args:
        value (str | float | Decimal): The value to convert.

    Returns:
        Decimal: Rounded decimal value, or Decimal('0.00') on error.
    """
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    try:
        normalized = str(value).replace(",", ".")
        return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")
