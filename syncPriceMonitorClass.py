import requests
from bs4 import BeautifulSoup
import smtplib
import time
from abc import ABC, abstractmethod
import yaml
import logging
import os
from dotenv import load_dotenv
from database_manager import DatabaseManager

db_manager = DatabaseManager('price_monitor.db')

# Use db_manager methods as needed in your application


# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class SyncPriceMonitor:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.db_manager = DatabaseManager(self.config['database']['file'])
        self.scrapers = {}
        for item in self.config['items']:
            platform = item['platform']
            if platform not in self.scrapers:
                self.scrapers[platform] = ScraperFactory.get_scraper(platform)

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            return yaml.safe_load(file)

    def check_prices(self):
        for item in self.config['items']:
            url = item['url']
            desired_price = item['desired_price']
            platform = item['platform']

            try:
                headers = {"User-Agent": self.config['user_agent']}
                page = requests.get(url, headers=headers)
                soup = BeautifulSoup(page.content, 'html.parser')

                scraper = self.scrapers[platform]
                title = scraper.get_title(soup)
                price = scraper.get_price(soup)
                
                # Database operations
                product_id = self.db_manager.add_or_update_product(url, title, platform, desired_price)
                self.db_manager.add_price_history(product_id, price)

                if price < desired_price:
                    self.send_mail(title, price, url, desired_price)

                logging.info(f"Title: {title}, Current price: {price}")
            except Exception as e:
                logging.error(f"Error checking price for {url}: {str(e)}")

    def send_mail(self, title, price, url, desired_price):
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASSWORD'))

            subject = f'Price Alert for {title}'
            body = f"The price of {title} has fallen below your desired price of {desired_price}!\nCurrent price: {price}\nCheck it here: {url}"

            msg = f"Subject: {subject}\n\n{body}"

            server.sendmail(os.getenv('EMAIL_USER'),
                            os.getenv('EMAIL_RECIPIENT'), msg)

            logging.info("Email alert sent successfully")
        except Exception as e:
            logging.error(f"Error sending email: {str(e)}")
        finally:
            server.quit()


class PlatformScraper(ABC):
    @abstractmethod
    def get_title(self, soup):
        pass

    @abstractmethod
    def get_price(self, soup):
        pass


class AmazonScraper(PlatformScraper):
    def get_title(self, soup):
        try:
            return soup.find(id="productTitle").get_text().strip()
        except AttributeError:
            logging.error("Could not find product title on Amazon page")
            return "Unknown Product"

    def get_price(self, soup):
        try:
            price_str = soup.find(id="priceblock_ourprice").get_text()
            return float(price_str[2:].replace(',', ''))
        except (AttributeError, ValueError):
            logging.error("Could not parse price from Amazon page")
            return float('inf')


class EbayScraper(PlatformScraper):
    def get_title(self, soup):
        try:
            return soup.find(id="itemTitle").get_text().strip('Details about   ')
        except AttributeError:
            logging.error("Could not find product title on eBay page")
            return "Unknown Product"

    def get_price(self, soup):
        try:
            price_str = soup.find(id="prcIsum").get_text().strip()
            return float(price_str[4:].replace(',', ''))
        except (AttributeError, ValueError):
            logging.error("Could not parse price from eBay page")
            return float('inf')


class ScraperFactory:
    @staticmethod
    def get_scraper(platform):
        if platform == "amazon":
            return AmazonScraper()
        elif platform == "ebay":
            return EbayScraper()
        else:
            raise ValueError(f"Unsupported platform: {platform}")


if __name__ == "__main__":
    monitor = SyncPriceMonitor('config.yaml')
    while True:
        monitor.check_prices()
        time.sleep(3600)  # Check every hour
