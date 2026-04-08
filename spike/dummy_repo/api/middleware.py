"""API middleware - authentication and request processing."""
from services.auth import AuthService


class AuthMiddleware:
    """Middleware that validates auth tokens on incoming requests."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def authenticate(self, request: dict) -> bool:
        """Check if request has a valid auth token."""
        token = request.get("headers", {}).get("Authorization", "")
        if not token:
            return False
        return self.auth_service.verify_token(token)

    def process_request(self, request: dict) -> dict:
        """Process and enrich request before routing."""
        if self.authenticate(request):
            request["authenticated"] = True
        else:
            request["authenticated"] = False
        return request
