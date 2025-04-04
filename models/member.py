from datetime import datetime
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP


class Title(Enum):
    F = "F"
    CB = "CB"
    iaCB = "iaCB"
    AH = "AH"


class Member:
    def __init__(self, email: str, name: str, title: str, start_balance: float = 0.0) -> object:
        self.email = email
        self.name = name.strip()

        title = title.strip()
        if title not in Title._value2member_map_:
            allowed = ', '.join(t.value for t in Title)
            raise ValueError(f"Invalid title '{title}'. Allowed values: {allowed}")
        self.title = title # "F", "CB", "iaCB", "AH"

        self.start_balance = self._parse_balance(start_balance)
        self.created_at = datetime.today().strftime("%Y-%m-%d")
        self.transactions = []

    @staticmethod
    def _parse_balance(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
    def to_dict(self):
        return {
            "email": self.email,
            "name": self.name,
            "title": self.title,
            "start_balance": float(self.start_balance),
            "transactions": self.transactions,
            "created_at": self.created_at
        }

    @staticmethod
    def from_dict(email, data):
        member: Member = Member(
            email=email,
            name=data.get("name"),
            title=data["title"],
            start_balance=data.get("start_balance", data.get("balance", 0.0))
        )
        member.active = data.get("active", True)
        member.created_at = data.get("created_at", datetime.today().strftime("%Y-%m-%d"))
        member.transactions = data.get("transactions", [])
        return member
