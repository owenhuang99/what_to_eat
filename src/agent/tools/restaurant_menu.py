from typing import Dict, Optional
import time
import os
import json
import re
import logging
from datetime import datetime

from bs4 import BeautifulSoup
from PIL import Image
import openai

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import BrowserTool
from .normalize_menu import normalize_with_llm

# Constants
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data/menus")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")


class RestaurantMenuTool:
    def __init__(self, agent=None):
        self.agent = agent
        self.setup_logging()

    def setup_logging(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, f'menu_tool_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _extract_with_vlm(self, image_path: str) -> str:
        img = Image.open(image_path)
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all menu items with their names and prices from this image. Format: 'Item -- Price'"},
                        {"type": "image_url", "image_url": openai.Image.from_pil_image(img)}
                    ]
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def get_menu(self, restaurant_name: str, restaurant_url: Optional[str] = None,
                 uploaded_menu: Optional[str] = None, zipcode: Optional[str] = "00000") -> Dict:
        try:
            self.logger.info(f"Getting menu for {restaurant_name}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)

            # If user uploads menu manually
            if uploaded_menu:
                raw_text = uploaded_menu
                zipcode = self._infer_zipcode_from_context() or zipcode
                normalized = normalize_with_llm(raw_text, restaurant_name, zipcode)
                self.logger.info(f"[LLM-NORMALIZED] Got {len(normalized.get('items', []))} normalized items")
                return {
                    "status": "success",
                    "message": "Normalized menu returned from upload",
                    "menu_items": [dict(item) for item in normalized.get("items", [])]
                }

            # If scraping menu from restaurant website
            if restaurant_url:
                browser = BrowserTool()
                browser.setup_browser()
                driver = browser.get_driver()
                driver.get(restaurant_url)
                driver.set_window_size(1280, 3000)

                screenshot_path = f"/tmp/{restaurant_name.lower().replace(' ', '_')}_menu.png"
                driver.save_screenshot(screenshot_path)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                page_content = driver.page_source
                browser.close()

                # Try HTML scraping first
                menu_text = self.extract_visible_menu_text(page_content)
                raw_text = menu_text

                if not menu_text.strip():
                    self.logger.info("HTML scraping failed — trying VLM fallback")
                    raw_text = self._extract_with_vlm(screenshot_path)

                # Save raw menu text
                raw_txt_path = os.path.join(
                    OUTPUT_DIR,
                    f"{restaurant_name.replace(' ', '_').lower()}_{zipcode}_menu.txt"
                )
                with open(raw_txt_path, "w", encoding="utf-8") as f:
                    f.write(raw_text)
                self.logger.info(f"Saved extracted menu to: {raw_txt_path}")

                # Normalize menu
                zipcode = self._infer_zipcode_from_context() or zipcode
                dish_reviews = self.extract_dish_reviews(page_content)
                normalized = normalize_with_llm(raw_text, restaurant_name, zipcode, reviews=dish_reviews)

                json_path = raw_txt_path.replace(".txt", "_cleaned.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(normalized, f, indent=2)

                return {
                    "status": "success",
                    "message": "Normalized menu returned",
                    "menu_items": [dict(item) for item in normalized.get("items", [])]
                }

            return {
                "status": "request_upload",
                "message": "Menu not found. Please upload a menu text file.",
                "menu_items": []
            }

        except Exception as e:
            self.logger.error(f"Error getting menu: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error getting menu: {str(e)}",
                "menu_items": []
            }

    def extract_visible_menu_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        candidates = soup.find_all(["section", "div", "article"])
        text_blocks = []
        for block in candidates:
            text = block.get_text(separator="\n", strip=True)
            if len(text.splitlines()) >= 5 and any(keyword in text for keyword in
                                                   ["$", "Burrito", "Taco", "Chicken", "Menu", "Steak"]):
                text_blocks.append(text)
        return "\n\n".join(text_blocks)
    
    def extract_dish_reviews(self, html: str) -> dict:
        """
        Extracts dish reviews from DoorDash page HTML.
        Returns a mapping: {dish_name: [review1, review2, ...]}
        """
        soup = BeautifulSoup(html, "html.parser")
        reviews = {}

        # Example: pull all review blocks
        review_blocks = soup.find_all("div", string=re.compile("DoorDash order"))

        for block in review_blocks:
            text = block.get_text(separator="\n")
            for line in text.splitlines():
                for dish in ["Braised Beef & Mushrooms", "Grilled Grass Fed Steak", "Side Grilled Cage Free Chicken"]:
                    if dish.lower() in line.lower():
                        reviews.setdefault(dish, []).append(line.strip())

        return reviews


    def _infer_zipcode_from_context(self) -> str:
        if hasattr(self, "agent") and self.agent:
            return self.agent.conversation_context.get("current_location", "")
        return ""

    def close(self):
        self.logger.info("Menu tool closed")
