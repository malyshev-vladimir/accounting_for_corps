from decimal import Decimal
from datetime import date
from unittest.mock import patch
import models.member
from models.member import Title


def test_create_member():
    m = models.member.Member("mail@example.com", "Last", "First", start_balance=10.0)
    assert m.email == "mail@example.com"
    assert m.last_name == "Last"
    assert m.first_name == "First"
    assert m.title == "F"
    assert m.is_resident is True
    assert m.start_balance == Decimal("10.00")


def test_get_balance_at_excludes_future(monkeypatch, sample_member):
    today = date.today()
    monkeypatch.setattr(sample_member, "get_transactions", lambda: [
        type("Tx", (), {"amount": Decimal("10.0"), "date": today}),
        type("Tx", (), {"amount": Decimal("999.0"), "date": today.replace(year=today.year + 1)}),
    ])
    assert sample_member.get_balance_at(today) == Decimal("10.00")


def test_get_balance_with_transactions(monkeypatch, sample_member):
    monkeypatch.setattr(sample_member, "get_transactions", lambda: [
        type("Tx", (), {"amount": Decimal("-10.0"), "date": date.today()}),
        type("Tx", (), {"amount": Decimal("5.0"), "date": date.today()}),
    ])
    assert sample_member.get_balance() == Decimal("-5.00")


def test_get_title_enum(sample_member):
    sample_member.title = Title.iaCB
    assert sample_member.get_title() == "iaCB"


def test_change_title_to(sample_member):
    logs = []

    class FakeCursor:
        def execute(self, query, params=None):
            logs.append(query.lower().strip())

        def fetchone(self):
            return True

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.member.get_cursor", return_value=FakeCursor()):
        sample_member.change_title("CB", changed_by="admin@example.com")

    assert sample_member.title == Title.CB.value


def test_change_title_no_change(sample_member):
    sample_member.title = "CB"

    with patch("models.member.get_cursor") as mock_cursor:
        sample_member.change_title("CB", changed_by="admin@example.com")

    mock_cursor.assert_not_called()


def test_change_residency(sample_member):
    logs = []

    class FakeCursor:
        def execute(self, query, params=None):
            logs.append(query.lower().strip())

        def fetchone(self):
            return True

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.member.get_cursor", return_value=FakeCursor()):
        sample_member.change_residency(False, changed_by="admin@example.com")

    assert sample_member.is_resident is False
    assert any("update members" in q for q in logs)
    assert any("insert into residency_changes" in q for q in logs)


def test_change_residency_no_change(sample_member):
    sample_member.is_resident = True

    with patch("models.member.get_cursor") as mock_cursor:
        sample_member.change_residency(True, changed_by="admin@example.com")

    mock_cursor.assert_not_called()


def test_create_transaction(sample_member):
    saved = {}

    class FakeTransaction:
        def __init__(self, transaction_date, description, amount, member_email):
            saved["args"] = (transaction_date, description, amount, member_email)

        def save(self, changed_by):
            saved["changed_by"] = changed_by

    with patch("models.member.Transaction", FakeTransaction):
        sample_member.create_transaction(
            transaction_date=date(2025, 5, 1),
            description="Test Entry",
            amount=Decimal("-15.0"),
            changed_by="admin@example.com"
        )

    assert saved["args"][1] == "Test Entry"
    assert saved["changed_by"] == "admin@example.com"


def test_save_to_db_insert(sample_member):
    logs = []

    class FakeCursor:
        def execute(self, query, params=None):
            logs.append(query.lower().strip())

        def fetchone(self):
            return None

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.member.get_cursor", return_value=FakeCursor()):
        sample_member.save_to_db()

    assert any("insert into members" in q for q in logs)
    assert any("insert into title_changes" in q for q in logs)
    assert any("insert into residency_changes" in q for q in logs)


def test_save_to_db_update_existing(sample_member):
    logs = []

    class FakeCursor:
        def __init__(self):
            self.calls = 0

        def execute(self, query, params=None):
            logs.append(query.lower().strip())

        def fetchone(self):
            self.calls += 1
            return True

        def __enter__(self): return self

        def __exit__(self, exc_type, exc_val, exc_tb): pass

    with patch("models.member.get_cursor", return_value=FakeCursor()):
        sample_member.save_to_db()

    assert any("insert into members" in q for q in logs)
    assert not any("insert into title_changes" in q for q in logs)
    assert not any("insert into residency_changes" in q for q in logs)


def test_get_last_credit_date(monkeypatch, sample_member):
    today = date.today()
    monkeypatch.setattr(sample_member, "get_transactions", lambda: [
        type("Tx", (), {"type": 3, "date": today.replace(year=2023)}),
        type("Tx", (), {"type": 3, "date": today.replace(year=2024)}),
        type("Tx", (), {"type": 1, "date": today.replace(year=2025)}),
    ])
    assert sample_member.get_last_credit_date() == today.replace(year=2024)


def test_get_last_credit_date_none(monkeypatch, sample_member):
    monkeypatch.setattr(sample_member, "get_transactions", lambda: [
        type("Tx", (), {"type": 2, "date": date(2023, 1, 1)}),
        type("Tx", (), {"type": 4, "date": date(2024, 1, 1)}),
    ])
    assert sample_member.get_last_credit_date() is None
