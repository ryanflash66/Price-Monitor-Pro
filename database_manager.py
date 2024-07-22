import sqlite3
import logging
from datetime import datetime
import re

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self.create_tables()

    def create_tables(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    desired_price REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                );

                CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
            ''')

    def connect(self):
        self.conn = sqlite3.connect(self.db_file)
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()

    def add_or_update_product(self, url, name, platform, desired_price):
        if not self.is_valid_url(url):
            raise ValueError("Invalid URL provided")

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO products (url, name, platform, desired_price)
                VALUES (?, ?, ?, ?)
            ''', (url, name, platform, desired_price))
            return cursor.lastrowid
        
    def is_valid_url(self, url):
        regex = re.compile(
            r'^https?://'  # http:// or https://
            # domain...
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url is not None and regex.search(url)

    def add_price_history(self, product_id, price):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO price_history (product_id, price)
                VALUES (?, ?)
            ''', (product_id, price))
            return cursor.lastrowid

    def get_all_products(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, url, name, platform, desired_price
                FROM products
            ''')
            return cursor.fetchall()
        
    def get_product_id(self, url):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM products WHERE url = ?
            ''', (url,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_price_history(self, product_id, limit=30):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT price, checked_at
                FROM price_history
                WHERE product_id = ?
                ORDER BY checked_at DESC
                LIMIT ?
            ''', (product_id, limit))
            return cursor.fetchall()
        
    def update_product_price(self, product_id, new_price):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products
                SET desired_price = ?
                WHERE id = ?
            ''', (new_price, product_id))
            return cursor.rowcount > 0  # Returns True if a row was updated
        
    def delete_product(self, product_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            return cursor.rowcount > 0
        
    def get_product(self, product_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            return cursor.fetchone()
        
    def update_product(self, product_id, new_name, new_desired_price):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products
                SET name = ?, desired_price = ?
                WHERE id = ?
            ''', (new_name, new_desired_price, product_id))
            return cursor.rowcount > 0


# Usage example
if __name__ == "__main__":
    db_manager = DatabaseManager('price_monitor.db')

    # Add or update a product
    product_id = db_manager.add_or_update_product(
        'https://example.com/product', 'Test Product', 'amazon', 99.99)

    # Add some price history
    db_manager.add_price_history(product_id, 105.99)
    db_manager.add_price_history(product_id, 102.50)

    # Retrieve all products
    products = db_manager.get_all_products()
    print("All products:", products)

    # Retrieve price history for a product
    history = db_manager.get_price_history(product_id)
    print("Price history:", history)