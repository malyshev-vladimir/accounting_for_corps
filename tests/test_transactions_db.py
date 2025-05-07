from datetime import date
from decimal import Decimal
from unittest.mock import patch
from services import transactions_db
from models.transaction_type import TransactionType


def test_load_transactions_by_email():
    mock_rows = [
        [1, date(2025, 5, 1), "Test 1", Decimal("10.00"), TransactionType.CUSTOM],
        [2, date(2025, 6, 1), "Test 2", Decimal("-5.00"), TransactionType.MONTHLY_FEE],
    ]

    class FakeCursor:
        def execute(self, query, params=None): self.executed = True

        def fetchall(self): return mock_rows

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("services.transactions_db.get_cursor", return_value=FakeCursor()):
        txs = transactions_db.load_transactions_by_email("test@example.com")
        assert len(txs) == 2
        assert txs[0].id == 1
        assert txs[0].description == "Test 1"
        assert txs[1].amount == Decimal("-5.00")


def test_load_transactions_by_type():
    mock_rows = [
        [7, date(2025, 4, 1), "Fee April", Decimal("-15.00"), TransactionType.MONTHLY_FEE],
    ]

    class FakeCursor:
        def execute(self, query, params=None): self.executed = True

        def fetchall(self): return mock_rows

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("services.transactions_db.get_cursor", return_value=FakeCursor()):
        txs = transactions_db.load_transactions_by_type("test@example.com", TransactionType.MONTHLY_FEE.value)
        assert len(txs) == 1
        assert txs[0].description == "Fee April"
        assert txs[0].type == TransactionType.MONTHLY_FEE


def test_load_transaction_by_id_success():
    mock_row = ["test@example.com", date(2025, 3, 1), "Something", Decimal("5.00"), TransactionType.CUSTOM]

    class FakeCursor:
        def execute(self, query, params=None): self.executed = True

        def fetchone(self): return mock_row

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("services.transactions_db.get_cursor", return_value=FakeCursor()):
        tx = transactions_db.load_transaction_by_id(42)
        assert tx.id == 42
        assert tx.member_email == "test@example.com"
        assert tx.amount == Decimal("5.00")


def test_load_transaction_by_id_not_found():
    class FakeCursor:
        def execute(self, query, params=None): pass

        def fetchone(self): return None

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("services.transactions_db.get_cursor", return_value=FakeCursor()):
        try:
            transactions_db.load_transaction_by_id(999)
        except ValueError as e:
            assert "not found" in str(e).lower()
        else:
            assert False, "Expected ValueError"
