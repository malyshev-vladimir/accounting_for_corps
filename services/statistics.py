import io
import base64
import matplotlib.pyplot as plt
from datetime import date
from collections import OrderedDict
from dateutil.relativedelta import relativedelta

from services.members_db import load_all_members


def calculate_monthly_debt_trend() -> tuple[list[str], list[float], list[float]]:
    """
    Calculate the total community balance (i.e., debt) for the first day of each month,
    over the past two years up to the current month.

    Returns:
        tuple:
            - labels (list of str): month labels in "YYYY-MM" format
            - totals (list of float): total balance on each month's first day
            - deltas (list of float): difference compared to the previous month
    """
    members = load_all_members()
    if not members:
        return [], [], []

    # Define monthly range: from 2 years ago to now
    first_date = (date.today().replace(day=1) - relativedelta(years=2))
    today = date.today().replace(day=1)

    checkpoints = OrderedDict()
    current = first_date
    while current <= today:
        checkpoints[current] = 0.0
        current_month = current.month + 1 if current.month < 12 else 1
        current_year = current.year + 1 if current.month == 12 else current.year
        current = date(current_year, current_month, 1)

    for check_date in checkpoints:
        total = sum(member.get_balance_at(check_date) for member in members)
        checkpoints[check_date] = round(total, 2)

    labels = [d.strftime("%Y-%m") for d in checkpoints]
    totals = list(checkpoints.values())
    deltas = [0.0] + [round(totals[i] - totals[i - 1], 2) for i in range(1, len(totals))]

    return labels, totals, deltas


def build_debt_chart(labels: list[str], totals: list[float], deltas: list[float]) -> str:
    """
    Generate a line and bar chart showing the community's monthly debt trend.

    Args:
        labels (list of str): Month labels in "YYYY-MM" format.
        totals (list of float): Cumulative debt values per month.
        deltas (list of float): Changes in debt relative to the previous month.

    Returns:
        str: A base64-encoded PNG image suitable for embedding in HTML.
    """
    fig, ax = plt.subplots(figsize=(10, 4))

    # Line plot for total debt
    ax.plot(labels, totals, label="Gesamtschulden", color="red", marker="o")

    # Bar chart for monthly differences
    ax.bar(labels, deltas, label="Änderung", alpha=0.3, color="orange")

    ax.set_ylabel("€")
    ax.set_title("Monatliche Entwicklung der Schulden")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the figure to a buffer and encode as base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    plt.close(fig)

    return image_base64
