from datetime import datetime
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


class Title(Enum):
    F = "F"
    CB = "CB"
    iaCB = "iaCB"
    AH = "AH"


class Member:
    def __init__(self, email: str, last_name: str, first_name: str = "",
                 title: str = "F", is_resident: bool = True, start_balance: float = 0.0):
        """
        Initialize a new Member with identity, title, residency, and financial data.

        Args:
            email (str): Unique identifier and contact email of the member.
            last_name (str): Last name of the member.
            first_name (str): First name of the member (optional).
            title (str): Current title/status of the member (e.g., "CB", "AH").
            is_resident (bool): Whether the member lives in the community house.
            start_balance (float): Starting account balance (default is 0.0).
        """
        self.email = email
        self.last_name = last_name.strip()
        self.first_name = first_name.strip()
        self.title = title
        self.is_resident = is_resident
        self.created_at = datetime.today().strftime("%Y-%m-%d")
        self.title_history = {self.created_at: title}
        self.resident_history = {self.created_at: is_resident}
        self.start_balance = self._parse_balance(start_balance)
        self.transactions = []

    @staticmethod
    def _get_value_at(history: dict, date_str: str):
        """
        Get the value from a history dictionary that was active at the given date.

        Args:
            history (dict): Dictionary with date keys (YYYY-MM-DD) and values.
            date_str (str): Target date in 'YYYY-MM-DD' format.

        Returns:
            Any: The value (e.g., title or resident status) valid at that date.
        """
        date = datetime.strptime(date_str, "%Y-%m-%d")
        sorted_items = sorted(history.items(), key=lambda x: x[0])

        current_value = sorted_items[0][1]
        for d_str, val in sorted_items:
            d = datetime.strptime(d_str, "%Y-%m-%d")
            if d <= date:
                current_value = val
            else:
                break
        return current_value

    def get_title_at(self, date_str: str) -> str:
        """Return the member's title valid at the specified date"""
        return self._get_value_at(self.title_history, date_str)

    def get_resident_status_at(self, date_str: str) -> bool:
        """Return whether the member was a resident on the specified date"""
        return self._get_value_at(self.resident_history, date_str)

    @staticmethod
    def _parse_balance(value) -> Decimal:
        """
        Convert a value into a Decimal with two decimal places.

        Accepts numbers with dot or comma as decimal separator.
        If conversion fails, returns Decimal('0.00').

        Args:
            value (Any): A numeric value or string to convert.

        Returns:
            Decimal: A safely parsed monetary value.
        """
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        try:
            normalized = str(value).replace(",", ".")
            return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0.00")

    def add_transaction(self, date: str, description: str, amount):
        """
        Add a transaction record to the member's transaction list.

        Args:
            date (str): Transaction date in 'YYYY-MM-DD' format.
            description (str): Description of the transaction.
            amount (float | str | Decimal): Transaction amount (positive or negative).

        Raises:
            ValueError: If the date format is invalid.
        """
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: '{date}'. Expected YYYY-MM-DD.")

        amount = self._parse_balance(amount)
        self.transactions.append({
            "date": date,
            "description": description,
            "amount": float(amount)
        })

    @property
    def balance(self) -> Decimal:
        """
        Calculate the current account balance.

        Returns:
            Decimal: Starting balance plus sum of all transaction amounts.
        """
        total = self.start_balance
        for tx in self.transactions:
            total += self._parse_balance(tx["amount"])
        return total

    @property
    def to_dict(self) -> dict:
        """
        Convert the Member object to a dictionary for storage or serialization.

        Returns:
            dict: Dictionary representation of the member.
        """
        return {
            "email": self.email,
            "last_name": self.last_name,
            "first_name": self.first_name,
            "title": self.title,
            "is_resident": self.is_resident,
            "created_at": self.created_at,
            "title_history": self.title_history,
            "resident_history": self.resident_history,
            "start_balance": float(self.start_balance),
            "transactions": self.transactions
        }

    @staticmethod
    def from_dict(data: dict) -> "Member":
        """
        Create a Member instance from a dictionary.

        Uses the most recent title and resident status from their histories.

        Args:
            data (dict): Dictionary containing member data.

        Returns:
            Member: Reconstructed Member object.
        """
        latest_title_date = max(data["title_history"].keys())
        latest_resident_date = max(data["resident_history"].keys())

        member = Member(
            email=data.get("email"),
            last_name=data.get("last_name", ""),
            first_name=data.get("first_name", ""),
            title=data["title_history"][latest_title_date],
            is_resident=data["resident_history"][latest_resident_date],
            start_balance=data.get("start_balance", 0.0)
        )

        member.created_at = data.get("created_at", latest_title_date)
        member.title_history = data.get("title_history", {})
        member.resident_history = data.get("resident_history", {})
        member.transactions = data.get("transactions", [])

        return member
