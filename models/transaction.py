import logging
from decimal import Decimal
from datetime import date
from db import get_cursor
from services.logging_db import log_transaction_change
from models.transaction_type import TransactionType


class Transaction:
    """
    Represents a single financial transaction, linked to a member.
    """

    def __init__(self,
                 transaction_date: date,
                 description: str,
                 amount: Decimal,
                 member_email: str,
                 transaction_type: TransactionType = TransactionType.CUSTOM,
                 transaction_id: int = None):
        self.date = transaction_date
        self.description = description
        self.amount = Decimal(amount)
        self.member_email = member_email
        self.type = transaction_type
        self.id = transaction_id

    def save(self, changed_by: str):
        """
        Save this transaction to the database and log creation.

        Args:
            changed_by (str): Email of the user/admin creating the transaction.
        """
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO transactions (member_email, date, description, amount, transaction_type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (self.member_email, self.date, self.description, self.amount, self.type.value))
            self.id = cur.fetchone()[0]

        log_transaction_change(
            self.id,
            "create",
            changed_by,
            f"Created transaction: {self.description}"
        )

    def update(
            self,
            new_date: date = None,
            new_description: str = None,
            new_amount: float = None,
            changed_by: str = "",
            note: str = ""
    ):
        """
        Update the transaction in the database and log the change.

        Note: The transaction type cannot be changed. To change the type,
        delete the transaction and create a new one.

        Args:
            new_date (date, optional): New transaction date.
            new_description (str, optional): New description.
            new_amount (float, optional): New amount.
            changed_by (str): Email of the user making the change.
            note (str): Optional log note.
        """
        if self.id is None:
            raise ValueError("Cannot update transaction without ID.")

        # Keep current values for any omitted parameters
        new_date = new_date or self.date
        new_description = new_description or self.description
        new_amount = new_amount if new_amount is not None else self.amount

        with get_cursor() as cur:
            cur.execute("""
                UPDATE transactions
                SET date = %s, description = %s, amount = %s
                WHERE id = %s
            """, (new_date, new_description, new_amount, self.id))

        log_transaction_change(
            self.id,
            "update",
            changed_by,
            note or f"Updated transaction: {new_description}"
        )

        self.date = new_date
        self.description = new_description
        self.amount = Decimal(new_amount)

    def delete(self, changed_by: str) -> bool:
        """
        Delete the transaction from the database and log the action.

        Args:
            changed_by (str): The admin/user who is performing the deletion.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """

        if self.id is None:
            logging.error("[!] Cannot delete transaction without ID.")
            return False

        try:
            with get_cursor() as cur:
                # Execute the DELETE statement to remove the transaction
                cur.execute(
                    "DELETE FROM transactions WHERE id = %s AND member_email = %s",
                    (self.id, self.member_email)
                )
                # If one row was deleted, return True
                if cur.rowcount == 1:
                    # Log after successful deletion
                    log_transaction_change(
                        transaction_id=self.id,
                        action="delete",
                        changed_by=changed_by,
                        description=f"Deleted transaction: {self.description}"
                    )
                    logging.info(f"[✓] Deleted transaction {self.id} for {self.member_email}")
                    return True
                else:
                    # If no rows were deleted, return False
                    logging.warning(f"[!] No transaction found for ID {self.id}")
                    return False

        except Exception as e:
            # Log any exceptions that occur during the deletion process
            logging.error(f"[!] Exception while deleting transaction {self.id}: {e}")
            return False
