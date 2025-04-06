import json
import os

# Define the path to the settings file (e.g., containing email credentials, config values)
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