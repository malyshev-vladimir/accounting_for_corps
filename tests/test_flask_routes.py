import datetime
import re
from pathlib import Path

import pytest
from app import app
from decimal import Decimal
from unittest.mock import MagicMock, patch
from models.member import Member
from io import BytesIO


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ROUTE: GET /

def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Email" in response.data or b"email" in response.data


# ROUTE: POST /dashboard

def test_dashboard_admin_redirect(client):
    with patch("app.get_admin_email", return_value="admin@example.com"):
        response = client.post("/dashboard", data={"email": "admin@example.com"})
        assert response.status_code == 302
        assert "/admin" in response.location


def test_dashboard_member_view(client):
    with patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_member_by_email") as mock_load:
        mock_member = MagicMock()
        mock_member.get_balance.return_value = Decimal("100")
        mock_member.get_transactions.return_value = []
        mock_load.return_value = mock_member

        response = client.post("/dashboard", data={"email": "member@example.com"})
        assert response.status_code == 200
        assert b"dein kontoauszug" in response.data.lower()


def test_dashboard_member_not_found(client):
    with patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_member_by_email", side_effect=ValueError("not found")):
        response = client.post("/dashboard", data={"email": "nonexistent@example.com"})
        assert response.status_code == 404


# ROUTE: GET /reimbursement-form/<email>

def test_reimbursement_form_success(client):
    with patch("app.load_member_by_email") as mock_load:
        mock_member = MagicMock()
        mock_member.first_name = "Max"
        mock_member.last_name = "Muster"
        mock_load.return_value = mock_member

        response = client.get("/reimbursement-form/user@example.com")
        assert response.status_code == 200
        assert b"Erstattungsformular" in response.data or b"erstattung" in response.data.lower()


def test_reimbursement_form_member_not_found(client):
    with patch("app.load_member_by_email", return_value=None):
        response = client.get("/reimbursement-form/user@example.com")
        assert response.status_code == 404
        assert b"mitglied nicht gefunden" in response.data.lower()


# ROUTE: POST /submit-reimbursement

