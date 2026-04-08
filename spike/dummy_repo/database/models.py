"""Database models - SQLAlchemy-style ORM definitions."""
from utils.helpers import generate_id, validate_email
from database.connection import DatabasePool


class User:
    """User model."""

    def __init__(self, name: str, email: str):
        self.id = generate_id("user")
        self.name = name
        self.email = email
        self.is_valid = validate_email(email)

    def save(self, pool: DatabasePool):
        """Persist user to database."""
        conn = pool.get_connection()
        # ... save logic ...
        pool.release(conn)


class Product:
    """Product model."""

    def __init__(self, name: str, price: float):
        self.id = generate_id("prod")
        self.name = name
        self.price = price

    def save(self, pool: DatabasePool):
        """Persist product to database."""
        conn = pool.get_connection()
        # ... save logic ...
        pool.release(conn)


class Order:
    """Order model."""

    def __init__(self, user: User, products: list):
        self.id = generate_id("order")
        self.user = user
        self.products = products
        self.total = sum(p.price for p in products)
