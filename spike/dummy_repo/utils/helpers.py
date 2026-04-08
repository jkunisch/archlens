"""Shared utility functions used across all layers."""
import hashlib
import datetime


def generate_id(prefix: str) -> str:
    """Generate a unique ID with the given prefix."""
    timestamp = datetime.datetime.now().isoformat()
    raw = f"{prefix}_{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Format a monetary amount for display."""
    symbols = {"EUR": "€", "USD": "$", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[-1]
