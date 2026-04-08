"""Frontend UI components."""
from frontend.views import render_template


class ProductCard:
    """Renders a product card in the UI."""

    def __init__(self, name: str, price: str, image_url: str):
        self.name = name
        self.price = price
        self.image_url = image_url

    def render(self) -> str:
        """Render the product card as HTML."""
        template_data = {
            "name": self.name,
            "price": self.price,
            "image": self.image_url,
        }
        return render_template("product_card", template_data)


class NavigationBar:
    """Top navigation bar component."""

    def __init__(self, items: list[str]):
        self.items = items

    def render(self) -> str:
        """Render navigation bar."""
        links = " | ".join(self.items)
        return f"<nav>{links}</nav>"
