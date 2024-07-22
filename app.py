import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
from asyncPriceMonitorClass import AsyncPriceMonitor
from database_manager import DatabaseManager

# Initialize AsyncPriceMonitor and DatabaseManager
price_monitor = AsyncPriceMonitor('config.yaml')
db_manager = DatabaseManager('price_monitor.db')


def main():
    st.set_page_config(page_title="Price Monitor",
                       page_icon="📊", layout="wide")
    st.title("Price Monitor")

    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Choose a page", ["Dashboard", "Add Product", "View Products"])

    if page == "Dashboard":
        show_dashboard()
    elif page == "Add Product":
        show_add_product()
    elif page == "View Products":
        show_products()


def show_dashboard():
    st.header("Dashboard")
    st.write("Welcome to the Price Monitor Dashboard!")

    try:
        products = db_manager.get_all_products()
        if products:
            st.subheader("Monitoring Summary")
            st.write(f"Total products monitored: {len(products)}")

            platforms = [product[3] for product in products]
            platform_counts = pd.Series(platforms).value_counts()
            fig = px.pie(values=platform_counts.values,
                         names=platform_counts.index, title="Products by Platform")
            st.plotly_chart(fig)
        else:
            st.info(
                "No products are currently being monitored. Add some products to get started!")
    except Exception as e:
        st.error(f"Error retrieving products: {str(e)}")


def show_add_product():
    st.header("Add New Product")
    with st.form("add_product_form"):
        url = st.text_input("Product URL")
        name = st.text_input("Product Name")
        platform = st.selectbox("Platform", ["amazon", "ebay"])
        desired_price = st.number_input(
            "Desired Price", min_value=0.01, step=0.01)
        submitted = st.form_submit_button("Add Product")
        if submitted:
            try:
                db_manager.add_or_update_product(
                    url, name, platform, desired_price)
                st.success(f"Added {name} to monitoring list!")
                with st.spinner('Checking initial price... This may take up to a minute.'):
                    try:
                        price = asyncio.run(
                            price_monitor.check_single_price(url, platform))
                        if price is not None:
                            db_manager.add_price_history(
                                db_manager.get_product_id(url), price)
                            st.write(f"Current price: ${price:.2f}")
                            if price < desired_price:
                                st.success(
                                    f"Price drop alert! Current price (${price:.2f}) is below your desired price (${desired_price:.2f})")
                            else:
                                st.info(
                                    f"Current price (${price:.2f}) is above your desired price (${desired_price:.2f})")
                        else:
                            st.warning(
                                "Couldn't retrieve the current price. It will be updated on the next check.")
                    except Exception as e:
                        st.warning(
                            f"Product added, but couldn't check the price: {str(e)}")
            except Exception as e:
                st.error(f"Error adding product: {str(e)}")

    if st.button("Test Scraper"):
        if url and platform:
            with st.spinner('Testing scraper... This may take up to a minute.'):
                result = asyncio.run(price_monitor.test_scraper(url, platform))
                st.code(result)
        else:
            st.warning(
                "Please enter a URL and select a platform to test the scraper.")


def show_products():
    st.header("Monitored Products")
    try:
        products = db_manager.get_all_products()
        if not products:
            st.info("No products found. Add some products to start monitoring!")
            return

        for product in products:
            with st.expander(product[2]):  # product name
                st.write(f"URL: {product[1]}")
                st.write(f"Platform: {product[3]}")
                st.write(f"Desired Price: ${product[4]:.2f}")

                # Fetch and display price history
                history = db_manager.get_price_history(product[0])
                if history:
                    df = pd.DataFrame(history, columns=['Price', 'Date'])
                    fig = px.line(df, x='Date', y='Price',
                                  title=f'Price History: {product[2]}')
                    st.plotly_chart(fig)
                else:
                    st.write("No price history available yet.")

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"Check Price Now for {product[2]}"):
                        with st.spinner('Checking price...'):
                            check_price_sync(
                                product[1], product[3], product[4])
                with col2:
                    if st.button(f"Edit {product[2]}"):
                        st.session_state.editing_product = product[0]
                        st.experimental_rerun()
                with col3:
                    if st.button(f"Delete {product[2]}"):
                        if db_manager.delete_product(product[0]):
                            st.success(f"Deleted {product[2]}")
                            st.experimental_rerun()
                        else:
                            st.error("Failed to delete product")

        if 'editing_product' in st.session_state:
            edit_product(st.session_state.editing_product)
    except Exception as e:
        st.error(f"Error retrieving products: {str(e)}")


def edit_product(product_id):
    product = db_manager.get_product(product_id)
    if product:
        st.subheader(f"Editing {product[2]}")
        new_name = st.text_input("Product Name", value=product[2])
        new_desired_price = st.number_input(
            "Desired Price", value=float(product[4]), min_value=0.01, step=0.01)
        if st.button("Save Changes"):
            if db_manager.update_product(product_id, new_name, new_desired_price):
                st.success("Product updated successfully")
                del st.session_state.editing_product
                st.experimental_rerun()
            else:
                st.error("Failed to update product")
    else:
        st.error("Product not found")


def check_price_sync(url, platform, desired_price):
    try:
        with st.spinner('Checking price... This may take a moment.'):
            price = asyncio.run(
                price_monitor.check_single_price(url, platform))
        if price is not None:
            db_manager.add_price_history(db_manager.get_product_id(url), price)
            st.write(f"Current price: ${price:.2f}")
            if price < desired_price:
                st.success(
                    f"Price drop alert! Current price (${price:.2f}) is below your desired price (${desired_price:.2f})")
            else:
                st.info(
                    f"Current price (${price:.2f}) is above your desired price (${desired_price:.2f})")
        else:
            st.warning(
                "Unable to retrieve the current price. The product might be unavailable or the page structure might have changed.")
    except Exception as e:
        st.error(f"Error checking price: {str(e)}")
        st.info("The website might be temporarily unavailable. Please try again later or use the 'Test Scraper' button to diagnose the issue.")


if __name__ == "__main__":
    main()
