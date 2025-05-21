import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
from services.report_sender import send_report_email
from datetime import date
from decimal import Decimal



def test_send_email_success():
    mock_template = """
    <html>
    <body>
        <p>{{title}} {{last_name}}</p>
        <table>{{transactions}}</table>
        <p>Saldo: {{balance}}</p>
        <p>{{phone_number}}</p>
    </body>
    </html>
    """

    class DummyTransaction:
        def __init__(self):
            self.date = date(2025, 1, 1)
            self.amount = Decimal("10.00")
            self.description = "Testeintrag"

    fake_member = MagicMock()
    fake_member.title = "CB"
    fake_member.last_name = "Test"
    fake_member.email = "test@example.com"
    fake_member.get_balance.return_value = Decimal("100.0")
    fake_member.get_transactions.return_value = [DummyTransaction()]
    fake_member.get_current_title.return_value = "CB"

    with patch("builtins.open", mock_open(read_data=mock_template)), \
         patch("os.path.exists", return_value=True), \
         patch("smtplib.SMTP_SSL") as mock_smtp, \
         patch.dict(os.environ, {"PHONE_NUMBER": "+49 123 456789"}):

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        def debug_send_message(msg):
            print("[DEBUG] Email content:")
            print(msg.get_content())

        mock_server.send_message.side_effect = debug_send_message

        send_report_email(fake_member)

        mock_server.login.assert_called()

        mock_server.sendmail.assert_called()


def test_template_file_not_found():
    fake_member = MagicMock()
    fake_member.email = "test@example.com"
    fake_member.get_balance.return_value = 0
    fake_member.get_transactions.return_value = []
    fake_member.get_current_title.return_value = "CB"
    fake_member.last_name = "Test"

    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError) as exc_info:
            send_report_email(fake_member)
        assert str(exc_info.value).startswith("Email template not found")


def test_smtp_login_error():
    mock_template = "<html>{{last_name}}</html>"

    fake_member = MagicMock()
    fake_member.title = "CB"
    fake_member.last_name = "Test"
    fake_member.email = "test@example.com"
    fake_member.get_balance.return_value = 100.0
    fake_member.get_transactions.return_value = []
    fake_member.get_current_title.return_value = "CB"

    with patch("builtins.open", mock_open(read_data=mock_template)), \
            patch("os.path.exists", return_value=True), \
            patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("Login failed")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with pytest.raises(Exception) as exc_info:
            send_report_email(fake_member)
        assert "Login failed" in str(exc_info.value)
