from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from services.members_io import load_all_members, save_all_members
from models.member import Title


def change_member_title():
    """
    Allows the user to assign a new title to a selected member.
    The new title is added to the member's title_history with the current date.
    """
    members = load_all_members()
    if not members:
        print("No members found.")
        return

    # Show list of members to choose from
    emails = list(members.keys())
    for i, email in enumerate(emails, 1):
        m = members[email]
        print(f"{i}. {m.title} {m.name} ({email})")

    try:
        index = int(input("Select member number: "))
        if not 1 <= index <= len(emails):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        return

    selected_email = emails[index - 1]
    member = members[selected_email]

    # Ask for new title
    new_title = input("Enter new title: ").strip()
    if new_title not in Title._value2member_map_:
        allowed = ', '.join(t.value for t in Title)
        print(f"Invalid title. Allowed values: {allowed}")
        return

    today = datetime.today().strftime("%Y-%m-%d")
    member.title_history[new_title] = today

    # Save updated member data
    save_all_members(members)

    print(f"[✓] Title '{new_title}' assigned to {member.name} ({member.email}) as of {today}.")


def input_valid_date():
    while True:
        try:
            year = int(input("  => Year (e.g. 2025): "))
            if year < 2023:
                raise ValueError("Year must be 2023 or later.")
            mouth = int(input("  => Mouth (1 - 12): "))
            if not 1 <= mouth <= 12:
                raise ValueError("Mouth must be between 1 and 12.")
            day = int(input("  => Day (1 - 31): "))
            if not 1 <= day <= 31:
                raise ValueError("Day must be between 1 and 31.")

            date_obj = datetime(year, mouth, day)
            return date_obj.strftime("%Y-%m-%d")

        except ValueError as error:
            print(f"{error}. Please try again")


def input_transaction_amount(prompt="Enter amount (e.g. 12.50 or 12,50): ") -> Decimal:
    """
    Prompts the user to enter a monetary amount and returns a Decimal rounded to 2 decimal places.
    Accepts both comma and dot as decimal separator.
    Repeats prompt until valid input is entered.
    """
    while True:
        user_input = input(prompt).strip().replace(",", ".")
        try:
            amount = Decimal(user_input).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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
        meeting_type_choice = input("  => Enter an option (1-4):")
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
        sem_choice = input("  => Enter number (1 or 2): ").strip()
        if sem_choice == "1":
            sem_type = "WiSe"

            current_year = datetime.today().year
            print("\nChoose year:")
            print(f"1. {current_year - 2} / {current_year - 1}")
            print(f"2. {current_year - 1} / {current_year}")
            print(f"3. {current_year} / {current_year + 1}")
            print(f"4. {current_year + 1} / {current_year + 2}")

            while True:
                year_choice_index = input("  => Enter number (1-4): ").strip()
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
                year_choice_index = input("  => Enter number (1-4): ").strip()
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

                return f"{sem_type} {year_for_ss}"

        else:
            print("Invalid choice. Please enter 1 or 2.")
