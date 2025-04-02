import json
import os
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


def input_valid_date():
    while True:
        try:
            year = int(input("Year (e.g. 2025): "))
            if year < 2023:
                raise ValueError("Year must be 2023 or later.")
            mouth = int(input("Mouth (1 - 12): "))
            if not 1 <= mouth <= 12:
                raise ValueError("Mouth must be between 1 and 12.")
            day = int(input("Day (1 - 31): "))
            if not 1 <= day <= 31:
                raise ValueError("Day must be between 1 and 31.")

            date_obj = datetime(year, mouth, day)
            return date_obj.strftime("%Y-%m-%d")

        except ValueError as e:
            print(f"Error. Please try again")


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

    description = input("Description: ").strip()
    amount_input = input("Amount (use '-' for expenses): ").strip()

    try:
        amount = Decimal(amount_input)
        member.add_transaction(date, description, amount)
        save_members(members)
        print(f"Transaction added to {name}.")
    except Exception as e:
        print("Error: {e}")


def load_members():
    if not os.path.exists(FILENAME):
        return {}
    with open(FILENAME, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {name: Member.from_dict(name, info) for name, info in data.items()}


def save_members(members: dict):
    data = {name: member.to_dict for name, member in members.items()}
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def add_member():
    name = input("Member name (must be unique): ").strip()
    allowed_titles = ", ".join(t.value for t in Title)
    print(f"Title must be one of the following: {allowed_titles}")
    title = input("Title: ").strip()

    active_input = input("Is the member active? (yes/no, default yes): ").strip().lower()
    active = True if active_input in ("", "yes", "y") else False

    balance_input = input("Balance (e.g. 10.50): ").strip()
    try:
        balance = Decimal(balance_input)
    except (InvalidOperation, ValueError):
        print("Invalid balance format. Please enter a number like 12.34.")
        return

    members = load_members()

    if name in members:
        print(f"A member named '{name}' already exists.")
        return

    try:
        member = Member(name, title, active, balance)
    except ValueError as e:
        print(f"{e}")
        return

    members[name] = member
    save_members(members)
    print(f"Member '{name}' has been added.")


def view_members():
    members = load_members()
    if not members:
        print("No members found.")
        return
    print("\n Members list:")
    for name, member in members.items():
        print(f"-{member.title} {name}: active={member.active}, balance={member.balance}")


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
