from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime
from services.reimbursements_db import (
    save_reimbursement_items,
    update_bank_details,
)


def test_save_reimbursement_items_executes_insert():
    mock_cursor = MagicMock()

    test_email = "mock@example.com"
    test_rows = [{
        "description": "Test Fahrtkosten",
        "date": "12.05.2025",
        "amount": "12.34",
        "receipt_filename": "test_receipt.pdf"
    }]

    with patch("services.reimbursements_db.get_cursor",
               return_value=MagicMock(__enter__=lambda s: mock_cursor, __exit__=lambda *a: None)):
        save_reimbursement_items(test_email, test_rows)

    assert mock_cursor.execute.called
    args = mock_cursor.execute.call_args[0][1]

    assert args[0] == test_email
    assert isinstance(args[1], datetime)
    assert args[2] == "Test Fahrtkosten"
    assert args[3] == "12.05.2025"
    assert args[4] == Decimal("12.34")
    assert args[5] == "test_receipt.pdf"


def test_save_reimbursement_items_skips_incomplete():
    mock_cursor = MagicMock()
    test_email = "mock@example.com"
    test_rows = [
        {"description": "valid", "date": "12.05.2025", "amount": "10.00", "receipt_filename": "a.pdf"},
        {"description": "invalid", "date": "", "amount": "", "receipt_filename": ""},
    ]

    with patch("services.reimbursements_db.get_cursor",
               return_value=MagicMock(__enter__=lambda s: mock_cursor, __exit__=lambda *a: None)):
        save_reimbursement_items(test_email, test_rows)

    assert mock_cursor.execute.call_count == 1
    args = mock_cursor.execute.call_args[0][1]

    assert args[0] == test_email
    assert isinstance(args[1], datetime)
    assert args[2] == "valid"
    assert args[3] == "12.05.2025"
    assert args[4] == Decimal("10.00")
    assert args[5] == "a.pdf"


def test_update_bank_details_executes_upsert():
    mock_cursor = MagicMock()

    test_email = "mock@example.com"
    bank_name = "Test Bank"
    iban = "DE00123456780000000000"

    with patch("services.reimbursements_db.get_cursor",
               return_value=MagicMock(__enter__=lambda s: mock_cursor, __exit__=lambda *a: None)):
        update_bank_details(test_email, bank_name, iban)

    assert mock_cursor.execute.called
    args = mock_cursor.execute.call_args[0][1]

    assert args[0] == test_email
    assert args[1] == bank_name
    assert args[2] == iban
    assert isinstance(args[3], datetime)
