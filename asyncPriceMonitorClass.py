import asyncio
import aiohttp
from bs4 import BeautifulSoup
import smtplib
import time
from abc import ABC, abstractmethod
import yaml
import logging
import os
from dotenv import load_dotenv
from database_manager import DatabaseManager
import re
import random
from fake_useragent import UserAgent


db_manager = DatabaseManager('price_monitor.db')

# Use db_manager methods as needed in your application


# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class AsyncPriceMonitor:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.db_manager = DatabaseManager(self.config['database']['file'])
        self.scrapers = {}
        for item in self.config['items']:
            platform = item['platform']
            if platform not in self.scrapers:
                self.scrapers[platform] = AsyncScraperFactory.get_scraper(
                    platform)
        self.user_agent = UserAgent()
        
    async def fetch_with_retry(self, session, url, max_retries=5):
        for attempt in range(max_retries):
            try:
                headers = {"User-Agent": self.user_agent.random}
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 503:
                        wait_time = (2 ** attempt) + random.uniform(1, 3)
                        logging.warning(
                            f"Received 503 error. Retrying in {wait_time:.2f} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        response.raise_for_status()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = (2 ** attempt) + random.uniform(1, 3)
                logging.warning(
                    f"Request failed. Retrying in {wait_time:.2f} seconds... Error: {str(e)}")
                await asyncio.sleep(wait_time)
        raise ValueError(f"Failed to fetch page after {max_retries} attempts")

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            return yaml.safe_load(file)

    async def check_price(self, session, item):
        url = item['url']
        desired_price = item['desired_price']
        platform = item['platform']

        try:
            async with session.get(url) as response:
                page_content = await response.text()

            soup = BeautifulSoup(page_content, 'html.parser')

            scraper = self.scrapers[platform]
            title = await scraper.get_title(soup)
            price = await scraper.get_price(soup)

            # Database operations
            product_id = self.db_manager.add_or_update_product(
                url, title, platform, desired_price)
            self.db_manager.add_price_history(product_id, price)

            if price < desired_price:
                await self.send_mail(title, price, url, desired_price)

            logging.info(f"Title: {title}, Current price: {price}")
        except Exception as e:
            logging.error(f"Error checking price for {url}: {str(e)}")

    async def check_prices(self):
        async with aiohttp.ClientSession(headers={"User-Agent": self.config['user_agent']}) as session:
            tasks = [self.check_price(session, item)
                     for item in self.config['items']]
            await asyncio.gather(*tasks)

    async def check_single_price(self, url, platform):
        try:
            async with aiohttp.ClientSession() as session:
                page_content = await self.fetch_with_retry(session, url)

            soup = BeautifulSoup(page_content, 'html.parser')

            scraper = self.scrapers[platform]
            price = await scraper.get_price(soup)

            if price is None:
                raise ValueError("Price could not be extracted from the page")
            if price == float('inf') or price <= 0:
                raise ValueError(f"Invalid price value: {price}")

            logging.info(
                f"Successfully retrieved price for {url}: ${price:.2f}")
            return price
        except Exception as e:
            logging.error(f"Error checking price for {url}: {str(e)}")
            raise ValueError(f"Unable to retrieve a valid price: {str(e)}")

    async def test_scraper(self, url, platform):
        try:
            async with aiohttp.ClientSession() as session:
                page_content = await self.fetch_with_retry(session, url)

            soup = BeautifulSoup(page_content, 'html.parser')

            scraper = self.scrapers[platform]
            title = await scraper.get_title(soup)
            price = await scraper.get_price(soup)

            price_str = f"${price:.2f}" if price is not None else "N/A"
            return f"Title: {title}\nPrice: {price_str}"
        except Exception as e:
            return f"Error testing scraper: {str(e)}"


class AsyncPlatformScraper(ABC):
    @abstractmethod
    async def get_title(self, soup):
        pass

    @abstractmethod
    async def get_price(self, soup):
        pass


class AsyncAmazonScraper(AsyncPlatformScraper):
    async def get_title(self, soup):
        try:
            return soup.find(id="productTitle").get_text().strip()
        except AttributeError:
            logging.error("Could not find product title on Amazon page")
            return "Unknown Product"

    async def get_price(self, soup):
        try:
            # Try to find the price using multiple possible selectors
            price_element = (
                soup.select_one('.a-price .a-offscreen') or
                soup.select_one('#priceblock_ourprice') or
                soup.select_one('#priceblock_dealprice') or
                soup.select_one('.a-size-medium.a-color-price')
            )

            if price_element:
                price_str = price_element.get_text().strip()
                # Remove currency symbols and commas, and handle potential multiple dots
                price_str = re.sub(r'[^\d.]', '', price_str)
                # If there are multiple dots, keep only the last one
                price_str = '.'.join(price_str.split(
                    '.')[-2:]) if price_str.count('.') > 1 else price_str
                return float(price_str)
            else:
                raise ValueError("Price element not found on the page")
        except Exception as e:
            logging.error(f"Error parsing Amazon price: {str(e)}")
            return None


class AsyncEbayScraper(AsyncPlatformScraper):
    async def get_title(self, soup):
        try:
            title_element = soup.find(
                'h1', {'class': 'x-item-title__mainTitle'}) or soup.find(id="itemTitle")
            if title_element:
                return title_element.get_text().strip().replace('Details about', '').strip()
            else:
                logging.warning(
                    "Title element not found using expected selectors. Attempting fallback method.")
                # Fallback method: try to find any h1 tag
                h1_tags = soup.find_all('h1')
                if h1_tags:
                    return h1_tags[0].get_text().strip()
                else:
                    raise ValueError(
                        "No suitable title element found on the page")
        except Exception as e:
            logging.error(
                f"Error finding product title on eBay page: {str(e)}")
            return "Unknown Product"

    async def get_price(self, soup):
        try:
            # Try multiple selectors for the price
            price_element = (
                soup.find('div', {'class': 'x-price-primary'}) or
                soup.find(id="prcIsum") or
                soup.find('span', {'class': 'notranslate'}) or
                soup.find('span', {'itemprop': 'price'})
            )

            if price_element:
                price_str = price_element.get_text().strip()
                # Remove currency symbols and commas
                price_str = re.sub(r'[^\d.]', '', price_str)
                return float(price_str)
            else:
                logging.warning(
                    "Price element not found using expected selectors. Attempting fallback method.")
                # Fallback method: try to find any element with a dollar sign
                price_text = soup.find(text=re.compile(r'\$\d+(\.\d{2})?'))
                if price_text:
                    price_str = re.sub(r'[^\d.]', '', price_text)
                    return float(price_str)
                else:
                    raise ValueError(
                        "No suitable price element found on the page")
        except Exception as e:
            logging.error(f"Error parsing eBay price: {str(e)}")
            return None


class AsyncScraperFactory:
    @staticmethod
    def get_scraper(platform):
        if platform == "amazon":
            return AsyncAmazonScraper()
        elif platform == "ebay":
            return AsyncEbayScraper()
        else:
            raise ValueError(f"Unsupported platform: {platform}")


async def main():
    monitor = AsyncPriceMonitor('config.yaml')
    while True:
        await monitor.check_prices()
        await asyncio.sleep(3600)  # Check every hour

if __name__ == "__main__":
    asyncio.run(main())
