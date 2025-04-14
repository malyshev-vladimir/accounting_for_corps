import json
import os

# Define the path to the settings file
SETTINGS_PATH = os.path.join("config", "settings.json")


def load_settings():
    """
    Loads application-wide settings from a JSON file.

    Returns:
        dict: A dictionary containing settings loaded from config/settings.json.

    Raises:
        FileNotFoundError: If the settings file is missing.
        json.JSONDecodeError: If the file is not a valid JSON.
    """
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_monthly_payment_for_residents():
    """
    Returns the configured monthly payment for residents of house.
    Falls back to 15.0 if not defined in settings.
    """
    return load_settings().get("monthly_payments", {}).get("monthly_payment_for_residents", 15.0)


def get_monthly_payment_for_non_residents():
    """
    Returns the configured monthly payment for non-residents of house.
    Falls back to 12.5 if not defined in settings.
    """
    return load_settings().get("monthly_payments", {}).get("monthly_payment_for_non_residents", 12.5)
