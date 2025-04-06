import os
from datetime import datetime
from models.member import Member

# Path to the email template file used to generate personalized reports
TEMPLATE_PATH = os.path.join("config", "email_template.html")


def format_member_email(member: Member) -> str:
    """
    Generate a personalized HTML email report for a member by filling a template
    with their transaction data, balance, name, and title.

    The function loads a HTML file from the config folder that includes placeholders:
    - {{transactions}} — the table rows
    - {{balance}} — the current account balance
    - {{title}} — member's title (e.g., CB)
    - {{name}} — member's last name

    Returns:
        str: A fully formatted HTML email body ready to send.
    """

    # Load the HTML template from file
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Email template not found at {TEMPLATE_PATH}")

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template: str = f.read()

    # Sort the member's transactions by date (ascending)
    sorted_tx = sorted(member.transactions, key=lambda t: t["date"])

    # Create HTML table rows
    transaction_rows = []
    for tx in sorted_tx:
        # Format the transaction date as "dd.mm.yy"
        date_obj = datetime.strptime(tx["date"], "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d.%m.%y")

        # Format amount using European comma format and add € symbol
        amount = f'{tx["amount"]:.2f}'.replace(".", ",") + " €"

        # Prepare the transaction description
        description = tx["description"]

        # Add table row (<tr>)
        row = f"<tr><td>{date_formatted}</td><td>{amount}</td><td>{description}</td></tr>"
        transaction_rows.append(row)

    # Join all rows into a single string
    transactions_html = "\n".join(transaction_rows)

    # Format final balance string
    balance_str = f'{member.balance:.2f}'.replace(".", ",") + " €"

    # Replace all placeholders in the template
    filled = template.replace("{{transactions}}", transactions_html)
    filled = filled.replace("{{balance}}", balance_str)
    filled = filled.replace("{{title}}", member.title)
    filled = filled.replace("{{name}}", member.name)

    # Add current timestamp
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    filled = filled.replace("{{generated_at}}", generated_at)

    return filled
