from datetime import datetime
from db import get_cursor


def log_title_change(member_email: str, new_title: str, changed_by: str) -> None:
    """
    Log a title change for a member.

    If a previous title change exists within the last 3 days,
    it is deleted and replaced with the new one.
    This avoids logging multiple quick changes as separate records.

    Args:
        member_email (str): Email of the member whose title was changed.
        new_title (str): New title value to be recorded.
        changed_by (str): Email of the admin/user who made the change.

    Returns:
        None
    """
    with get_cursor() as cur:
        # Fetch the most recent title change entry for this member
        cur.execute("""
            SELECT id, new_title, changed_at
            FROM title_changes
            WHERE member_email = %s
            ORDER BY changed_at DESC
            LIMIT 1
        """, (member_email,))
        row = cur.fetchone()

        now = datetime.now()

        if row:
            last_id, previous_title, changed_at = row
            delta = now - changed_at

            # Skip logging if the title hasn't actually changed
            if previous_title == new_title:
                return

            # Delete the last entry if it was logged less than 3 days ago
            if delta.days < 3:
                cur.execute("DELETE FROM title_changes WHERE id = %s", (last_id,))

        # Insert the new title change into the log
        cur.execute("""
            INSERT INTO title_changes (member_email, new_title, changed_by)
            VALUES (%s, %s, %s)
        """, (member_email, new_title, changed_by))


def log_residency_change(member_email: str, new_resident: bool, changed_by: str) -> None:
    """
    Log a residency status change for a member.

    If a previous residency change exists within the last 3 days,
    it is deleted and replaced with the new one.
    This prevents logging frequent toggles as separate events.

    Args:
        member_email (str): Email of the member whose residency status changed.
        new_resident (bool): New residency status to be recorded.
        changed_by (str): Email of the admin/user who made the change.

    Returns:
        None
    """
    with get_cursor() as cur:
        # Fetch the most recent residency change entry for this member
        cur.execute("""
            SELECT id, new_resident, changed_at
            FROM residency_changes
            WHERE member_email = %s
            ORDER BY changed_at DESC
            LIMIT 1
        """, (member_email,))
        row = cur.fetchone()

        now = datetime.now()

        if row:
            last_id, previous_status, changed_at = row
            delta = now - changed_at

            # Skip logging if the status hasn't actually changed
            if previous_status == new_resident:
                return

            # Delete the last entry if it was logged less than 3 days ago
            if delta.days < 3:
                cur.execute("DELETE FROM residency_changes WHERE id = %s", (last_id,))

        # Insert the new residency change into the log
        cur.execute("""
            INSERT INTO residency_changes (member_email, new_resident, changed_by)
            VALUES (%s, %s, %s)
        """, (member_email, new_resident, changed_by))


def log_transaction_change(
    transaction_id: int,
    action: str,
    changed_by: str,
    description: str = ""
) -> None:
    """
    Log the change in the transaction.

    This function logs actions such as 'create', 'update', or 'delete' for a given transaction.

    Args:
        transaction_id (int): The ID of the affected transaction.
        action (str): The action performed (e.g., 'create', 'update', 'delete').
        changed_by (str): The email of the admin or user who performed the action.
        description (str): A description of the action being logged (default is empty).
    """
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO transaction_change_log (
                transaction_id,
                action,
                changed_by,
                description
            )
            VALUES (%s, %s, %s, %s)
        """, (
            transaction_id,
            action,
            changed_by,
            description
        ))
