from typing import List
from db import get_cursor
from models.transaction import Transaction


def load_transactions_by_email(email: str) -> List[Transaction]:
    """
    Load all transactions from the database for a given member email.

    Args:
        email (str): Email of the member.

    Returns:
        List[Transaction]: List of Transaction objects associated with the given email.
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, date, description, amount, transaction_type
            FROM transactions
            WHERE LOWER(member_email) = %s
            ORDER BY date
            """, (email.lower(),))
        rows = cur.fetchall()

    return [
        Transaction(
            transaction_date=row[1],
            description=row[2],
            amount=row[3],
            transaction_type=row[4],
            member_email=email,
            transaction_id=row[0]
        ) for row in rows
    ]


def load_transactions_by_type(email: str, type_number: int) -> List[Transaction]:
    """
        Load all transactions of a specific type for a given member email.

        Args:
            email (str): Member's email.
            type_number (int): Enum value of the transaction type.

        Returns:
            List[Transaction]: List of transactions matching the type.
        """
    with get_cursor() as cur:
        cur.execute("""
                SELECT id, date, description, amount, transaction_type
                FROM transactions
                WHERE member_email = %s AND transaction_type = %s
                ORDER BY date
            """, (email, type_number))
        rows = cur.fetchall()

    return [
        Transaction(
            transaction_date=row[1],
            description=row[2],
            amount=row[3],
            transaction_type=row[4],
            member_email=email,
            transaction_id=row[0]
        ) for row in rows
    ]


def load_transaction_by_id(transaction_id: int) -> Transaction:
    """
    Load a single transaction from the database by its ID.

    Args:
        transaction_id (int): ID of the transaction.

    Returns:
        Transaction: The loaded transaction.

    Raises:
        ValueError: If no transaction with the given ID exists.
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT member_email, date, description, amount, transaction_type
            FROM transactions
            WHERE id = %s
        """, (transaction_id,))
        row = cur.fetchone()

    if not row:
        raise ValueError(f"Transaction with ID {transaction_id} not found.")

    return Transaction(
        transaction_date=row[1],
        description=row[2],
        amount=row[3],
        member_email=row[0],
        transaction_type=row[4],
        transaction_id=transaction_id
    )
