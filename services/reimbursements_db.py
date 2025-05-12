from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from db import get_cursor


def save_reimbursement_items(member_email: str,
                             rows: List[dict]) -> None:
    """
    Save multiple reimbursement items into the database for a given member.

    Args:
        member_email (str): The email of the member submitting the reimbursement.
        rows (List[dict]): A list of dicts, each with keys: 'description', 'date', 'amount', 'receipt_filename'.
    """
    with get_cursor() as cur:
        for row in rows:
            if not row.get("description") or not row.get("date") or not row.get("amount"):
                continue  # Skip incomplete rows
            try:
                cur.execute("""
                            INSERT INTO reimbursement_items (member_email, created_at, description, date, amount, 
                                receipt_filename)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                member_email,
                                datetime.now(),
                                row['description'],
                                row['date'],
                                Decimal(row['amount']),
                                row.get('receipt_filename')
                            ))
            except InvalidOperation:
                continue


def update_bank_details(member_email: str,
                        bank_name: str,
                        iban: str) -> None:
    """
    Save or update the bank details info for the given member.

    Args:
        member_email (str): The email of the member.
        bank_name (str): The name of the bank.
        iban (str): The IBAN string.
    """
    with get_cursor() as cur:
        cur.execute("""
                    INSERT INTO bank_details (member_email, bank_name, iban, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (member_email) DO UPDATE SET bank_name  = EXCLUDED.bank_name,
                                                             iban       = EXCLUDED.iban,
                                                             updated_at = EXCLUDED.updated_at
                    """, (
                        member_email,
                        bank_name.strip(),
                        iban.strip(),
                        datetime.now()
                    ))
