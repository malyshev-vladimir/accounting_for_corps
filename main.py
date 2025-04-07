import smtplib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage

from models.member import Member, Title
from services.interface import input_valid_date, input_transaction_amount, input_protocol_info
from services.monthly_payments import add_missing_monthly_payments
from services.email_templates import format_member_email
from services.settings_loader import load_settings
from services.members_io import load_all_members, save_all_members

FILENAME = 'data/members.json'


def change_member_title():
    """
    Allows the user to change a member's title by adding a new entry to their title_history.
    Prompts the user to select a member and choose a new title.
    """
    members = load_all_members()
    if not members:
        print("No members found.")
        return

    # Display members with indexes
    emails = list(members.keys())
    print("\n Members:")
    for i, email in enumerate(emails, start=1):
        member = members[email]
        print(f"{i}. {member.name} ({email})")

    try:
        index = int(input("Select member number: "))
        if not 1 <= index <= len(emails):
            raise ValueError("Invalid selection.")
    except ValueError as e:
        print(f"Invalid input. {e}")
        return

    selected_email = emails[index - 1]
    member = members[selected_email]

    # Show current title history
    print("\nCurrent title history:")
    for title, date in member.title_history.items():
        print(f"- {title} since {date}")

    # Prompt for new title
    print("\nAvailable titles:", ', '.join([t.value for t in Title]))
    new_title = input("Enter the new title: ").strip()

    if new_title not in Title._value2member_map_:
        print(f"Invalid title '{new_title}'.")
        return

    today = datetime.today().strftime("%Y-%m-%d")
    member.title_history[new_title] = today

    save_all_members(members)
    print(f"[✓] Title '{new_title}' added for {member.name} on {today}")


def send_email_report(to_email: str, subject: str, body: str):
    """
    Sends an email to the specified recipient using credentials from config/settings.json.

    Parameters:
    - to_email (str): Recipient's email address
    - subject (str): Subject line of the email
    - body (str): Plain-text body of the email
    """

    # Load credentials from settings file
    settings = load_settings()
    sender_email = settings["email_address"]
    sender_password = settings["email_password"]

    # Create and configure the email message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content(body, subtype="html")

    # Connect to SMTP server via SSL and send the email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)


def send_report_to_member():
    """
    Prompt the user to select a member from the list and send them a personalized
    account report via email. The email body is generated from a template.
    """

    # Load all members from the data file
    members = load_all_members()
    if not members:
        print("No members found.")
        return

    # Present a numbered list of members (by email + name)
    emails = list(members.keys())
    for i, email in enumerate(emails, 1):
        print(f"{i}. {members[email].title} {members[email].name} ({email})")

    try:
        index = int(input("Select member number: "))
        if not 1 <= index <= len(emails):
            raise ValueError("Invalid number.")
    except ValueError:
        print("Invalid input. Please enter a valid number from the list.")
        return

    # Get selected member
    selected_email = emails[index - 1]
    member = members[selected_email]

    # Add a personalized email subject line
    date_str = datetime.now().strftime("%d.%m.%Y")
    subject = f"CC-Kontostand zum {date_str} ({member.title} {member.name})"

    # Generate the email body from the template
    body = format_member_email(member)

    # Try sending the email and report result to user
    try:
        send_email_report(member.email, subject, body)
        print(f"\n[✓] Email was successfully sent to {member.title} {member.name} ({member.email})")
    except Exception as e:
        print(f"\n[✗] Failed to send email to {member.title} {member.name} ({member.email}): {e}")


def check_all_members_payments():
    members = load_all_members()
    for member in members.values():
        add_missing_monthly_payments(member, datetime.today())
    save_all_members(members)
    print("Loading! Monthly payments checked and added.")


