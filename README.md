# Price Monitor

A Python application for monitoring product prices across various e-commerce platforms using asynchronous operations and a Streamlit web interface.

## Features

- Asynchronous price checking for improved performance
- Support for multiple e-commerce platforms (currently Amazon and eBay)
- SQLite database for storing user data, products, and price history
- Streamlit-based web interface for easy interaction
- Real-time price checking and historical price tracking
- Product management (add, edit, delete)
- Data visualization with price history charts
- Robust error handling and retry mechanisms
- Configurable user agent and scraping parameters

## Tech Stack

- Python 3.7+
- aiohttp for asynchronous HTTP requests
- BeautifulSoup4 for web scraping
- SQLite for database management
- Streamlit for the web interface
- Plotly for data visualization
- YAML for configuration management

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/price-monitor.git
   cd price-monitor
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Copy the `.env.example` file to `.env`
   - Edit the `.env` file and fill in your email credentials (if you want to use email notifications)

4. Configure your items to monitor:
   - Edit the `config.yaml` file to add or modify items you want to monitor

5. Initialize the database:
   - The database will be automatically created when you run the application

## Usage

To run the Streamlit app:
```
streamlit run app.py
```

This will start the web interface where you can:
- View the dashboard with monitoring summary
- Add new products to monitor
- View and manage existing monitored products
- Check prices in real-time
- View price history charts

## Project Structure

- `app.py`: Main Streamlit application
- `asyncPriceMonitorClass.py`: Asynchronous price monitoring logic
- `database_manager.py`: Database operations and management
- `config.yaml`: Configuration file for user agent and monitored items
- `requirements.txt`: List of Python dependencies

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Future Improvements

- Implement user authentication
- Add support for more e-commerce platforms
- Enhance data analysis features
- Implement a more robust notification system
- Optimize performance for larger datasets