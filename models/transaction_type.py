from enum import Enum


class TransactionType(Enum):
    CUSTOM = 1
    DRINKS = 2
    CREDIT = 3
    FINE = 4
    REIMBURSEMENT = 5

    def label(self) -> str:
        return {
            TransactionType.CUSTOM: "Beliebig",
            TransactionType.DRINKS: "Getränkeabrechnung",
            TransactionType.CREDIT: "Gutschrift",
            TransactionType.FINE: "Strafe",
            TransactionType.REIMBURSEMENT: "Rückerstattung (AaA)",
        }.get(self, "Unbekannt")
