from typing import Dict
import time
import os
from datetime import datetime
import logging
from .browser import BrowserTool
from selenium.webdriver.common.by import By

class LocateRestaurantTool:
    """
    A tool for locating a restaurant by name and zip code.
    """
    def __init__(self):
        self.browser = BrowserTool()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'location_search_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def search_restaurant(self, restaurant_name: str, zip_code: str) -> Dict:
        """Search for a restaurant by name and zip code"""
        try:
            self.logger.info(f"Searching for restaurant: {restaurant_name} in {zip_code}")
            
            # Setup browser if not already done
            if not self.browser.driver:
                self.browser.setup_browser()
            
            # Construct the search URL
            search_url = f"https://www.google.com/search?q={restaurant_name}+{zip_code}"
            self.browser.driver.get(search_url)
            
            time.sleep(2)
            
            # Attempt to extract from Maps panel
            try:
                maps_panel = self.browser.driver.find_element(By.CSS_SELECTOR, "div[data-attrid='kc:/location/location:address']")
                if maps_panel:
                    address = maps_panel.text

                    try:
                        hours = self.browser.driver.find_element(By.CSS_SELECTOR, "div[data-attrid='kc:/location/location:hours']").text
                    except:
                        hours = "Hours not available"

                    try:
                        phone = self.browser.driver.find_element(By.CSS_SELECTOR, "div[data-attrid='kc:/collection/knowledge_panels/has_phone:phone']").text
                    except:
                        phone = "Phone not available"

                    try:
                        url = self.browser.driver.find_element(By.CSS_SELECTOR, "a[data-url]").get_attribute("href")
                    except:
                        url = self.browser.driver.current_url

                    return {
                        "status": "success",
                        "message": f"Located restaurant in Google Maps:\nAddress: {address}\nHours: {hours}\nPhone: {phone}",
                        "url": url
                    }
            except Exception as e:
                self.logger.warning(f"Could not find Google Maps panel: {str(e)}")

            # Try fallback to search results
            selectors = ["div.g", "div.tF2Cxc", "div.yuRUbf"]
            matched_restaurants = []

            for selector in selectors:
                results = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                for result in results[:5]:  # Limit to top 5
                    try:
                        title = result.find_element(By.CSS_SELECTOR, "h3").text
                        link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                        snippet = result.find_element(By.CSS_SELECTOR, "div.VwiC3b, div.IsZvec").text
                        matched_restaurants.append({
                            "title": title,
                            "url": link,
                            "description": snippet
                        })
                    except:
                        continue

            if len(matched_restaurants) > 1:
                return {
                    "status": "user_select",
                    "restaurants": matched_restaurants,
                    "message": f"Found {len(matched_restaurants)} possible matches. Please choose one."
                }
            elif matched_restaurants:
                return {
                    "status": "success",
                    "message": f"Located restaurant in search results:\nTitle: {matched_restaurants[0]['title']}",
                    "url": matched_restaurants[0]["url"]
                }
            else:
                return {
                    "status": "error",
                    "message": "No results found in search"
                }

        except Exception as e:
            self.logger.error(f"Error during restaurant search: {str(e)}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }

    def close(self):
        """Close all resources"""
        self.browser.close()
        self.logger.info("Restaurant location search tool closed")
