from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Product:
    name: str = "Product name not found"
    price: str = "Price not available"
    image_url: str = "Image not found"
    rating: str = "Rating not available"
    reviews_count: str = "Reviews not available"
    availability: str = "Availability not found"
    description: str = "Description not available"
    url: str = ""
    error: Optional[str] = None

@dataclass
class SearchResult:
    query: str
    products: List[Product] = field(default_factory=list)
