from services import settings_loader


def test_get_admin_email(monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "Admin@Example.com")
    assert settings_loader.get_admin_email() == "admin@example.com"


def test_get_monthly_payment_for_residents(monkeypatch):
    monkeypatch.setenv("MONTHLY_PAYMENT_RESIDENTS", "17.50")
    result = settings_loader.get_monthly_payment_for_residents()
    assert isinstance(result, float)
    assert result == 17.50


def test_get_monthly_payment_for_non_residents(monkeypatch):
    monkeypatch.setenv("MONTHLY_PAYMENT_NON_RESIDENTS", "42.00")
    result = settings_loader.get_monthly_payment_for_non_residents()
    assert isinstance(result, float)
    assert result == 42.00
