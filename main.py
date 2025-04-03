import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

from _decimal import ROUND_HALF_UP

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

        except ValueError as error:
            print(f"{error}. Please try again")


def input_transaction_amount():
    while True:
        value = input("Enter amount (e.g. 10.50 or -5.00): ").strip()
        value = value.replace(",", ".")  # Replace comma with dot for decimal input to allow users using a comma)
        try:
            amount = Decimal(value)
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return amount
        except InvalidOperation:
            print("Invalid format. Please enter a number with up to 2 decimal places.")


def input_protocol_info():
    print("\nChoose protocol type:")
    print("1. AC")
    print("2. CC")
    print("3. GCC")
    print("4. FCC")

    while True:
        meeting_type_choice = input("Enter an option (1-4):")
        if meeting_type_choice == "1":
            meeting_type = "AC"
            break
        elif meeting_type_choice == "2":
            meeting_type = "CC"
            break
        elif meeting_type_choice == "3":
            meeting_type = "GCC"
            break
        elif meeting_type_choice == "4":
            meeting_type = "FCC"
            break
        else:
            print("Invalid choice. Please choose one of the options: 1, 2, 3, 4.")

    while True:
        meeting_number_choice = input("Enter the meeting number:").strip()
        if meeting_number_choice.isdigit():
            meeting_number = int(meeting_number_choice)
            if 1 <= meeting_number <= 20:
                break
        print("I dont think that you had more then 20 meetings =) Please enter a number between 1 and 20.")

    semester = input_semester_by_choice()

    return f"{meeting_number}. {meeting_type} {semester}"


def input_semester_by_choice():
    print("\nChoose semester type:")
    print("1. WiSe (Wintersemester)")
    print("2. SoSe (Sommersemester)")

    while True:
        sem_choice = input("Enter number (1 or 2): ").strip()
        if sem_choice == "1":
            sem_type = "WiSe"

            current_year = datetime.today().year
            print("\nChoose year:")
            print(f"1. {current_year - 2} / {current_year - 1}")
            print(f"2. {current_year - 1} / {current_year}")
            print(f"3. {current_year} / {current_year + 1}")
            print(f"4. {current_year + 1} / {current_year + 2}")

            while True:
                year_choice_index = input("Enter number (1-4): ").strip()
                if year_choice_index == "1":
                    year_for_ws = str(current_year - 2)[2:] + "/" + str(current_year - 1)[2:]
                elif year_choice_index == "2":
                    year_for_ws = str(current_year - 1)[2:] + "/" + str(current_year)[2:]
                elif year_choice_index == "3":
                    year_for_ws = str(current_year)[2:] + "/" + str(current_year + 1)[2:]
                elif year_choice_index == "4":
                    year_for_ws = str(current_year + 1)[2:] + "/" + str(current_year + 2)[2:]
                else:
                    print("Invalid choice. Please choose one of the options: 1, 2, 3, 4.")
                    continue
                break

            return f"{sem_type} {year_for_ws}"

        elif sem_choice == "2":
            sem_type = "SoSe"

            current_year = datetime.today().year
            print("\nChoose year:")
            print(f"1. {current_year - 2}")
            print(f"2. {current_year - 1}")
            print(f"3. {current_year}")
            print(f"4. {current_year + 1}")

            while True:
                year_choice_index = input("Enter number (1-4): ").strip()
                if year_choice_index == "1":
                    year_for_ss = str(current_year - 2)[2:]
                elif year_choice_index == "2":
                    year_for_ss = str(current_year - 1)[2:]
                elif year_choice_index == "3":
                    year_for_ss = str(current_year)[2:]
                elif year_choice_index == "4":
                    year_for_ss = str(current_year + 1)[2:]
                else:
                    print("Invalid choice. Please choose one of the options: 1, 2, 3, 4.")
                    continue
                break

            return f"{sem_type} {year_for_ss}"

        else:
            print("Invalid choice. Please enter 1 or 2.")


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
    print("0. Eine beliebige Transaktion hinzufügen ")
    print("1. Gutschrift")
    print("2. Getränkeabrechnung")
    print("3. Strafen")
    print("4. Rückzahlung aufgrund eines Antrags auf Auslagenrückerstattung")
    print("5. Beitrag für die Veranstaltung")

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