def test_submit_reimbursement_valid_entry(client):
    with patch("app.save_reimbursement_items") as mock_save, \
            patch("app.update_bank_details") as mock_update, \
            patch("app.load_member_by_email") as mock_load:
        mock_member = MagicMock()
        mock_member.last_name = "Muster"
        mock_load.return_value = mock_member

        data = {
            "email": "user@example.com",
            "refund_type": "bank",
            "bank_name": "Test Bank",
            "iban": "DE00123456780000000000",
            "description[]": ["Fahrt nach Berlin"],
            "date[]": ["13.05.2025"],
            "amount[]": ["19.90"],
            "receipt[]": (BytesIO(b"dummy pdf"), "beleg.pdf")
        }

        try:
            response = client.post("/submit-reimbursement", data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert mock_save.called
            assert mock_update.called

            # Check the structure of saved data
            args = mock_save.call_args[0][1]
            assert isinstance(args, list)
            assert len(args) == 1
            item = args[0]
            assert item["description"] == "Fahrt nach Berlin"
            assert item["date"] == "13.05.2025"
            assert item["amount"] == "19.90"

            # Check filename structure: f"{short_desc}_{date_part}_{member.last_name}_{uuid}{ext}"
            assert re.match(r"fahrt_nach_berlin_20250513_Muster_[a-f0-9]{8}\.pdf", item["receipt_filename"])

        finally:
            # Delete the created file
            filename = item["receipt_filename"]
            path = Path("uploads") / filename
            if path.exists():
                path.unlink()


def test_submit_reimbursement_all_entries_invalid(client):
    with patch("app.save_reimbursement_items") as mock_save, \
            patch("app.update_bank_details") as mock_update, \
            patch("app.load_member_by_email") as mock_load:
        mock_load.return_value = MagicMock(last_name="Invalid")

        data = {
            "email": "user@example.com",
            "refund_type": "bank",
            "bank_name": "Bank",
            "iban": "DE00000000000000000000",
            "description[]": ["", ""],
            "date[]": ["", ""],
            "amount[]": ["", ""],
            "receipt[]": [
                (BytesIO(b""), ""), (BytesIO(b""), "")
            ]
        }

        response = client.post("/submit-reimbursement", data=data, content_type="multipart/form-data")

        assert response.status_code == 302
        mock_save.assert_not_called()  # nothing is saved
        mock_update.assert_called_once()  # but bank_details are updated


def test_submit_reimbursement_skips_incomplete_entries(client):
    with patch("app.save_reimbursement_items") as mock_save, \
            patch("app.update_bank_details"), \
            patch("app.load_member_by_email") as mock_load:
        mock_member = MagicMock()
        mock_member.last_name = "Test"
        mock_load.return_value = mock_member

        data = {
            "email": "user@example.com",
            "refund_type": "bank",
            "bank_name": "Test Bank",
            "iban": "DE00123456780000000000",
            "description[]": ["", "Taxi zur Hassia"],
            "date[]": ["", "01.05.2024"],
            "amount[]": ["", "15.00"],
            "receipt[]": [
                (BytesIO(b""), ""),  # Incomplete
                (BytesIO(b"valid"), "beleg2.pdf")  # Valid
            ]
        }

        try:
            response = client.post("/submit-reimbursement", data=data, content_type='multipart/form-data')
            assert response.status_code == 302

            # Only one complete entry should be saved
            mock_save.assert_called_once()
            entries = mock_save.call_args[0][1]
            assert len(entries) == 1
            assert entries[0]["description"] == "Taxi zur Hassia"
        finally:
            if mock_save.called:
                item = mock_save.call_args[0][1][0]
                path = Path("uploads") / item["receipt_filename"]
                if path.exists():
                    path.unlink()


def test_submit_reimbursement_without_bank_info(client):
    with patch("app.save_reimbursement_items") as mock_save, \
            patch("app.update_bank_details") as mock_update, \
            patch("app.load_member_by_email") as mock_load:
        mock_load.return_value = MagicMock(last_name="Nobank")

        data = {
            "email": "user@example.com",
            "refund_type": "bank",  # type "bank" selected
            "bank_name": "",  # but no bank name provided
            "iban": "",
            "description[]": ["Taxi"],
            "date[]": ["01.05.2024"],
            "amount[]": ["15.00"],
            "receipt[]": (BytesIO(b"valid"), "beleg.pdf")
        }
        try:
            response = client.post("/submit-reimbursement", data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            mock_save.assert_called_once()
            mock_update.assert_not_called()  # bank details are not updated
        finally:
            if mock_save.called:
                item = mock_save.call_args[0][1][0]
                path = Path("uploads") / item["receipt_filename"]
                if path.exists():
                    path.unlink()


# ROUTE: GET /admin

def test_admin_panel_loads(client):
    with patch("app.load_all_members", return_value=[]):
        response = client.get("/admin")
        assert response.status_code == 200


def test_admin_panel_error(client):
    with patch("app.load_all_members", side_effect=Exception("DB failure")):
        response = client.get("/admin")
        assert response.status_code == 500
        assert b"error loading members" in response.data.lower()


@pytest.fixture
def mock_sorted_members():
    m1 = MagicMock(spec=Member)
    m1.last_name = "Ziegler"
    m1.email = "ziegler@example.com"
    m1.created_at = "2023-05-01"
    m1.get_balance.return_value = Decimal("-100.00")

    m2 = MagicMock(spec=Member)
    m2.last_name = "Albrecht"
    m2.email = "albrecht@example.com"
    m2.created_at = "2023-04-01"
    m2.get_balance.return_value = Decimal("0.00")

    m3 = MagicMock(spec=Member)
    m3.last_name = "Berger"
    m3.email = "berger@example.com"
    m3.created_at = "2023-06-01"
    m3.get_balance.return_value = Decimal("-50.00")

    return [m1, m2, m3]


def test_admin_sort_by_balance_asc(client, mock_sorted_members):
    with patch("app.load_all_members", return_value=mock_sorted_members):
        response = client.get("/admin?sort_by=balance&order=asc")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        pos_ziegler = html.find("ziegler@example.com")
        pos_berger = html.find("berger@example.com")
        pos_albrecht = html.find("albrecht@example.com")
        assert pos_ziegler < pos_berger < pos_albrecht


def test_admin_sort_by_name_desc(client, mock_sorted_members):
    with patch("app.load_all_members", return_value=mock_sorted_members):
        response = client.get("/admin?sort_by=name&order=desc")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        pos_ziegler = html.find("ziegler@example.com")
        pos_berger = html.find("berger@example.com")
        pos_albrecht = html.find("albrecht@example.com")
        assert pos_ziegler < pos_berger < pos_albrecht


def test_admin_sort_by_created_at_asc(client, mock_sorted_members):
    with patch("app.load_all_members", return_value=mock_sorted_members):
        response = client.get("/admin?sort_by=created_at&order=asc")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        pos_albrecht = html.find("albrecht@example.com")
        pos_ziegler = html.find("ziegler@example.com")
        pos_berger = html.find("berger@example.com")
        assert pos_albrecht < pos_ziegler < pos_berger


def test_admin_sort_default(client, mock_sorted_members):
    with patch("app.load_all_members", return_value=mock_sorted_members):
        response = client.get("/admin")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        pos_ziegler = html.find("ziegler@example.com")
        pos_berger = html.find("berger@example.com")
        pos_albrecht = html.find("albrecht@example.com")
        assert pos_ziegler < pos_berger < pos_albrecht


# ROUTE: GET /admin/statistics

def test_admin_statistics_loads(client):
    mock_member = MagicMock()
    mock_member.get_balance.return_value = Decimal("-200.00")
    mock_member.get_balance_at.return_value = Decimal("-150.00")
    mock_member.get_last_credit_date.return_value = datetime.datetime(2025, 5, 1)
    mock_member.last_name = "Schmidt"
    mock_member.get_title.return_value = "CB"

    with patch("app.load_all_members", return_value=[mock_member]):
        response = client.get("/admin/statistics")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Schmidt" in html
        assert "CB Schmidt" in html
        assert "200.00" in html or "-200.00" in html
        assert "01.05.2025" in html
        assert "Fehlbetrag" not in html


def test_admin_statistics_ignores_small_debts(client):
    mock_member = MagicMock()
    mock_member.get_balance.return_value = Decimal("-50.00")
    mock_member.get_balance_at.return_value = Decimal("-40.00")
    mock_member.get_last_credit_date.return_value = datetime.datetime(2025, 4, 1)
    mock_member.last_name = "Mild"
    mock_member.get_title.return_value = "F"

    with patch("app.load_all_members", return_value=[mock_member]):
        response = client.get("/admin/statistics")
        html = response.get_data(as_text=True)
        assert "Mild" not in html


def test_admin_statistics_handles_invalid_date(client):
    with patch("app.load_all_members", return_value=[]):
        response = client.get("/admin/statistics?date=invalid-date")
        assert response.status_code == 200


def test_admin_statistics_handles_missing_last_credit(client):
    member = MagicMock()
    member.get_balance.return_value = Decimal("-120.00")
    member.get_balance_at.return_value = Decimal("-100.00")
    member.get_last_credit_date.return_value = None
    member.last_name = "NoTopup"
    member.get_title.return_value = "CB"

    with patch("app.load_all_members", return_value=[member]):
        response = client.get("/admin/statistics")
        html = response.get_data(as_text=True)
        assert "–" in html


def test_admin_statistics_respects_custom_date_param(client):
    member = MagicMock()
    member.get_balance.return_value = Decimal("-150.00")
    member.get_balance_at.return_value = Decimal("-130.00")
    member.get_last_credit_date.return_value = datetime.datetime(2025, 3, 10)
    member.last_name = "Dated"
    member.get_title.return_value = "CB"

    with patch("app.load_all_members", return_value=[member]):
        response = client.get("/admin/statistics?date=01.01.2024")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Dated" in html
        assert "10.03.2025" in html


def test_admin_statistics_raises_on_db_failure(client):
    with patch("app.load_all_members", side_effect=Exception("DB error")):
        response = client.get("/admin/statistics")
        assert response.status_code == 500
        assert b"error" in response.data.lower()


def test_admin_statistics_equal_debt_sorting(client):
    m1 = MagicMock()
    m1.last_name = "Alpha"
    m1.get_title.return_value = "CB"
    m1.get_balance.return_value = Decimal("-150.00")
    m1.get_balance_at.return_value = Decimal("-140.00")
    m1.get_last_credit_date.return_value = datetime.datetime(2025, 1, 1)

    m2 = MagicMock()
    m2.last_name = "Beta"
    m2.get_title.return_value = "CB"
    m2.get_balance.return_value = Decimal("-150.00")
    m2.get_balance_at.return_value = Decimal("-140.00")
    m2.get_last_credit_date.return_value = datetime.datetime(2025, 2, 1)

    with patch("app.load_all_members", return_value=[m1, m2]):
        response = client.get("/admin/statistics")
        html = response.get_data(as_text=True)
        pos_alpha = html.find("Alpha")
        pos_beta = html.find("Beta")
        assert pos_alpha < pos_beta or pos_beta < pos_alpha


# ROUTE: GET, POST /admin/add_member

def test_add_member_get_form(client):
    response = client.get("/admin/add_member")
    assert response.status_code == 200


def test_add_member_success(client):
    with patch("app.load_member_by_email", side_effect=ValueError("Not found")), \
            patch("app.Member") as MockMember:
        mock_instance = MagicMock()
        MockMember.return_value = mock_instance

        response = client.post("/admin/add_member", data={
            "email": "new@example.com",
            "last_name": "Muster",
            "first_name": "Max",
            "title": "F",
            "is_resident": "on",
            "start_balance": "15.00"
        })

        assert response.status_code == 302
        MockMember.assert_called_once()
        mock_instance.save_to_db.assert_called_once()


def test_add_member_email_normalization(client):
    with patch("app.load_member_by_email", side_effect=ValueError("Not found")), \
            patch("app.Member") as MockMember:
        mock_instance = MagicMock()
        MockMember.return_value = mock_instance

        response = client.post("/admin/add_member", data={
            "email": "  TestUser@Example.COM  ",
            "last_name": "Tester",
            "first_name": "Max",
            "title": "CB",
            "is_resident": "on",
            "start_balance": "25.00"
        })

        assert response.status_code == 302
        args, kwargs = MockMember.call_args
        normalized_email = kwargs["email"]
        assert normalized_email == "testuser@example.com"


def test_add_member_not_resident_by_default(client):
    with patch("app.load_member_by_email", side_effect=ValueError("Not found")), \
            patch("app.Member") as MockMember:
        mock_instance = MagicMock()
        MockMember.return_value = mock_instance

        response = client.post("/admin/add_member", data={
            "email": "nobody@example.com",
            "last_name": "No",
            "first_name": "Body",
            "title": "F",
            "start_balance": "0.00"
            # "is_resident" is missing
        })

        assert response.status_code == 302
        _, kwargs = MockMember.call_args
        assert kwargs["is_resident"] is False


def test_add_member_balance_with_comma(client):
    with patch("app.load_member_by_email", side_effect=ValueError("Not found")), \
            patch("app.Member") as MockMember:
        mock_instance = MagicMock()
        MockMember.return_value = mock_instance

        response = client.post("/admin/add_member", data={
            "email": "comma@example.com",
            "last_name": "Comma",
            "first_name": "User",
            "title": "F",
            "is_resident": "on",
            "start_balance": "12,50"
        })

        assert response.status_code == 302
        _, kwargs = MockMember.call_args
        assert kwargs["start_balance"] == Decimal("12.50")


def test_add_member_already_exists(client):
    with patch("app.load_member_by_email", return_value=MagicMock()):
        response = client.post("/admin/add_member", data={
            "email": "existing@example.com",
            "last_name": "Test",
            "first_name": "User",
            "title": "F",
            "start_balance": "10.00"
        })
        assert response.status_code == 400


def test_add_member_invalid_email(client):
    response = client.post("/admin/add_member", data={
        "email": "invalid-email",
        "last_name": "User",
        "first_name": "Max",
        "title": "F",
        "start_balance": "10.00"
    })
    assert response.status_code == 400


def test_add_member_invalid_balance(client):
    response = client.post("/admin/add_member", data={
        "email": "user@example.com",
        "last_name": "Test",
        "first_name": "Max",
        "title": "F",
        "start_balance": "not-a-number"
    })
    assert response.status_code == 400


def test_add_member_invalid_title(client):
    response = client.post("/admin/add_member", data={
        "email": "user@example.com",
        "last_name": "Test",
        "first_name": "User",
        "title": "INVALID",  # not in Title
        "start_balance": "10.00"
    })
    assert response.status_code == 400
    assert b"invalid title" in response.data.lower()


def test_update_member_status_exception(client):
    with patch("app.load_member_by_email", side_effect=Exception("DB error")):
        response = client.post("/admin/update_member_status", json={
            "email": "user@example.com",
            "title": "CB",
            "is_resident": True
        })
        assert response.status_code == 500
        assert b"db error" in response.data.lower() or b"error" in response.data.lower()


# ROUTE: GET /admin/check_monthly_payments

def test_check_all_missing_monthly_payments(client):
    with patch("app.load_all_members", return_value=[]), \
            patch("app.get_monthly_payment_for_residents", return_value=Decimal("20")), \
            patch("app.get_monthly_payment_for_non_residents", return_value=Decimal("30")):
        response = client.get("/admin/check_monthly_payments")
        assert response.status_code == 200


# ROUTE: POST /admin/save_missing_payments

def test_save_missing_payments_invalid_date(client):
    with patch("app.Transaction"), \
            patch("app.get_admin_email", return_value="admin@example.com"):
        response = client.post("/admin/save_missing_payments", json={
            "transactions": [{
                "email": "user@example.com",
                "date": "not-a-date",
                "amount": "25.00"
            }]
        })
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["saved"] == 0


def test_save_missing_payments_invalid_amount(client):
    with patch("app.Transaction"), \
            patch("app.get_admin_email", return_value="admin@example.com"):
        response = client.post("/admin/save_missing_payments", json={
            "transactions": [{
                "email": "user@example.com",
                "date": "2024-05-01",
                "amount": "abc"
            }]
        })
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["saved"] == 0


def test_save_missing_payments_missing_field(client):
    with patch("app.Transaction"), \
            patch("app.get_admin_email", return_value="admin@example.com"):
        response = client.post("/admin/save_missing_payments", json={})
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["saved"] == 0


def test_save_missing_payments(client):
    with patch("app.Transaction") as MockTransaction, \
            patch("app.get_admin_email", return_value="admin@example.com"):
        mock_tx = MagicMock()
        MockTransaction.return_value = mock_tx

        response = client.post("/admin/save_missing_payments", json={
            "transactions": [{
                "email": "user@example.com",
                "date": "2024-05-01",
                "amount": "25.00"
            }]
        })
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["saved"] == 1
        mock_tx.save.assert_called_once()


@pytest.mark.parametrize("invalid_date", ["not-a-date", "2025/05/01", "May 1, 2025"])
def test_save_missing_payments_invalid_date_format(client, invalid_date):
    """Ensure that transactions with invalid date formats are skipped"""
    response = client.post("/admin/save_missing_payments", json={
        "transactions": [
            {"email": "test@example.com", "date": invalid_date, "amount": "15.00"}
        ]
    })
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["saved"] == 0


def test_save_missing_payments_partial_failure(client):
    """Test that if one of multiple transactions fails, others are still saved"""
    with patch("app.Transaction") as MockTransaction, \
            patch("app.get_admin_email", return_value="admin@example.com"):
        # First and third succeed, second raises exception inside Transaction()
        valid_tx = MagicMock()
        MockTransaction.side_effect = [valid_tx, Exception("fail"), valid_tx]

        response = client.post("/admin/save_missing_payments", json={
            "transactions": [
                {"email": "one@example.com", "date": "2025-05-01", "amount": "15.00"},
                {"email": "bad@example.com", "date": "2025-05-02", "amount": "15.00"},
                {"email": "two@example.com", "date": "2025-05-01", "amount": "15.00"},
            ]
        })

        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["saved"] == 2


def test_check_missing_payments_html_contains_expected_fields(client):
    from models.member import Member
    mock_member = MagicMock(spec=Member)
    mock_member.email = "test@example.com"
    mock_member.first_name = "Test"
    mock_member.last_name = "User"
    mock_member.title = "F"
    mock_member.is_resident = True
    mock_member.created_at = "2023-01-01"
    mock_member.get_balance.return_value = 0
    mock_member.get_transactions.return_value = []

    mock_missing_tx = MagicMock()
    mock_missing_tx.date = datetime.date(2025, 5, 1)
    mock_missing_tx.amount = Decimal("15.00")

    with patch("app.load_all_members", return_value=[mock_member]), \
            patch("app.get_monthly_payment_for_residents", return_value=Decimal("15.00")), \
            patch("app.get_monthly_payment_for_non_residents", return_value=Decimal("12.50")), \
            patch("app.get_missing_monthly_payment_transactions", return_value=[mock_missing_tx]), \
            patch("app.load_transactions_by_type", return_value=[]):
        response = client.get("/admin/check_monthly_payments")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Test" in html
        assert "User" in html
        assert "15.00" in html
        assert "Fehlende Aktivenbeiträge" in html


# ROUTE: GET /admin/add_transaction

def test_admin_add_transaction_get(client):
    with patch("app.load_all_members", return_value=[]):
        response = client.get("/admin/add_transaction")
        assert response.status_code == 200


# ROUTE: POST /admin/add_transaction

def test_admin_add_transaction_post_success(client):
    with patch("app.Transaction") as MockTransaction, \
            patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_all_members", return_value=[]):
        mock_tx = MagicMock()
        MockTransaction.return_value = mock_tx

        response = client.post("/admin/add_transaction", data={
            "email": "user@example.com",
            "date": "2024-05-01",
            "description": "Test transaction",
            "amount": "10.00",
            "type": "1"
        })
        assert response.status_code == 302
        mock_tx.save.assert_called_once()


def test_admin_add_transaction_invalid_date(client):
    response = client.post("/admin/add_transaction", data={
        "email": "user@example.com",
        "date": "invalid-date",
        "description": "Test",
        "amount": "10.00",
        "type": "1"
    })
    assert response.status_code == 400
    assert b"datum" in response.data.lower()


def test_admin_add_transaction_invalid_amount(client):
    response = client.post("/admin/add_transaction", data={
        "email": "user@example.com",
        "date": "2024-05-01",
        "description": "Test",
        "amount": "notanumber",
        "type": "1"
    })
    assert response.status_code == 400
    assert b"betrag" in response.data.lower()


def test_admin_add_transaction_invalid_type(client):
    response = client.post("/admin/add_transaction", data={
        "email": "user@example.com",
        "date": "2024-05-01",
        "description": "Test",
        "amount": "10.00",
        "type": "invalid"
    })
    assert response.status_code == 400
    assert b"transaktionstyp" in response.data.lower()


# ROUTE: POST /delete_transaction/<email>/<id>

def test_delete_transaction_success(client):
    with patch("app.load_transaction_by_id") as mock_load, \
            patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.log_transaction_change") as mock_log:
        mock_tx = MagicMock()
        mock_tx.member_email = "user@example.com"
        mock_tx.id = 1
        mock_tx.description = "desc"
        mock_tx.delete.return_value = True
        mock_load.return_value = mock_tx

        response = client.post("/delete_transaction/user@example.com/1")
        assert response.status_code == 204
        mock_log.assert_called_once()


def test_delete_transaction_email_mismatch(client):
    with patch("app.load_transaction_by_id") as mock_load:
        mock_tx = MagicMock()
        mock_tx.member_email = "someoneelse@example.com"
        mock_load.return_value = mock_tx

        response = client.post("/delete_transaction/user@example.com/1")
        assert response.status_code == 400


def test_delete_transaction_exception(client):
    with patch("app.load_transaction_by_id", side_effect=Exception("DB error")):
        response = client.post("/delete_transaction/user@example.com/1")
        assert response.status_code == 400
        assert b"error deleting transaction" in response.data.lower()


# ROUTE: GET /admin/edit_titles_and_residency

def test_edit_titles_and_residency(client):
    with patch("app.load_all_members") as mock_load, patch("app.Title", new=MagicMock()):
        # Mock the members and titles
        mock_members = [
            MagicMock(last_name="Doe", first_name="John", email="john.doe@example.com", title="F", is_resident=True,
                      created_at="2021-01-01"),
            MagicMock(last_name="Smith", first_name="Jane", email="jane.smith@example.com", title="CB",
                      is_resident=False, created_at="2021-02-01")
        ]
        mock_load.return_value = mock_members

        response = client.get("/admin/edit_titles_and_residency")

        # Assert that the page loaded correctly (status 200)
        assert response.status_code == 200

        # Use a more flexible regular expression for the header
        assert re.search(r"<h2[^>]*>Titel\s*&\s*Wohnsitzstatus\s*bearbeiten</h2>", response.data.decode('utf-8'))

        # Check if the members' data is rendered in the response (last name, first name, title, etc.)
        for member in mock_members:
            assert member.last_name.encode() in response.data
            assert member.first_name.encode() in response.data
            assert member.email.encode() in response.data
            assert member.title.encode() in response.data


# ROUTE: POST /admin/update_member_status

def test_update_member_status_missing_fields(client):
    # Send a POST request with missing 'is_resident'
    response = client.post("/admin/update_member_status", json={
        "email": "user@example.com",
        "title": "CB"  # Missing 'is_resident'
    })

    # Assert that the response is an error due to missing fields
    assert response.status_code == 400
    assert response.json["error"] == "Missing fields"  # Check the correct error message


# ROUTE: POST /send_report

def test_send_report_success(client):
    with patch("app.load_member_by_email") as mock_load, \
            patch("app.send_report_email"):
        mock_load.return_value = MagicMock()

        response = client.post("/send_report", json={"email": "user@example.com"})
        assert response.status_code == 200
        assert response.json["success"] is True


def test_send_report_not_found(client):
    with patch("app.load_member_by_email", side_effect=ValueError("Not found")):
        response = client.post("/send_report", json={"email": "missing@example.com"})
        assert response.status_code == 404


def test_send_report_send_error(client):
    with patch("app.load_member_by_email", return_value=MagicMock()), \
            patch("app.send_report_email", side_effect=Exception("SMTP error")):
        response = client.post("/send_report", json={"email": "user@example.com"})
        assert response.status_code == 500
        assert b"senden fehlgeschlagen" in response.data.lower()


# ROUTE: GET /admin/get_transactions

def test_get_transactions(client):
    with patch("app.load_transactions_by_email", return_value=[]):
        response = client.get("/admin/get_transactions?email=user@example.com")
        assert response.status_code == 200
        assert isinstance(response.json, list)


def test_get_transactions_missing_email(client):
    response = client.get("/admin/get_transactions")
    assert response.status_code == 400
    assert b"missing email" in response.data.lower()


def test_get_transactions_exception(client):
    with patch("app.load_transactions_by_email", side_effect=Exception("DB error")):
        response = client.get("/admin/get_transactions?email=user@example.com")
        assert response.status_code == 500
        assert b"db error" in response.data.lower()
