from datetime import datetime
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


class Title(Enum):
    F = "F"
    CB = "CB"
    iaCB = "iaCB"
    AH = "AH"


class Member:
    def __init__(self, email: str, name: str, title: str, start_balance: float = 0.0):
        """
        Initialize a new Member with basic identity, status, and financial information.

        Parameters:
        - email (str): Unique identifier and contact of the member.
        - name (str): Last name of the member.
        - title (str): Current title/status (e.g., "CB", "AH", etc.).
        - start_balance (float): Starting account balance (default: 0.0).

        The title is validated against a predefined set of allowed values (Title enum).
        Title history is initialized with the provided title and the current creation date.
        """
        self.email = email
        self.name = name.strip()
        self.created_at = datetime.today().strftime("%Y-%m-%d")
        title = title.strip()
        if title not in Title._value2member_map_:
            allowed = ', '.join(t.value for t in Title)
            raise ValueError(f"Invalid title '{title}'. Allowed values: {allowed}")
        self.title_history = {title: self.created_at}
        self.start_balance = self._parse_balance(start_balance)
        self.transactions = []

    @property
    def title(self) -> str:
        """Returns the most recent title based on the last assigned date."""
        if not self.title_history:
            return "–"
        return sorted(self.title_history.items(), key=lambda i: i[1])[-1][0]

    @staticmethod
    def _parse_balance(value):
        """
        Safely converts the input value into a Decimal with two decimal places.
        Accepts numbers with a comma or dot as decimal separator.
        Returns Decimal('0.00') if parsing fails.
        """
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        try:
            normalized = str(value).replace(",", ".")
            return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0.00")

    def add_transaction(self, date: str, description: str, amount):
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
    def balance(self):
        total = self.start_balance
        for tx in self.transactions:
            total += self._parse_balance(tx["amount"])
        return total

    @property
    def to_dict(self) -> dict:
        """
        Serializes the Member instance into a dictionary format suitable for JSON storage.

        Returns:
            dict: A dictionary representation of the member, including:
                - name (str): Last name of the member
                - email (str): Unique email address
                - created_at (str): Account creation date in 'YYYY-MM-DD' format
                - title_history (dict): Mapping of titles to the dates they were assigned
                - start_balance (Decimal or float): Starting balance at time of creation
                - transactions (list): List of transaction records (each a dict)
        """
        return {
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
            "start_balance": float(self.start_balance),
            "transactions": self.transactions,
            "title_history": self.title_history
        }

    @staticmethod
    def from_dict(data: dict) -> "Member":
        """
        Reconstructs a Member instance from a dictionary with title history support.

        The most recent title (based on date in title_history) will be used for initialization.

        Args:
            data (dict): Serialized member data, including title_history, transactions, etc.

        Returns:
            Member: A fully restored Member object with loaded properties.
        """
        member: Member = Member(
            email=data["email"],
            name=data["name"],
            title=sorted(data["title_history"].items(), key=lambda i: i[1])[-1][0],
            start_balance=data.get("start_balance", 0.0)
        )
        member.created_at = data["created_at"]
        member.transactions = data.get("transactions", [])
        return member
