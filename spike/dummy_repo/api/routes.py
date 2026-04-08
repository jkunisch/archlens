"""API route handlers."""
from services.payment import PaymentService
from services.auth import AuthService
from api.middleware import AuthMiddleware


class OrderRoutes:
    """HTTP route handlers for order operations."""

    def __init__(self, payment_service: PaymentService, auth_middleware: AuthMiddleware):
        self.payment_service = payment_service
        self.auth_middleware = auth_middleware

    def create_order(self, request: dict) -> dict:
        """POST /orders - create a new order."""
        processed = self.auth_middleware.process_request(request)
        if not processed.get("authenticated"):
            return {"error": "Unauthorized", "status": 401}
        # ... order creation logic ...
        return {"status": 201, "message": "Order created"}

    def get_orders(self, request: dict) -> dict:
        """GET /orders - list orders."""
        processed = self.auth_middleware.process_request(request)
        if not processed.get("authenticated"):
            return {"error": "Unauthorized", "status": 401}
        return {"status": 200, "orders": []}


class AuthRoutes:
    """HTTP route handlers for authentication."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def login(self, request: dict) -> dict:
        """POST /login."""
        email = request.get("body", {}).get("email", "")
        password = request.get("body", {}).get("password", "")
        token = self.auth_service.login(email, password)
        if token:
            return {"status": 200, "token": token}
        return {"status": 401, "error": "Invalid credentials"}
