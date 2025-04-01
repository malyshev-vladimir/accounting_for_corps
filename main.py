import json
import os
from decimal import Decimal, InvalidOperation
from models.member import Member, Title

FILENAME = 'data/members.json'


def load_members():
    if not os.path.exists(FILENAME):
        return {}
    with open(FILENAME, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {name: Member.from_dict(name, info) for name, info in data.items()}


def save_members(members: dict):
    data = {name: member.to_dict() for name, member in members.items()}
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
    while True:
        print("\n Menu:")
        print("1. Add member")
        print("2. View all members")
        print("3. Exit")

        choice = input("Choose an option (1–3): ").strip()

        if choice == "1":
            add_member()
        elif choice == "2":
            view_members()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1, 2, or 3.")


if __name__ == "__main__":
    main()
