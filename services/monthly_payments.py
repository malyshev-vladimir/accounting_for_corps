from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from services.settings_loader import get_monthly_payment_for_residents, get_monthly_payment_for_non_residents


# Mapping from English to German month names.
GERMAN_MONTHS = {
    "January": "Januar", "February": "Februar", "March": "März",
    "April": "April", "May": "Mai", "June": "Juni",
    "July": "Juli", "August": "August", "September": "September",
    "October": "Oktober", "November": "November", "December": "Dezember"
}


def get_german_month_name(dt: datetime) -> str:
    """Return the German name of the month for a given date.

    Args:
        dt: A datetime object.

    Returns:
        The corresponding month name in German.
    """
    return GERMAN_MONTHS[dt.strftime("%B")]


def iterate_months(start: datetime, end: datetime):
    """Yield the first day of each month between start and end (inclusive).

    Args:
        start: The starting datetime.
        end: The ending datetime.

    Yields:
        A datetime object representing the first day of each month.
    """
    current = datetime(start.year, start.month, 1)
    while current <= end:
        yield current
        current += relativedelta(months=1)


def add_missing_monthly_payments(member, up_to_date: datetime):
    """Add missing monthly payment transactions for a member.

    Monthly payments are added from the member's creation date
    up to the specified date if they do not already exist.

    Args:
        member: A Member instance to update.
        up_to_date: The final month (inclusive) to check for missing payments.
    """
    if not member.created_at:
        return

    created = datetime.strptime(member.created_at, "%Y-%m-%d")
    current = datetime(created.year, created.month, 1)
    end = datetime(up_to_date.year, up_to_date.month, 1)

    # Collect existing descriptions to check for exact matches
    existing_descriptions = {
        tx["description"]
        for tx in member.transactions
    }

    while current <= end:
        date_str = current.strftime("%Y-%m-01")
        title = member.title

        if title == "AH":
            amount = Decimal("0.00")
        else:
            is_resident = member.get_resident_status_at(date_str)
            if is_resident:
                amount = Decimal(str(get_monthly_payment_for_residents()))
            else:
                amount = Decimal(str(get_monthly_payment_for_non_residents()))

        if amount > 0:
            month_label = get_german_month_name(current)
            year = current.year
            description = f"Aktivenbeitrag ({month_label} {year})"

            if description not in existing_descriptions:
                member.add_transaction(date_str, description, -amount)

        current += relativedelta(months=1)
