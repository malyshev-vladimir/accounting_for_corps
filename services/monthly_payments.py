from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

MONTHLY_PAYMENTS = {
    "monthly_payment_for_active": 15,
    "monthly_payment_for_inactive": 12.5
}


def add_missing_monthly_payments(member, up_to_date: datetime):
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

            if title in ("F", "CB"):
                amount = MONTHLY_PAYMENTS["monthly_payment_for_active"]
            elif title == "iaCB":
                amount = MONTHLY_PAYMENTS["monthly_payment_for_inactive"]
            else:  # title == "AH" или любой другой
                amount = Decimal("0.00")

            if amount > 0:
                description = f"Monthly contribution for {ym} (title: {title})"
                member.add_transaction(date_str, description, -amount)

        current += relativedelta(months=1)
