from .models import Product
from typing import List

class ProductFormatter:
    def format_product_details(self, product: Product) -> str:
        if product.error:
            return f"Error: {product.error}"
            
        result = f"# {product.name}\n\n"
        result += f"Price: {product.price}\n"
        result += f"Rating: {product.rating}\n"
        result += f"Reviews: {product.reviews_count}\n"
        result += f"Availability: {product.availability}\n"
        result += f"Image URL: {product.image_url}\n"
        result += f"Description: {product.description}\n"
        result += f"Product URL: {product.url}\n"
        return result

    def format_search_results(self, products: List[Product], query: str) -> str:
        if not products:
            return f"No products found for '{query}'"
        
        result = f"# Search Results for '{query}'\n\n"
        for i, product in enumerate(products):
            result += f"## {i+1}. {product.name}\n"
            result += f"Price: {product.price}\n"
            result += f"Rating: {product.rating}\n"
            result += f"URL: {product.url}\n\n"
        
        return result
