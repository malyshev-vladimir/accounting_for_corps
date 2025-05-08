import re

import pytest
from app import app
from decimal import Decimal
from unittest.mock import patch, MagicMock
from models.member import Member


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
    with patch("app.Transaction") as MockTransaction, \
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
    with patch("app.Transaction") as MockTransaction, \
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
    with patch("app.Transaction") as MockTransaction, \
            patch("app.get_admin_email", return_value="admin@example.com"):
        response = client.post("/admin/save_missing_payments", json={})
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["saved"] == 0


# ROUTE: POST /admin/save_missing_payments

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
            patch("app.send_report_email") as mock_send:
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
    with patch("app.load_transactions_by_email", return_value=[]) as mock_load:
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
