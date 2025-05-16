from unittest.mock import patch
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_submit_success_with_transaction(client):
    form_data = {
        "report_date": "15.05.2025",
        "test@example.com_Pils (0,5L)": "1",
        "test@example.com_Helles (0,5L)": "1"
    }

    beverages = [
        {"name": "Pils (0,5L)", "price": 1.04},
        {"name": "Helles (0,5L)", "price": 1.04}
    ]

    with patch("app.load_beverage_assortment", return_value=beverages), \
            patch("app.save_beverage_report", return_value=42) as mock_save_report, \
            patch("models.transaction.Transaction.save") as mock_tx_save, \
            patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_all_members", return_value=[]):
        response = client.post("/submit-beverage-report", data=form_data, follow_redirects=True)

    assert response.status_code == 200
    assert mock_save_report.called
    assert mock_tx_save.call_count == 1


def test_submit_missing_report_date(client):
    with patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_all_members", return_value=[]):
        response = client.post("/submit-beverage-report", data={}, follow_redirects=True)
    assert response.status_code == 200


def test_submit_no_transactions_created(client):
    data = {"report_date": "15.05.2025", "test@example.com_Bier": "0"}
    beverages = [{"name": "Bier", "price": 1.5}]

    with patch("app.load_beverage_assortment", return_value=beverages), \
            patch("app.save_beverage_report", return_value=1), \
            patch("models.transaction.Transaction.save") as mock_save, \
            patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_all_members", return_value=[]):
        response = client.post("/submit-beverage-report", data=data, follow_redirects=True)

    assert mock_save.call_count == 0
    assert response.status_code == 200


def test_submit_invalid_number_format(client):
    data = {
        "report_date": "15.05.2025",
        "test@example.com_Bier": "abc"
    }
    beverages = [{"name": "Bier", "price": 1.5}]

    with patch("app.load_beverage_assortment", return_value=beverages), \
            patch("app.save_beverage_report", return_value=1), \
            patch("models.transaction.Transaction.save") as mock_save, \
            patch("app.get_admin_email", return_value="admin@example.com"), \
            patch("app.load_all_members", return_value=[]):
        response = client.post("/submit-beverage-report", data=data, follow_redirects=True)

    assert mock_save.call_count == 0
    assert response.status_code == 200


def test_submit_beverage_report_ignores_submission_if_event_name_empty(client):
    with patch("app.save_beverage_report") as mock_save:
        response = client.post("/submit-beverage-report", data={
            "event_name": "",
            "email": "user@example.com",
            "drink_quantity_Cola": "3",
            "drink_quantity_Bier": "2"
        })

        mock_save.assert_not_called()
        assert response.status_code in (200, 302)
