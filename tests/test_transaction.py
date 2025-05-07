from datetime import date
from decimal import Decimal
from unittest.mock import patch
from models.transaction import Transaction
from models.transaction_type import TransactionType


def test_transaction_save():
    logs = {}
    fake_id = 42

    class FakeCursor:
        def execute(self, query, params=None):
            logs["executed"] = (query.strip().lower(), params)

        def fetchone(self):
            return [fake_id]

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.transaction.get_cursor", return_value=FakeCursor()):
        with patch("models.transaction.log_transaction_change") as mock_log:
            tx = Transaction(
                transaction_date=date(2025, 5, 1),
                description="Test payment",
                amount=Decimal("12.34"),
                member_email="test@example.com",
                transaction_type=TransactionType.CUSTOM
            )
            tx.save(changed_by="admin@example.com")

            assert tx.id == fake_id
            assert "insert into transactions" in logs["executed"][0]
            mock_log.assert_called_once()
            assert "created transaction" in mock_log.call_args[0][3].lower()


def test_transaction_update():
    logs = {}

    class FakeCursor:
        def execute(self, query, params=None):
            logs["executed"] = (query.strip().lower(), params)

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.transaction.get_cursor", return_value=FakeCursor()):
        with patch("models.transaction.log_transaction_change") as mock_log:
            tx = Transaction(
                transaction_date=date(2025, 5, 1),
                description="Old description",
                amount=Decimal("10.00"),
                member_email="test@example.com",
                transaction_id=123
            )

            tx.update(
                new_date=date(2025, 6, 1),
                new_description="New description",
                new_amount=Decimal("20.00"),
                changed_by="admin@example.com",
                note="Manual correction"
            )

            assert tx.description == "New description"
            assert tx.amount == Decimal("20.00")
            assert "update transactions" in logs["executed"][0]
            mock_log.assert_called_once()
            assert "manual correction" in mock_log.call_args[0][3].lower()


def test_transaction_delete_success():
    logs = {"deleted": False}

    class FakeCursor:
        rowcount = 1

        def execute(self, query, params=None):
            logs["query"] = query.strip().lower()

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.transaction.get_cursor", return_value=FakeCursor()):
        with patch("models.transaction.log_transaction_change") as mock_log:
            tx = Transaction(
                transaction_date=date(2025, 5, 1),
                description="To be deleted",
                amount=Decimal("5.00"),
                member_email="test@example.com",
                transaction_id=777
            )
            result = tx.delete(changed_by="admin@example.com")
            assert result is True
            assert "delete from transactions" in logs["query"]
            mock_log.assert_called_once()
            assert "deleted transaction" in mock_log.call_args[0][3].lower()


def test_transaction_delete_failure():
    class FakeCursor:
        rowcount = 0

        def execute(self, query, params=None): pass

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.transaction.get_cursor", return_value=FakeCursor()):
        with patch("models.transaction.log_transaction_change") as mock_log:
            tx = Transaction(
                transaction_date=date(2025, 5, 1),
                description="Missing",
                amount=Decimal("9.99"),
                member_email="test@example.com",
                transaction_id=999
            )
            result = tx.delete(changed_by="admin@example.com")
            assert result is False
            mock_log.assert_not_called()


def test_transaction_delete_without_id():
    tx = Transaction(
        transaction_date=date(2025, 5, 1),
        description="No ID",
        amount=Decimal("8.88"),
        member_email="test@example.com"
    )
    result = tx.delete(changed_by="admin@example.com")
    assert result is False
