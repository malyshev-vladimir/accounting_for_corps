from datetime import datetime
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP


class Title(Enum):
    CB = "CB"
    iaCB = "iaCB"
    AH = "AH"


class Member:
    def __init__(self, name: str, title: str, active: bool = True, start_balance: float = 0.0):
        title = title.strip()
        if title not in Title._value2member_map_:
            allowed = ', '.join(t.value for t in Title)
            raise ValueError(f"Invalid title '{title}'. Allowed values: {allowed}")

        self.name = name.strip()
        self.title = title  # "CB", "iaCB", "AH"
        self.active = active
        self.start_balance = self._parse_balance(start_balance)
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
            "title": self.title,
            "active": self.active,
            "start_balance": float(self.start_balance),
            "transactions": self.transactions
        }

    @staticmethod
    def from_dict(name, data):
        member: Member = Member(
            name,
            data["title"],
            data["active"],
            data["start_balance"],
        )
        member.transactions = data.get("transactions", [])
        return member
