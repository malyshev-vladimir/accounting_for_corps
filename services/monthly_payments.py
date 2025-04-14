from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from services.members_io import load_all_members, save_all_members
from services.settings_loader import get_monthly_payment_for_residents, get_monthly_payment_for_non_residents


def iterate_months(start: datetime, end: datetime):
    """
    Generator to yield the first day of each month between start and end (inclusive).
    """
    current = datetime(start.year, start.month, 1)
    while current <= end:
        yield current
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)


def add_missing_monthly_payments(member, up_to_date: datetime):
    """
    Adds monthly payments for the given member from their creation date to up_to_date.

    Args:
        member (Member): The member to process.
        up_to_date (datetime): The latest month to include.
    """
    if not member.created_at:
        return

    created = datetime.strptime(member.created_at, "%Y-%m-%d")
    current = datetime(created.year, created.month, 1)
    end = datetime(up_to_date.year, up_to_date.month, 1)

    existing_months = {
        tx["date"][:7]
        for tx in member.transactions
        if tx["description"].startswith("Monthly contribution for")
    }

    while current <= end:
        ym = current.strftime("%Y-%m")
        date_str = f"{ym}-01"

        if ym not in existing_months:
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
                description = f"Monthly contribution for {ym}"
                member.add_transaction(date_str, description, -amount)

        current += relativedelta(months=1)
