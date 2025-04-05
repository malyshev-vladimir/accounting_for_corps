import json
import os
from services.interface import input_valid_date, input_transaction_amount, input_protocol_info
from datetime import datetime
from decimal import Decimal, InvalidOperation

from models.member import Member, Title
from services.monthly_payments import add_missing_monthly_payments

FILENAME = 'data/members.json'


def check_all_members_payments():
    members = load_members()
    for member in members.values():
        add_missing_monthly_payments(member, datetime.today())
    save_members(members)
    print("Loading! Monthly payments checked and added.")


def add_transaction_to_member():
    members = load_members()
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
    save_members(members)
    print(f"Transaction added to [ {date}, {description}, {amount} ]")


def load_members():
    if not os.path.exists(FILENAME):
        return {}
    with open(FILENAME, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {email: Member.from_dict(email, info) for email, info in data.items()}


def save_members(members: dict):
    data = {email: member.to_dict for email, member in members.items()}
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


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

    members = load_members()

    if email in members:
        print(f"A member with email '{email}' already exists ({title} {name}).")
        return

    try:
        member = Member(name, title, email, balance)
    except ValueError as e:
        print(f"{e}")
        return

    members[email] = member
    save_members(members)
    print(f"Member '{name}' with '{email}' has been added.")


def view_members():
    members = load_members()
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
        print("4. Exit")

        choice = input("Choose an option (1–4): ").strip()

        if choice == "1":
            add_member()
        elif choice == "2":
            view_members()
        elif choice == "3":
            add_transaction_to_member()
        elif choice == "4":
            print("Goodbye! =)")
            break
        else:
            print("Invalid option. Please choose 1, 2, or 3.")


if __name__ == "__main__":
    main()
