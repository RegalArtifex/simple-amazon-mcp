import httpx
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List
from .models import Product
from .utils import clean_amazon_url

class AmazonScraper:
    def __init__(self, base_url: str = "https://www.amazon.in"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
        }

    async def fetch_page(self, url: str, retries: int = 3) -> str:
        for i in range(retries):
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, headers=self.headers, timeout=20.0)
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 503:
                        if i < retries - 1:
                            await asyncio.sleep(2 * (i + 1))  # Exponential backoff
                            continue
                    response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if i == retries - 1:
                    raise e
            except Exception as e:
                if i == retries - 1:
                    raise e
        return ""

    def clean_price(self, price_text: str) -> str:
        if not price_text:
            return "Price not available"
        # Extract digits and decimal point
        cleaned = "".join(re.findall(r'[\d.,]+', price_text.strip()))
        if cleaned:
            return f"₹{cleaned}"
        return "Price not available"

    def extract_product_data(self, html_content: str, url: str) -> Product:
        soup = BeautifulSoup(html_content, 'html.parser')
        product = Product(url=url)

        try:
            # Extract product name
            name_selectors = ['#productTitle', 'h1.a-size-large', '.a-size-large.product-title-word-break']
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    product.name = name_elem.get_text().strip()
                    break

            # Extract price
            price_selectors = [
                '.a-price .a-offscreen',
                '.a-price-whole',
                '#priceblock_ourprice',
                '#priceblock_dealprice',
                '.a-color-price'
            ]
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    product.price = self.clean_price(price_elem.get_text())
                    break

            # Extract image URL
            image_selectors = [
                '#landingImage',
                '#imgBlkFront',
                '#main-image',
                '.a-dynamic-image'
            ]
            for selector in image_selectors:
                img_elem = soup.select_one(selector)
                if img_elem:
                    # Check Various attributes
                    img_url = (img_elem.get('data-old-hires') or 
                              img_elem.get('data-a-dynamic-image') or 
                              img_elem.get('src'))
                    
                    if img_url and img_url.startswith('{'):
                        # It's a JSON dict of URLs
                        try:
                            # Usually the first key is the highest res URL
                            img_url = list(json.loads(img_url).keys())[0]
                        except:
                            pass
                            
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        product.image_url = img_url
                        break

            # Extract rating
            rating_selectors = ['.a-icon-star .a-icon-alt', '.a-icon-alt', '#acrCustomerReviewText']
            for selector in rating_selectors:
                rating_elem = soup.select_one(selector)
                if rating_elem:
                    txt = rating_elem.get_text()
                    if "out of 5" in txt or "stars" in txt:
                        rating_match = re.search(r'(\d+\.?\d*)', txt)
                        if rating_match:
                            product.rating = f"{rating_match.group(1)} out of 5"
                            break

            # Extract reviews count
            reviews_elem = soup.select_one('#acrCustomerReviewText')
            if reviews_elem:
                reviews_match = re.search(r'(\d+(?:,\d+)*)', reviews_elem.get_text())
                if reviews_match:
                    product.reviews_count = f"{reviews_match.group(1)} reviews"

            # Extract availability
            avail_selectors = ['#availability span', '.a-color-success', '.a-color-price']
            for selector in avail_selectors:
                avail_elem = soup.select_one(selector)
                if avail_elem:
                    product.availability = avail_elem.get_text().strip()
                    break

            # Extract description
            desc_selectors = ['#productDescription p', '#feature-bullets .a-list-item', '#productDescription']
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    product.description = desc_elem.get_text().strip()
                    break

        except Exception as e:
            product.error = f"Error parsing product data: {str(e)}"

        return product

    async def scrape_product(self, product_url: str) -> Product:
        html_content = await self.fetch_page(product_url)
        return self.extract_product_data(html_content, product_url)

    async def search_products(self, query: str, max_results: int = 5) -> List[Product]:
        search_url = f"{self.base_url}/s?k={query.replace(' ', '+')}"
        html_content = await self.fetch_page(search_url)
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        # Try different container selectors
        containers = soup.select('[data-component-type="s-search-result"]')
        if not containers:
            containers = soup.select('.s-result-item[data-asin]')

        for container in containers:
            if len(products) >= max_results:
                break
                
            try:
                # Skip sponsored products if they are weirdly structured
                if "AdHolder" in container.get('class', []):
                    # continue # Optional: filter ads
                    pass

                p = Product()
                
                # Name
                name_elem = (container.select_one('h2 a span') or 
                            container.select_one('.a-size-medium.a-color-base.a-text-normal') or
                            container.select_one('.a-size-base-plus.a-color-base.a-text-normal'))
                if name_elem: 
                    p.name = name_elem.get_text().strip()
                else:
                    continue # Skip result if no name
                
                # URL
                url_elem = container.select_one('h2 a') or container.select_one('a.a-link-normal.s-no-outline')
                if url_elem:
                    p_url = url_elem.get('href')
                    if p_url:
                        if p_url.startswith('/'): p_url = self.base_url + p_url
                        p.url = p_url
                
                # Price
                price_elem = container.select_one('.a-price .a-offscreen') or container.select_one('.a-price-whole')
                if price_elem: 
                    p.price = self.clean_price(price_elem.get_text())
                
                # Image
                img_elem = container.select_one('img.s-image')
                if img_elem: 
                    p.image_url = img_elem.get('src') or "Image not found"
                
                # Rating
                rating_elem = container.select_one('.a-icon-alt')
                if rating_elem:
                    rating_match = re.search(r'(\d+\.?\d*)', rating_elem.get_text())
                    if rating_match: 
                        p.rating = f"{rating_match.group(1)} out of 5"
                
                products.append(p)
            except Exception:
                continue
        
        return products
