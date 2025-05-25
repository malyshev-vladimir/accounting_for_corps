import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import date
from decimal import Decimal
from services.report_sender import send_report_email, format_member_email


class DummyTransaction:
    def __init__(self):
        self.date = date(2025, 1, 1)
        self.amount = Decimal("10.00")
        self.description = "Testeintrag"


@pytest.fixture
def fake_member():
    member = MagicMock()
    member.title = "CB"
    member.last_name = "Test"
    member.email = "test@example.com"
    member.get_balance.return_value = Decimal("100.00")
    member.get_transactions.return_value = [DummyTransaction()]
    return member


def test_format_member_email_success(fake_member):
    mock_template = """
    <html>
        <body>
            <p>{{title}} {{last_name}}</p>
            <table>{{transactions}}</table>
            <p>Saldo: {{balance}}</p>
            <p>{{phone_number}}</p>
            <p>{{generated_at}}</p>
        </body>
    </html>
    """

    with patch("builtins.open", mock_open(read_data=mock_template)), \
         patch("os.path.exists", return_value=True):

        html = format_member_email(fake_member, "+49 123 456789", "dummy_template.html")
        assert "Test" in html
        assert "10,00 €" in html
        assert "<table>" in html


def test_send_email_dry_run(fake_member):
    mock_template = "<html>{{title}} {{last_name}}</html>"

    with patch("builtins.open", mock_open(read_data=mock_template)), \
         patch("os.path.exists", return_value=True):

        result = send_report_email(
            fake_member,
            "sender@example.com",
            "password",
            "+49 123 456789",
            "dummy_template.html",
            dry_run=True
        )
        assert result is False


def test_send_email_success(fake_member):
    mock_template = "<html>{{title}} {{last_name}}</html>"

    with patch("builtins.open", mock_open(read_data=mock_template)), \
         patch("os.path.exists", return_value=True), \
         patch("smtplib.SMTP_SSL") as mock_smtp:

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_report_email(
            fake_member,
            "sender@example.com",
            "password",
            "+49 123 456789",
            "dummy_template.html"
        )
        assert result is True
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()


def test_invalid_email_raises_error(fake_member):
    fake_member.email = "invalid-email"

    with pytest.raises(ValueError):
        send_report_email(
            fake_member,
            "sender@example.com",
            "password",
            "+49 123 456789",
            "template.html"
        )


def test_missing_template_raises_error(fake_member):
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            format_member_email(fake_member, "+49 123 456789", "missing.html")