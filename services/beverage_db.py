from decimal import Decimal
from psycopg2.extras import execute_values
from db import get_cursor


def save_beverage_report(form, beverages, report_date) -> int:
    """
    Save a complete beverage report to the database.

    This function stores:
    1. The report metadata (report date),
    2. The beverage prices at the time of the report,
    3. All consumption entries (individual and event-based).

    Args:
        form (ImmutableMultiDict): The submitted form data from the POST request.
        beverages (list[dict]): List of current beverages with their prices.
        report_date (date): The selected report date.

    Returns:
        int: The ID of the newly created report in the beverage_reports table.
    """
    # Create a lookup for beverage prices
    beverage_map = {b["name"]: Decimal(str(b["price"])) for b in beverages}
    beverage_names = list(beverage_map.keys())

    with get_cursor() as cur:
        # Insert the report and retrieve its ID
        cur.execute(
            "INSERT INTO beverage_reports (report_date) VALUES (%s) RETURNING id;",
            (report_date,)
        )
        report_id = cur.fetchone()[0]

        # Save beverage prices for this report
        price_values = [(report_id, name, price) for name, price in beverage_map.items()]
        execute_values(
            cur,
            "INSERT INTO beverage_report_prices (report_id, beverage_name, price) VALUES %s",
            price_values
        )

        # Collect individual member entries
        individual_entries = []
        for key, values in form.items():
            if "_" not in key or key.startswith("event_"):
                continue
            email, bev = key.split("_", 1)
            if bev not in beverage_names:
                continue
            value_str = values.strip()
            count = int(value_str) if value_str.isdigit() else 0
            if count > 0:
                individual_entries.append((
                    report_id, False, email, None, bev, count
                ))

        # Collect event-based entries
        event_entries = []
        titles = form.getlist("event_title[]")
        for i, title in enumerate(titles):
            for bev in beverage_names:
                values = form.getlist(f"event_{bev}[]")
                if i < len(values) and values[i].isdigit():
                    count = int(values[i])
                    if count > 0:
                        event_entries.append((
                            report_id, True, None, title.strip(), bev, count
                        ))

        # Save all entries to the database
        all_entries = individual_entries + event_entries
        if all_entries:
            execute_values(
                cur,
                "INSERT INTO beverage_entries (report_id, is_event, email, event_title, beverage_name, count) VALUES %s",
                all_entries
            )

    return report_id
