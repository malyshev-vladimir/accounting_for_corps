from datetime import datetime, timedelta
from unittest.mock import patch
from services.logging_db import log_title_change, log_residency_change, log_transaction_change


def test_log_transaction_change():
    executed = {}

    class FakeCursor:
        def execute(self, query, params=None):
            executed["call"] = (query.strip().lower(), params)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch("services.logging_db.get_cursor", return_value=FakeCursor()):
        log_transaction_change(
            transaction_id=42,
            action="update",
            changed_by="admin@example.com",
            description="Changed details"
        )
        assert "insert into transaction_change_log" in executed["call"][0]
        assert executed["call"][1][0] == 42
        assert executed["call"][1][1] == "update"


def test_log_title_change_inserts(monkeypatch):
    executed = []

    class FakeCursor:
        def execute(self, query, params=None):
            executed.append((query.strip().lower(), params))

        def fetchone(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("services.logging_db.get_cursor", lambda: FakeCursor())
    log_title_change("test@example.com", "CB", "admin@example.com")

    assert any("insert into title_changes" in q for q, _ in executed)


def test_log_title_change_skips_if_same(monkeypatch):
    class FakeCursor:
        def execute(self, query, params=None):
            pass

        def fetchone(self):
            return [1, "CB", datetime.now() - timedelta(hours=2)]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("services.logging_db.get_cursor", lambda: FakeCursor())
    log_title_change("test@example.com", "CB", "admin@example.com")


def test_log_residency_change_inserts(monkeypatch):
    executed = []

    class FakeCursor:
        def execute(self, query, params=None):
            executed.append((query.strip().lower(), params))

        def fetchone(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("services.logging_db.get_cursor", lambda: FakeCursor())
    log_residency_change("test@example.com", True, "admin@example.com")

    assert any("insert into residency_changes" in q for q, _ in executed)


def test_log_residency_change_skips_if_same(monkeypatch):
    class FakeCursor:
        def execute(self, query, params=None):
            pass

        def fetchone(self):
            return [5, True, datetime.now() - timedelta(days=1)]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("services.logging_db.get_cursor", lambda: FakeCursor())
    log_residency_change("test@example.com", True, "admin@example.com")
