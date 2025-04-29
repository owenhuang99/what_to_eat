from typing import Dict, List
import os
from datetime import datetime
import logging
import json
import re
import requests
from io import BytesIO
from PIL import Image
import concurrent.futures
import openai

class RestaurantRecommendationsTool:
    """
    A tool for getting recommendations for dishes based on menu, health data, and budget.
    """
    def __init__(self, agent):
        self.setup_logging()
        self.agent = agent  # Store reference to the agent
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'recommendations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_image_with_llm(self, item_name, item_description=None):
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.error("OPENAI_API_KEY environment variable not set")
                return None, None

            # Build prompt
            english_name = item_name
            if any(ord(c) > 127 for c in item_name):
                translation_prompt = f'Translate to English: "{item_name}"'
                english_name = self.agent.ask_llm(translation_prompt).strip()

            prompt = f"Create a realistic food photograph of '{english_name}'. "
            if item_description:
                prompt += f"The dish contains {item_description}. "
            prompt += (
                "Create an image that looks like it was casually photographed in the restaurant with an iPhone, "
                "not a professional studio shot. Natural restaurant lighting, realistic plating, slight imperfections. "
                "No phone frame. Background should be realistic and restaurant-like."
            )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "dall-e-2",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024"
            }

            self.logger.info(f"Sending image generation request to OpenAI")

            response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=data)
            response.raise_for_status()
            image_url = "" # initialize url to prevent error
            image_url = response.json()["data"][0]["url"]

            image_response = requests.get(image_url, timeout=45)
            image_response.raise_for_status()
            return Image.open(BytesIO(image_response.content)), image_url
        
        except Exception as e:
            self.logger.error(f"Image download failed, fallback to image URL only: {e}")
            return None, image_url

    def get_recommendations(self, menu_items: List[Dict], health_data: Dict, budget: float = None, food_preference: str = None, debug_prompt: bool = True) -> Dict:
        """Get personalized recommendations based on menu, health data, budget, and food preferences"""
        try:
            self.logger.info("Getting recommendations")
            self.logger.info(f"Received budget parameter: {budget}")
            self.logger.info(f"Received food preference: {food_preference}")
            
            # Format menu items for prompt
            menu_text = "\n".join([
                json.dumps({
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "category": item.get("category", ""),
                    "ingredients": item.get("ingredients", ""),
                    "reviews": item.get("reviews", [])
                }, ensure_ascii=False)
                for item in menu_items
            ])
            self.logger.info(f"Received menu_text: {menu_text}")

            
            # Format health data for prompt
            health_text = ""
            if health_data:
                health_text = "\n".join([f"{k}: {v}" for k, v in health_data.items() if k != "user_id"])
            self.logger.info(f"Received health_text: {health_text}")
            
            # Format budget information
            budget_text = "No specific budget limit"
            if budget is not None:
                if isinstance(budget, dict):
                    # Handle min/max budget range
                    budget_text = f"${budget['min']:.2f} - ${budget['max']:.2f}"
                else:
                    # Handle single budget number
                    budget_text = f"${budget:.2f}"
            self.logger.info(f"Received budget_text: {budget_text}")
            
            # Format food preference information
            preference_text = "No specific food preference"
            if food_preference is not None and food_preference.strip():
                preference_text = food_preference
            self.logger.info(f"Received preference_text: {preference_text}")
            
            # Get restaurant name from context
            restaurant_name = self.agent.conversation_context.get("current_restaurant", "the restaurant")
            self.logger.info(f"Received restaurant_name: {restaurant_name}")
            # Create prompt for LLM
            prompt = f"""
            You are a helpful restaurant assistant recommending dishes from {restaurant_name} based on the menu, user's health data, budget, and preferences.
            For each dish, return:
            - Dish name and price
            - Ingredients
            - A short customer review summary(if available)
            - A brief explanation of why it's recommended (e.g., based on ingredients, reviews, or price)

            Menu (including dish name, price, category, ingredients, and customer reviews):
            {menu_text}
            
            User's Budget: {budget_text}
            
            User's Food Preferences: {preference_text}
            
            User's Health Data:
            {health_text}
            
            BUDGET GUIDELINES:
            - Try to recommend dishes that, when combined and added to the tax and tip, stay within the user's budget of {budget_text}
            - If the budget is limited, prioritize healthier options that fit within the budget
            - If very few dishes fit within budget, recommend the most affordable healthy options
            
            FOOD PREFERENCE GUIDELINES:
            - Prioritize dishes that match the user's food preferences
            - If no exact matches are found, recommend similar dishes that align with their preferences
            - Consider both the user's health data and food preferences when making recommendations

            HEALTH GUIDELINES:
            - Avoid any dishes containing ingredients listed in user's dietary restrictions
            - Avoid recommending dishes that might worsen user's diseases, here are some examples:
                - For users with diabetes: Avoid high-sugar dishes and refined carbohydrates, Recommend dishes with low glycemic index
                - For users with hypertension: Avoid high-sodium dishes, Recommend dishes rich in potassium, magnesium and fiber
                - For users with heart disease: Avoid dishes high in saturated fats and cholesterol, Recommend dishes with heart-healthy fats (olive oil, avocado)
            - Recommend dishes that are suitable for user's dietary goals, here are some examples:
                - Weight Loss: Recommend low-calorie, high-protein dishes with vegetables
                - Muscle Building: Prioritize high-protein dishes
                - Low Carb: Avoid pasta, bread, rice dishes; recommend protein and vegetable-based options
                - Low Fat: Suggest lean proteins and steamed/grilled preparations
                - Low Sodium: Avoid heavily seasoned dishes; recommend fresh preparations
                - High Protein: Prioritize lean meat, fish, legume-based dishes
                - High Fiber: Recommend dishes with whole grains, legumes, vegetables       
            
            RESPONSE GUIDELINES:           
            Return your recommendations in the following format:
            
            <Recommendation Summary>

            <Recommendation Details>
            Recommended dishes:
            1. <Dish Name> - <Dish Price>  
            - <Dish Ingredients>  
            - <Customer Review Summary> 
            - <Recommendation Reasoning>
            2. <Dish Name> - <Dish Price> 
            - <Dish Ingredients> 
            - <Customer Review Summary> 
            - <Recommendation Reasoning>
            3. <Dish Name> - <Dish Price> 
            - <Dish Ingredients> 
            - <Customer Review Summary> 
            - <Recommendation Reasoning>

            <Cost Breakdown>
            Pre-tax total: $60
            After tax total: $70
            After tips total: $80(10%), $90(15%), $100(20%)

            Keep your response friendly, conversational, and focused on the food recommendations.
            """
            
            print("="*20)
            print("Everything before debug_prompt looks good!")
            ## Output Prompt on Console
            if debug_prompt:
                print("\n======== RECOMMENDATION PROMPT ========")
                print(prompt)
                print("=======================================\n")
                
                # Also save to a file for easier viewing
                debug_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'last_prompt.txt')
                with open(debug_file, 'w') as f:
                    f.write(prompt)
                self.logger.info(f"Prompt saved to {debug_file}")
            
            # Always log the prompt
            self.logger.info(f"Generated prompt: {prompt}")
            
            # Get response from agent's LLM
            response = self.agent.ask_llm(prompt)
            self.logger.info(f"LLM response: {response}")
            
            # Clean the response to ensure it's plain text
            cleaned_response = response.strip()
            
            # Remove any code blocks if present
            if "```" in cleaned_response:
                parts = cleaned_response.split("```")
                # Take the part that looks like our desired format
                for part in parts:
                    if "Recommended dishes:" in part:
                        cleaned_response = part
                        break
            
            # Store the recommendation response in the agent context for later use
            self.agent.conversation_context["last_recommendations"] = cleaned_response
            
            # Format the response for the UI
            return {
                "status": "success",
                "message": cleaned_response,
                "menu_items": [],  # We don't need menu items since we're returning plain text
            }
                
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {str(e)}")
            return {
                "status": "error",
                "message": "I couldn't generate recommendations at this time. Would you like to try with different questions?",
                "menu_items": [],
            }
            
    def generate_dish_images(self, menu_items=None, num_dishes=3):
        """
        This is a separate method to generate dish images without text recommendations.
        
        Args:
            menu_items: List of menu items, or None to use items from agent context
            num_dishes: Maximum number of dishes to generate images for
            
        Returns:
            Dict with status, message and dish_images
        """
       
        try:
            self.logger.info("Generating dish images")
            
            # Use provided menu_items or get from agent context
            if menu_items is None:
                menu_items = self.agent.conversation_context.get("menu_items", [])
                
            if not menu_items:
                return {
                    "status": "error",
                    "message": "No menu items available to generate images",
                    "dish_images": []
                }
            
            # Create a lookup dictionary for menu items
            menu_lookup = {}
            for item in menu_items:
                name = item.get("name")
                if name:
                    menu_lookup[name] = {
                        "ingredients": item.get("ingredients", ""),
                        "image_link": item.get("image_link")
                    }
            
            # Get dish names from last recommendations if available
            dish_names = []
            if self.agent.conversation_context.get("last_recommendations"):
                last_recommendations = self.agent.conversation_context.get("last_recommendations")
                self.logger.info("Extracting dish names from last recommendations")
                
                dish_pattern = r"(\d+)[\.:\)]\s+(.*?)\s*-\s*.*"
                dish_matches = list(re.finditer(dish_pattern, last_recommendations))
                # Extract dish names from matches
                for match in dish_matches[:num_dishes]:
                    dish_name = match.group(2).strip()
                    # New: clean up markdown "**Dish Name**" ➔ "Dish Name"
                    dish_name = re.sub(r"\*\*(.*?)\*\*", r"\1", dish_name)
                    dish_name = dish_name.strip()
                    # Exclude irrelevant sections like ingredients, tips, total, etc.
                    if any(keyword in dish_name.lower() for keyword in ["ingredients", "recommended dishes", "recommendation", "cost breakdown", "total", "tip", "after tax", "after tips"]):
                        continue
                    dish_names.append(dish_name)
            
            if not dish_names:
                return {
                    "status": "error",
                    "message": "No dishes found to generate images",
                    "dish_images": []
                }
            
            # Prepare results and collect dishes that need image generation
            dish_images = []
            images_to_generate = []
            
            # First pass: use existing image_links and collect dishes that need generation
            for dish_name in dish_names:
                # Get dish info from menu lookup
                dish_info = menu_lookup.get(dish_name, {})
                
                # Check if image_link exists
                if dish_info.get("image_link"):
                    self.logger.info(f"Using existing image_link for {dish_name}")
                    dish_images.append({
                        "dish_name": dish_name,
                        "image": None,
                        "image_url": dish_info["image_link"]
                    })
                else:
                    # Get ingredients for description
                    description = dish_info.get("ingredients", "")
                    if not description:
                        description = f"A dish from {self.agent.conversation_context.get('current_restaurant', 'restaurant')}"
                    
                    # Add to generation list
                    images_to_generate.append((dish_name, description))
            
            # If we have images to generate, do it in parallel
            if images_to_generate:
                self.logger.info(f"Generating {len(images_to_generate)} images in parallel")
                
                # Use ThreadPoolExecutor for parallel processing
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(images_to_generate))) as executor:
                    # Submit jobs directly using generate_image_with_llm
                    future_to_dish = {}
                    for dish_name, description in images_to_generate:
                        # Create a future for each dish
                        future = executor.submit(self.generate_image_with_llm, dish_name, description)
                        future_to_dish[future] = dish_name
                    
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_dish):
                        dish_name = future_to_dish[future]
                        try:
                            img, img_url = future.result()
                            if img:
                                dish_images.append({
                                    "dish_name": dish_name,
                                    "image": img,
                                    "image_url": img_url
                                })
                        except Exception as e:
                            self.logger.error(f"Error generating image for {dish_name}: {str(e)}")
            
            return {
                "status": "success",
                "message": f"Generated {len(dish_images)} dish images",
                "dish_images": dish_images
            }
                
        except Exception as e:
            self.logger.error(f"Error generating dish images: {str(e)}")
            return {
                "status": "error",
                "message": "Could not generate dish images at this time.",
                "dish_images": []
            }
            
    def close(self):
        """Close all resources"""
        self.logger.info("Restaurant recommendations tool closed") 