import os
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

from models.member import Member

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_SENDER = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

# Path to the email template file used to generate personalized reports
TEMPLATE_PATH = os.path.join("config", "emails", "balance_report.html")


def send_report_email(member: Member):
    """
    Sends an HTML email with the member's transaction report.
    """
    html = format_member_email(member)

    today_str = datetime.today().strftime("%d.%m.%Y")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Kontostand vom {today_str}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = member.email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, member.email, msg.as_string())


def format_member_email(member: Member) -> str:
    """
    Generate a personalized HTML email report for a member by filling a template
    with their transaction data, balance, name, and title.

    The function loads an HTML file from the config folder that includes placeholders:
    - {{transactions}} — the table rows
    - {{balance}} — the current account balance
    - {{title}} — member's title (e.g., CB)
    - {{last_name}} — member's last name
    - {{phone_number}}  — kassenwart's phone number

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
    filled = filled.replace("{{last_name}}", member.last_name)
    filled = filled.replace("{{phone_number}}", PHONE_NUMBER)

    # Add current timestamp
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    filled = filled.replace("{{generated_at}}", generated_at)

    return filled
