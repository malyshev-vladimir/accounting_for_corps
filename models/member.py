from enum import Enum
from decimal import Decimal, ROUND_HALF_UP


class Title(Enum):
    CB = "CB"
    iaCB = "iaCB"
    AH = "AH"


class Member:
    def __init__(self, name: str, title: str, active: bool = True, balance: float = 0.0):
        title = title.strip()
        if title not in Title._value2member_map_:
            allowed = ', '.join(t.value for t in Title)
            raise ValueError(f"Invalid title '{title}'. Allowed values: {allowed}")

        self.name = name.strip()
        self.title = title  # "CB", "iaCB", "AH"
        self.active = active
        self.balance = self._parse_balance(balance)

    @staticmethod
    def _parse_balance(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def to_dict(self):
        return {
            "title": self.title,
            "active": self.active,
            "balance": float(self.balance)
        }

    @staticmethod
    def from_dict(name, data):
        return Member(
            name,
            data["title"],
            data["active"],
            data["balance"]
        )
