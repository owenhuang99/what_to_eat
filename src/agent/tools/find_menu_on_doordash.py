from .browser import BrowserTool
import time
import re
import logging
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class FindMenuOnDeliverySiteTool:
    def __init__(self):
        self.browser = BrowserTool()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def find_doordash_menu(self, restaurant_name: str, zipcode: str) -> dict:
        try:
            self.logger.info(f"Searching DoorDash menu for {restaurant_name} in {zipcode}")
            query = f"{restaurant_name} site:doordash.com/menu {zipcode}"
            url = self._search_google_for_doordash(query)
            if not url:
                return {"status": "error", "message": "Could not find DoorDash URL"}

            self.logger.info(f"Opening URL: {url}")
            driver = self.browser.setup_browser()
            driver.get(url)
            time.sleep(5)

            # Scroll to load content
            scroll_pause = 0.5
            scroll_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(0, scroll_height, 500):
                driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(scroll_pause)

            # Cache all <img> tags globally with class StyledImg
            img_elements = driver.find_elements(By.XPATH, "//img[contains(@class, 'StyledImg')]")

            items = driver.find_elements(By.CSS_SELECTOR, "div[data-anchor-id='MenuItem']")
            menu_items = []

            for item in items:
                try:
                    name = item.find_element(By.CSS_SELECTOR, "h3").text
                    price = item.find_element(By.CSS_SELECTOR, "span[class*='Price']").text
                    description = ""
                    p_tags = item.find_elements(By.CSS_SELECTOR, "p")
                    if p_tags:
                        description = p_tags[0].text

                    img_url = ""

                    # Match <img alt="Dish name"> to dish name
                    for img in img_elements:
                        alt_text = img.get_attribute("alt")
                        if alt_text and name.lower() in alt_text.lower():
                            img_url = img.get_attribute("src")
                            break

                    menu_items.append({
                        "name": name,
                        "price": price,
                        "ingredients": description,
                        "image_url": img_url,
                        "category": "",
                        "meal_time": "",
                        "reviews": []
                    })

                except Exception as e:
                    self.logger.error(f"Error parsing menu item: {e}")
                    continue


            # Save raw menu with image URLs to a .txt file
            save_path = f"data/menus/{restaurant_name.lower().replace(' ', '_')}_{zipcode}_menu.txt"
            with open(save_path, "w", encoding="utf-8") as f:
                for entry in menu_items:
                    f.write(f"{entry['name']}\n")
                    f.write(f"{entry['price']}\n")
                    f.write(f"{entry['ingredients']}\n")
                    f.write(f"{entry['image_url']}\n\n")  

            return {
                "status": "success",
                "message": f"Extracted {len(menu_items)} items from DoorDash",
                "menu_items": menu_items,
                "url": url
            }

        except Exception as e:
            self.logger.error(f"Failed to extract DoorDash menu: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"Error: {str(e)}"}