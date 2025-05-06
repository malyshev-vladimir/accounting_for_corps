from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from models.transaction import Transaction
from models.transaction_type import TransactionType
from services.members_db import load_member_by_email
from services.settings_loader import get_monthly_payment_for_residents, get_monthly_payment_for_non_residents
from services.transactions_db import load_transactions_by_email, load_transactions_by_type

# Mapping from English to German month names.
GERMAN_MONTHS = {
    "January": "Januar", "February": "Februar", "March": "März",
    "April": "April", "May": "Mai", "June": "Juni",
    "July": "Juli", "August": "August", "September": "September",
    "October": "Oktober", "November": "November", "December": "Dezember"
}


def get_german_month_name(dt: date) -> str:
    """Return the German name of the month for a given date.

    Args:
        dt: A date object.

    Returns:
        The corresponding month name in German.
    """
    return GERMAN_MONTHS[dt.strftime("%B")]


def iterate_months(start: date, end: date):
    """Yield the first day of each month between start and end (inclusive).

    Args:
        start: The starting datetime.
        end: The ending datetime.

    Yields:
        A datetime object representing the first day of each month.
    """
    current = date(start.year, start.month, 1)
    end = date(end.year, end.month, 1)

    while current <= end:
        yield current
        current += relativedelta(months=1)


def has_monthly_payment_for_month(member, month: datetime) -> bool:
    target_date = month.replace(day=1)
    for tx in load_transactions_by_email(member.email):
        if tx.date == target_date and tx.type == TransactionType.MONTHLY_FEE:
            return True
    return False


def get_missing_monthly_payment_transactions(email: str) -> list[Transaction]:
    """
    Given a member's email, return a list of all missing monthly payments
    from the creation date to the current month.

    Args:
        email (str): Email of the member.

    Returns:
        List[Transaction]: Transactions that should exist but are missing.
    """
    # Load the member object and list of transactions
    member = load_member_by_email(email)
    monthly_fees = load_transactions_by_type(email, TransactionType.MONTHLY_FEE.value)

    # Parse creation and define time range
    first_month = member.created_at.replace(day=1)
    current_month = date.today().replace(day=1)

    existing_months = {tx.date for tx in monthly_fees}

    missing_transactions = []

    for month in iterate_months(first_month, current_month):
        if month in existing_months:
            continue

        # Get payment amount
        amount = Decimal(str(
            get_monthly_payment_for_residents() if member.is_resident
            else get_monthly_payment_for_non_residents()
        ))
        if amount == 0:
            continue

        # Build transaction object
        tx = Transaction(
            transaction_date=month,
            description=f"Aktivenbeitrag ({get_german_month_name(month)} {month.year})",
            amount=-amount,
            member_email=member.email,
            transaction_type=TransactionType.MONTHLY_FEE
        )
        missing_transactions.append(tx)

    return missing_transactions
