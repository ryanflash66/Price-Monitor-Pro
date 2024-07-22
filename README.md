# Price Monitor

A Python application for monitoring product prices across various e-commerce platforms.

## Features

- Asynchronous and synchronous price checking
- Support for multiple e-commerce platforms (currently Amazon and eBay)
- Database storage for user data, products, and price history
- Email notifications for price drops
- Streamlit-based web interface

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
   - Edit the `.env` file and fill in your email credentials

4. Configure your items to monitor:
   - Edit the `config.yaml` file to add or modify items you want to monitor

5. Initialize the database:
   - Run the following command to set up the database:
     ```
     python database_manager.py
     ```

## Usage

To run the Streamlit app:
```
streamlit run app.py
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.