import os
import smtplib
import logging
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Template
from models.member import Member

logger = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def format_transaction_rows(transactions) -> str:
    """
    Format a list of transactions into HTML table rows.

    Args:
        transactions (List[Transaction]): List of transaction objects.

    Returns:
        str: HTML string with one <tr> per transaction.
    """
    rows = []
    for tx in sorted(transactions, key=lambda t: t.date):
        date_str = tx.date.strftime("%d.%m.%y")
        amount_str = f"{tx.amount:.2f}".replace(".", ",") + " €"
        rows.append(
            f"<tr><td>{date_str}</td><td>{amount_str}</td><td>{tx.description}</td></tr>"
        )
    return "\n".join(rows)


def format_member_email(member: Member, phone_number: str, template_path: str) -> str:
    """
    Generates an HTML email body for the given member using a Jinja2 template.

    Args:
        member (Member): The member to generate the report for.
        phone_number (str): Phone number to include in the email.
        template_path (str): Path to the Jinja2-compatible HTML template.

    Returns:
        str: HTML-formatted email body.

    Raises:
        FileNotFoundError: If the template file doesn't exist.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Email template not found at {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    return template.render(
        title=member.title,
        last_name=member.last_name,
        phone_number=phone_number or "",
        balance=f"{member.get_balance():.2f}".replace(".", ",") + " €",
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        transactions=format_transaction_rows(member.get_transactions()),
    )


def send_report_email(
    member: Member,
    sender_email: str,
    sender_password: str,
    phone_number: str,
    template_path: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
    dry_run: bool = False,
) -> bool:
    """
    Sends a balance report email to a member, using a rendered HTML template.

    Args:
        member (Member): The member to whom the email is sent.
        sender_email (str): Email of the sender.
        sender_password (str): Password (or app-specific) for SMTP login.
        phone_number (str): Phone number of sender (e.g. treasurer).
        template_path (str): Path to the email template (Jinja2 format).
        smtp_server (str): Hostname of the SMTP server.
        smtp_port (int): Port for SSL connection.
        dry_run (bool): If True, simulate sending without actually sending email.

    Returns:
        bool: True if email was sent successfully or simulated; False otherwise.

    Raises:
        ValueError: If the member email is invalid.
        RuntimeError: If sending the email fails.
    """
    if not EMAIL_REGEX.match(member.email):
        raise ValueError(f"Invalid email address: {member.email}")

    html = format_member_email(member, phone_number, template_path)
    subject = f"Kontostand vom {datetime.today().strftime('%d.%m.%Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = member.email
    msg.attach(MIMEText(html, "html"))

    if dry_run:
        logger.info(f"[DRY-RUN] Would send email to {member.email}")
        return False

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, member.email, msg.as_string())
        logger.info(f"Email successfully sent to {member.email}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending to {member.email}: {e}")
        raise RuntimeError(f"Failed to send email: {e}")
