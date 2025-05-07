from datetime import date
from decimal import Decimal
from unittest.mock import patch
from services import monthly_payments
from models.transaction import Transaction
from models.transaction_type import TransactionType


def test_get_german_month_name():
    assert monthly_payments.get_german_month_name(date(2025, 1, 1)) == "Januar"
    assert monthly_payments.get_german_month_name(date(2025, 3, 1)) == "März"
    assert monthly_payments.get_german_month_name(date(2025, 12, 1)) == "Dezember"


def test_iterate_months_normal():
    start = date(2025, 1, 1)
    end = date(2025, 4, 1)
    result = list(monthly_payments.iterate_months(start, end))
    assert result == [
        date(2025, 1, 1),
        date(2025, 2, 1),
        date(2025, 3, 1),
        date(2025, 4, 1)
    ]


def test_iterate_months_single_month():
    result = list(monthly_payments.iterate_months(date(2025, 5, 1), date(2025, 5, 1)))
    assert result == [date(2025, 5, 1)]


def test_iterate_months_empty():
    result = list(monthly_payments.iterate_months(date(2025, 6, 1), date(2025, 5, 1)))
    assert result == []


def test_has_monthly_payment_for_month_true(monkeypatch):
    class FakeTx:
        date = date(2025, 5, 1)
        type = TransactionType.MONTHLY_FEE

    member = type("Member", (), {"email": "test@example.com"})
    monkeypatch.setattr("services.monthly_payments.load_transactions_by_email", lambda email: [FakeTx])
    assert monthly_payments.has_monthly_payment_for_month(member, date(2025, 5, 1)) is True


def test_has_monthly_payment_for_month_false(monkeypatch):
    class FakeTx:
        date = date(2025, 4, 1)
        type = TransactionType.MONTHLY_FEE

    member = type("Member", (), {"email": "test@example.com"})
    monkeypatch.setattr("services.monthly_payments.load_transactions_by_email", lambda email: [FakeTx])
    assert monthly_payments.has_monthly_payment_for_month(member, date(2025, 5, 1)) is False


def test_has_monthly_payment_wrong_type(monkeypatch):
    class FakeTx:
        date = date(2025, 5, 1)
        type = TransactionType.CUSTOM

    member = type("Member", (), {"email": "test@example.com"})
    monkeypatch.setattr("services.monthly_payments.load_transactions_by_email", lambda email: [FakeTx])
    assert monthly_payments.has_monthly_payment_for_month(member, date(2025, 5, 1)) is False


def test_get_missing_monthly_payment_transactions(monkeypatch):
    class FakeMember:
        email = "test@example.com"
        is_resident = True
        created_at = date(2025, 3, 15)

    monkeypatch.setattr("services.monthly_payments.load_member_by_email", lambda email: FakeMember())
    monkeypatch.setattr("services.monthly_payments.load_transactions_by_type", lambda e, t: [
        Transaction(
            transaction_date=date(2025, 4, 1),
            description="Already Paid",
            amount=Decimal("-15.00"),
            member_email=e,
            transaction_type=TransactionType.MONTHLY_FEE
        )
    ])
    monkeypatch.setattr("services.monthly_payments.get_monthly_payment_for_residents", lambda: 15)
    monkeypatch.setattr("services.monthly_payments.get_monthly_payment_for_non_residents", lambda: 0)

    with patch("services.monthly_payments.date") as mock_date:
        mock_date.today.return_value = date(2025, 5, 7)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        missing = monthly_payments.get_missing_monthly_payment_transactions("test@example.com")

        assert len(missing) == 2
        assert missing[0].date == date(2025, 3, 1)
        assert missing[1].date == date(2025, 5, 1)
        assert all(tx.amount == Decimal("-15.00") for tx in missing)
        assert all(tx.type == TransactionType.MONTHLY_FEE for tx in missing)


def test_missing_monthly_payments_for_non_resident(monkeypatch):
    class FakeMember:
        email = "test@example.com"
        is_resident = False
        created_at = date(2025, 3, 1)

    monkeypatch.setattr("services.monthly_payments.load_member_by_email", lambda email: FakeMember())
    monkeypatch.setattr("services.monthly_payments.load_transactions_by_type", lambda e, t: [])
    monkeypatch.setattr("services.monthly_payments.get_monthly_payment_for_residents", lambda: 0)
    monkeypatch.setattr("services.monthly_payments.get_monthly_payment_for_non_residents", lambda: 25)

    with patch("services.monthly_payments.date") as mock_date:
        mock_date.today.return_value = date(2025, 5, 10)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        txs = monthly_payments.get_missing_monthly_payment_transactions("test@example.com")

        assert len(txs) == 3
        assert all(tx.amount == Decimal("-25.00") for tx in txs)
        assert txs[0].date == date(2025, 3, 1)


def test_zero_amount_payment_skipped(monkeypatch):
    class FakeMember:
        email = "test@example.com"
        is_resident = True
        created_at = date(2025, 3, 1)

    monkeypatch.setattr("services.monthly_payments.load_member_by_email", lambda email: FakeMember())
    monkeypatch.setattr("services.monthly_payments.load_transactions_by_type", lambda e, t: [])
    monkeypatch.setattr("services.monthly_payments.get_monthly_payment_for_residents", lambda: 0)
    monkeypatch.setattr("services.monthly_payments.get_monthly_payment_for_non_residents", lambda: 0)

    with patch("services.monthly_payments.date") as mock_date:
        mock_date.today.return_value = date(2025, 5, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        txs = monthly_payments.get_missing_monthly_payment_transactions("test@example.com")
        assert txs == []
