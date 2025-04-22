from typing import Dict
from db import get_cursor
from models.member import Member


def load_member(email: str) -> Member:
    """
    Load a single Member from the database, including their title history,
    resident history, and transactions.

    Args:
        email (str): Email of the member to load.

    Returns:
        Member: A Member object with full data.
    """
    with get_cursor() as cur:
        # Load base info
        cur.execute("SELECT * FROM members WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Member '{email}' not found in the database.")

        data = {
            "email": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "title": row[3],
            "is_resident": row[4],
            "created_at": row[5].isoformat(),
            "start_balance": float(row[6]),
            "title_history": {},
            "resident_history": {},
            "transactions": []
        }

        # Title history
        cur.execute("SELECT changed_at, title FROM title_history WHERE member_email = %s", (email,))
        for hist_row in cur.fetchall():
            data["title_history"][hist_row[0].isoformat()] = hist_row[1]

        # Resident history
        cur.execute("SELECT changed_at, is_resident FROM resident_history WHERE member_email = %s", (email,))
        for hist_row in cur.fetchall():
            data["resident_history"][hist_row[0].isoformat()] = hist_row[1]

        # Transactions
        cur.execute("""
            SELECT date, description, amount 
            FROM transactions 
            WHERE member_email = %s
            ORDER BY date
        """, (email,))
        for t_row in cur.fetchall():
            data["transactions"].append({
                "date": t_row[0].isoformat(),
                "description": t_row[1],
                "amount": float(t_row[2])
            })

    return Member.from_dict(data)


def load_all_members() -> Dict[str, Member]:
    """
    Load all members from the database using load_member(email).

    Returns:
        Dict[str, Member]: Dictionary of members indexed by email.
    """
    with get_cursor() as cur:
        cur.execute("SELECT email FROM members ORDER BY last_name, first_name")
        emails = [row[0] for row in cur.fetchall()]

    members = {}
    for email in emails:
        try:
            members[email] = load_member(email)
        except Exception as e:
            print(f"[!] Failed to load {email}: {e}")

    return members


def save_member(member: Member) -> None:
    """
    Insert or update a Member in the database, including their
    title history, resident history, and transactions. Only changed data is updated.

    Args:
        member (Member): Member instance to be saved or updated.
    """
    m = member.to_dict

    with get_cursor() as cur:
        # Save main member info
        cur.execute("""
            INSERT INTO members (
                email, first_name, last_name, title, is_resident,
                created_at, start_balance
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                title = EXCLUDED.title,
                is_resident = EXCLUDED.is_resident,
                start_balance = EXCLUDED.start_balance;
        """, (
            m["email"],
            m.get("first_name", ""),
            m["last_name"],
            m["title"],
            m["is_resident"],
            m["created_at"],
            m["start_balance"]
        ))

        updated_sections = []

        # --- Title history ---
        cur.execute("SELECT changed_at, title FROM title_history WHERE member_email = %s", (m["email"],))
        existing_titles = {row[0].isoformat(): row[1] for row in cur.fetchall()}

        if m["title_history"] != existing_titles:
            updated_sections.append("title_history")
            cur.execute("DELETE FROM title_history WHERE member_email = %s", (m["email"],))
            for date_str, title in m["title_history"].items():
                cur.execute("""
                    INSERT INTO title_history (member_email, changed_at, title)
                    VALUES (%s, %s, %s)
                """, (m["email"], date_str, title))

        # --- Resident history ---
        cur.execute("SELECT changed_at, is_resident FROM resident_history WHERE member_email = %s", (m["email"],))
        existing_residents = {row[0].isoformat(): row[1] for row in cur.fetchall()}

        if m["resident_history"] != existing_residents:
            updated_sections.append("resident_history")
            cur.execute("DELETE FROM resident_history WHERE member_email = %s", (m["email"],))
            for date_str, is_resident in m["resident_history"].items():
                cur.execute("""
                    INSERT INTO resident_history (member_email, changed_at, is_resident)
                    VALUES (%s, %s, %s)
                """, (m["email"], date_str, is_resident))

        # --- Transactions ---
        cur.execute("""
            SELECT date, description, amount
            FROM transactions
            WHERE member_email = %s
            ORDER BY date
        """, (m["email"],))
        existing_transactions = [
            {
                "date": row[0].isoformat(),
                "description": row[1],
                "amount": float(row[2])
            } for row in cur.fetchall()
        ]

        if m["transactions"] != existing_transactions:
            updated_sections.append("transactions")
            cur.execute("DELETE FROM transactions WHERE member_email = %s", (m["email"],))
            for tx in m["transactions"]:
                cur.execute("""
                    INSERT INTO transactions (member_email, date, description, amount)
                    VALUES (%s, %s, %s, %s)
                """, (m["email"], tx["date"], tx["description"], tx["amount"]))

        # --- Log result ---
        log_msg = f"Saved member: {m['email']}"
        if updated_sections:
            log_msg += f" (updated: {', '.join(updated_sections)})"
        else:
            log_msg += " (no changes in history)"
        print(log_msg)
