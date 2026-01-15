from mcp.server.fastmcp import FastMCP
from .scraper import AmazonScraper
from .formatter import ProductFormatter
from .utils import clean_amazon_url
import httpx
from urllib.parse import urlparse

class AmazonMCPServer:
    def __init__(self, scraper: AmazonScraper = None, formatter: ProductFormatter = None):
        self.mcp = FastMCP(
            "Amazon Scraper",
            instructions="""
            # Amazon Scraper Server
            
            This server provides access to Amazon products through various tools.
            For search products, identify the keywords and number of results you want to get from the user input
            
            ## Available Tools
            - `scrape_product(product_url)` - Scrape a product from Amazon
            - `search_products(query, max_results)` - Search for products on Amazon
            """
        )
        self.scraper = scraper or AmazonScraper()
        self.formatter = formatter or ProductFormatter()
        self._register_tools()

    def _register_tools(self):
        @self.mcp.tool()
        async def scrape_product(product_url: str) -> str:
            """Scrape product information from an Amazon product URL"""
            try:
                parsed_url = urlparse(product_url)
                if 'amazon' not in parsed_url.netloc.lower():
                    return "Error: Please provide a valid Amazon product URL"
                
                product = await self.scraper.scrape_product(product_url)
                return self.formatter.format_product_details(product)
                
            except httpx.HTTPStatusError as e:
                return f"HTTP Error: {e.response.status_code} - {e.response.reason_phrase}"
            except Exception as e:
                return f"Error scraping product: {str(e)}"

        @self.mcp.tool()
        async def search_products(query: str, max_results: int = 5) -> str:
            """Search for products on Amazon and return results"""
            try:
                products = await self.scraper.search_products(query, max_results)
                return self.formatter.format_search_results(products, query)
            except Exception as e:
                return f"Error searching products: {str(e)}"

    def run(self):
        self.mcp.run(transport="stdio")

def main():
    server = AmazonMCPServer()
    server.run()

if __name__ == "__main__":
    main()
