from typing import List
from db import get_cursor
from models.member import Member


def load_member_by_email(email: str) -> Member:
    """
    Load a single Member from the database by email.

    Args:
        email (str): Email of the member to load.

    Returns:
        Member: A Member object with full data.
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT email, last_name, first_name, title, is_resident, created_at, start_balance
            FROM members WHERE email = %s
        """, (email,))
        row = cur.fetchone()

        if not row:
            raise ValueError(f"Member '{email}' not found in the database.")

    return Member(
            email=row[0],
            last_name=row[1],
            first_name=row[2] or "",
            title=row[3],
            is_resident=row[4],
            created_at=row[5],
            start_balance=row[6]
        )


def load_all_members() -> List[Member]:
    """
    Load all members from the database using load_member(email).

    Returns:
        List[Member]: List of Member objects.
    """
    with get_cursor() as cur:
        cur.execute("SELECT email FROM members ORDER BY last_name, first_name")
        emails = [row[0] for row in cur.fetchall()]

    members = []
    for email in emails:
        try:
            member = load_member_by_email(email)
            members.append(member)
        except Exception as e:
            print(f"[!] Failed to load {email}: {e}")

    return members
