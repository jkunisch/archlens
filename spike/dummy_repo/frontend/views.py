"""Frontend views - renders pages by calling the API layer."""
from api.routes import OrderRoutes, AuthRoutes


def render_template(template_name: str, data: dict) -> str:
    """Render an HTML template with data."""
    return f"<div class='{template_name}'>{data}</div>"


class DashboardView:
    """Dashboard page view."""

    def __init__(self, order_routes: OrderRoutes):
        self.order_routes = order_routes

    def render(self, request: dict) -> str:
        """Render the dashboard page."""
        orders = self.order_routes.get_orders(request)
        return render_template("dashboard", {"orders": orders})


class LoginView:
    """Login page view."""

    def __init__(self, auth_routes: AuthRoutes):
        self.auth_routes = auth_routes

    def render(self, request: dict) -> str:
        """Render the login page."""
        return render_template("login", {"action": "/login"})