def add_transaction_to_member():
    members = load_all_members()
    if not members:
        print("No members found.")
        return

    names = list(members.keys())
    print("\n Members:")
    for i, name in enumerate(names, start=1):
        print(f"{i}. {name}")

    try:
        index = int(input("Enter the number of the member: "))
        if not 1 <= index <= len(names):
            raise ValueError("invalid number.")
    except ValueError as e:
        print(f"{e}")
        return

    name = names[index - 1]
    member = members[name]

    print("Enter transaction date: ")
    date = input_valid_date()

    print("\n  Choose transaction type:")
    print("\t 0. Eine beliebige Transaktion hinzufügen ")
    print("\t 1. Gutschrift")
    print("\t 2. Getränkeabrechnung")
    print("\t 3. Strafen")
    print("\t 4. Rückzahlung aufgrund eines Antrags auf Auslagenrückerstattung")
    print("\t 5. Beitrag für die Veranstaltung")

    while True:
        transaction_type = input("Enter number of the transaction (0 - 5): ").strip()

        if transaction_type == "0":
            description = input("Description: ").strip()
            break

        elif transaction_type == "1":
            print("Enter date of the \"Gutschrift\"-transaction:")
            date_of_transaction = input_valid_date()
            description = f"Gutschrift von {date_of_transaction}"
            break

        elif transaction_type == "2":
            print("Enter the date of the \"Getränkeabrechnung\":")
            action_date = input_valid_date()
            description = f"Getränkeabrechnung von {action_date}"
            break

        elif transaction_type == "3":
            print("Enter the protocols info: ")
            protocol_info = input_protocol_info()
            description = f"Strafe von {protocol_info})"
            break

        elif transaction_type == "4":
            print("Enter the date of the \"Antrag auf Auslagenrückerstattung\" in CC-mail")
            action_date = input_valid_date()
            description = f"AaA von {action_date}"
            break

        elif transaction_type == "5":
            print("Enter the date of the event:")
            action_date = input_valid_date()
            event = input("Enter the event: ")
            description = event + f" von {action_date}"
            break

        else:
            print("Invalid choice. Please choose one of the options: 1, 2, 3, 4.")

    amount = input_transaction_amount()

    member.add_transaction(date, description, amount)
    save_all_members(members)
    print(f"Transaction added to [ {date}, {description}, {amount} ]")


def add_member():
    email = input("  => Email address: ").strip()
    if "@" not in email or "." not in email:
        print("Invalid email format.")
        return
    
    name: str = input("Member name (must be unique): ").strip()
    
    allowed_titles = ", ".join(t.value for t in Title)
    print(f"Title must be one of the following: {allowed_titles}")
    title = input("Title: ").strip()

    balance_input = input("Balance (e.g. 10.50): ").strip()
    try:
        balance = Decimal(balance_input)
    except (InvalidOperation, ValueError):
        print("Invalid balance format. Please enter a number like 12.34.")
        return

    members = load_all_members()

    if email in members:
        print(f"A member with email '{email}' already exists ({title} {name}).")
        return

    try:
        member = Member(name, title, email, balance)
    except ValueError as e:
        print(f"{e}")
        return

    members[email] = member
    save_all_members(members)
    print(f"Member '{name}' with '{email}' has been added.")


def view_members():
    members = load_all_members()
    if not members:
        print("No members found.")
        return
    print("\n Members list:")
    for email, member in members.items():
        print(f"-{member.title} {member.name} ({email}): balance={member.balance}")


def main():
    check_all_members_payments()

    while True:
        print("\n Menu:")
        print("1. Add member")
        print("2. View all members")
        print("3. Add transaction to member")
        print("4. Send email report to a member")
        print("5. Change member`s title")
        print("6. Exit")

        choice = input("Choose an option (1–6): ").strip()

        if choice == "1":
            add_member()
        elif choice == "2":
            view_members()
        elif choice == "3":
            add_transaction_to_member()
        elif choice == "4":
            send_report_to_member()
        elif choice == "5":
            change_member_title()
        elif choice == "6":
            print("Goodbye! =)")
            break
        else:
            print("Invalid option. Please choose 1, 2, 3, 4 or 5.")


if __name__ == "__main__":
    main()
