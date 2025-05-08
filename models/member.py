from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List

from db import get_cursor
from models.transaction import Transaction
from models.validators import parse_decimal
from services.transactions_db import load_transactions_by_email


class Title(Enum):
    F = "F"
    CB = "CB"
    iaCB = "iaCB"
    AH = "AH"

    def full(self):
        return {
            Title.F: "Fuchs",
            Title.CB: "Corpsbruder",
            Title.iaCB: "inaktiver CB",
            Title.AH: "Alter Herr"
        }[self]


class Member:
    def __init__(self,
                 email: str,
                 last_name: str,
                 first_name: str = "",
                 title: str = "F",
                 is_resident: bool = True,
                 created_at: date = None,
                 start_balance: Decimal = Decimal("0.00"),
                 ):
        """
        Initialize a new Member with identity, title, residency, and financial data.

        Args:
            email (str): Unique identifier and contact email of the member.
            last_name (str): Last name of the member.
            first_name (str): First name of the member (default: "").
            title (str): Current title/status of the member default: "F").
            is_resident (bool): Whether the member lives in the community house (default: True).
            created_at (date): Creating date of the member (default: today)
            start_balance (Decimal): Starting account balance (default: 0.00).
        """

        self.email = email
        self.last_name = last_name.strip()
        self.first_name = first_name.strip()
        self.title = title
        self.is_resident = is_resident
        self.created_at = created_at or datetime.today().date()
        self.start_balance = parse_decimal(start_balance)

    def get_transactions(self) -> List[Transaction]:
        """
        Load all transactions linked to this member from the database.

        Returns:
            list[Transaction]: List of Transaction objects.
        """
        return load_transactions_by_email(self.email)

    def get_balance(self) -> Decimal:
        """
        Return the current account balance by summing all transactions up to today.

        Returns:
            Decimal: Starting balance plus all transaction amounts.
        """
        total = Decimal(self.start_balance)
        for tx in self.get_transactions():
            if tx.date <= date.today():
                total += tx.amount
        return total

    def change_title(self, new_title: str, changed_by: str = None) -> None:
        """
        Change the member's title and log the change in the database only if the title changes.

        Args:
            new_title (str): New title to assign.
            changed_by (str): Email of the person who made the change (default: admin).
        """
        # Normalize current title (convert Enum to string if needed)
        current_title = self.title.value if isinstance(self.title, Title) else self.title

        # If the title hasn't changed, skip the update and logging
        if new_title == current_title:
            return  # No change, skip update and logging

        # If the title has changed, update it
        self.title = new_title

        # Update the title in the database
        with get_cursor() as cur:
            cur.execute("""
                    UPDATE members
                    SET title = %s
                    WHERE email = %s
                """, (new_title, self.email))

            # Log the title change
            cur.execute("""
                    INSERT INTO title_changes (member_email, changed_at, new_title, changed_by)
                    VALUES (%s, %s, %s, %s)
                """, (self.email, datetime.now(), new_title, changed_by))

    def change_residency(self, new_resident: bool, changed_by: str = None) -> None:
        """
        Change the residency status of the member and log the change only if the residency status changes.

        Args:
            new_resident (bool): New residency status to assign.
            changed_by (str): Email of the person who made the change (default: admin).
        """
        if new_resident == self.is_resident:
            return  # No change, skip

        self.is_resident = new_resident
        now = datetime.now()

        with get_cursor() as cur:
            # Update current value in the members table
            cur.execute("""
                UPDATE members
                SET is_resident = %s
                WHERE email = %s
            """, (new_resident, self.email))

            # Log the change in residency_changes
            cur.execute("""
                INSERT INTO residency_changes (member_email, changed_at, new_resident, changed_by)
                VALUES (%s, %s, %s, %s)
            """, (self.email, now, new_resident, changed_by))

    def create_transaction(self,
                           transaction_date: date,
                           description: str,
                           amount: Decimal,
                           changed_by: str) -> Transaction:
        """
        Create a new transaction for this member, save it to the database, and return it.

        Args:
            transaction_date (date): The date of the transaction.
            description (str): Description of the transaction.
            amount (Decimal): Transaction amount (positive for income, negative for expense).
            changed_by (str): Email of the user creating the transaction (for audit logging).

        Returns:
            Transaction: The created and saved transaction object.
        """
        transaction = Transaction(
            transaction_date=transaction_date,
            description=description,
            amount=amount,
            member_email=self.email
        )
        transaction.save(changed_by=changed_by)
        return transaction

    def save_to_db(self) -> None:
        """
        Save the core member data into the database.

        If the member already exists (based on email), their
        first name, last name, title, residency status, and
        starting balance are updated.

        Additionally, if the member is new, their initial title
        and residency status are recorded in the corresponding history tables.
        """
        with get_cursor() as cur:
            # Try to insert or update the member
            cur.execute("""
                INSERT INTO members (
                    email, first_name, last_name, title, is_resident, created_at, start_balance
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    title = EXCLUDED.title,
                    is_resident = EXCLUDED.is_resident,
                    start_balance = EXCLUDED.start_balance
                    -- created_at intentionally not updated to preserve original creation time
            """, (
                self.email,
                self.first_name,
                self.last_name,
                self.title,
                self.is_resident,
                self.created_at,
                float(self.start_balance)
            ))

            # Check if it's a new member by querying title_changes
            cur.execute("SELECT 1 FROM title_changes WHERE member_email = %s LIMIT 1", (self.email,))
            title_exists = cur.fetchone()

            if not title_exists:
                # Save initial title history
                cur.execute("""
                    INSERT INTO title_changes (member_email, changed_at, new_title, changed_by)
                    VALUES (%s, %s, %s, %s)
                """, (
                    self.email,
                    datetime.now(),
                    self.title,
                    self.email  # assuming self.email is the one creating their own record
                ))

            # Check if it's a new member by querying residency_changes
            cur.execute("SELECT 1 FROM residency_changes WHERE member_email = %s LIMIT 1", (self.email,))
            residency_exists = cur.fetchone()

            if not residency_exists:
                # Save initial residency status
                cur.execute("""
                    INSERT INTO residency_changes (member_email, changed_at, new_resident, changed_by)
                    VALUES (%s, %s, %s, %s)
                """, (
                    self.email,
                    datetime.now(),
                    self.is_resident,
                    self.email
                ))
