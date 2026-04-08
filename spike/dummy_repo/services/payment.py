"""Payment processing service."""
from database.models import Order, User
from database.connection import DatabasePool
from utils.helpers import format_currency, generate_id


class PaymentService:
    """Handles payment processing for orders."""

    def __init__(self, db_pool: DatabasePool):
        self.db_pool = db_pool

    def process_payment(self, order: Order, payment_method: str) -> dict:
        """Process payment for an order."""
        transaction_id = generate_id("txn")
        amount = format_currency(order.total)
        result = {
            "transaction_id": transaction_id,
            "amount": amount,
            "status": "completed",
            "method": payment_method,
        }
        return result

    def refund(self, transaction_id: str, reason: str) -> dict:
        """Process a refund."""
        refund_id = generate_id("refund")
        return {
            "refund_id": refund_id,
            "original_transaction": transaction_id,
            "reason": reason,
            "status": "processed",
        }
