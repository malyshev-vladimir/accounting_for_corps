import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def get_admin_email() -> str:
    """
    Returns the configured administrator email from environment.

    Returns:
        str: The admin email address.
    """
    return os.getenv("EMAIL_ADDRESS", "").lower()


def get_monthly_payment_for_residents():
    """
    Returns the configured monthly payment for residents of house.
    """
    return float(os.environ["MONTHLY_PAYMENT_RESIDENTS"])


def get_monthly_payment_for_non_residents():
    """
    Returns the configured monthly payment for non-residents of house.
    """
    return float(os.environ["MONTHLY_PAYMENT_NON_RESIDENTS"])
