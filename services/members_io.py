import json
import os
from models.member import Member


FILENAME = "data/members.json"


def load_all_members() -> dict:
    """
    Loads all members from the JSON file defined by FILENAME.

    Returns:
        dict: A dictionary where each key is a member's email and each value is a Member object.
              Returns an empty dictionary if the file does not exist.

    Raises:
        JSONDecodeError: If the file exists but contains invalid JSON.
    """
    if not os.path.exists(FILENAME):
        return {}
    with open(FILENAME, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {email: Member.from_dict(info) for email, info in data.items()}


def save_all_members(members: dict):
    """
    Saves all members to the JSON file defined by FILENAME.

    Parameters:
        members (dict): A dictionary of Member objects indexed by their email address.

    Side effects:
        Writes a JSON file to disk with properly formatted and indented content.
    """
    data = {email: member.to_dict for email, member in members.items()}
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
