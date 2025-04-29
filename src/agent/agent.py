import autogen
from typing import Dict, List, Optional
import os
import re
from dotenv import load_dotenv
import logging
from datetime import datetime
import json
import sys
import src.agent.agent
sys.stdout.reconfigure(encoding='utf-8')

from .tools.locate_restaurant import LocateRestaurantTool
from .tools.restaurant_menu import RestaurantMenuTool
from .tools.restaurant_recommendations import RestaurantRecommendationsTool
from .tools.find_menu_on_doordash import FindMenuOnDeliverySiteTool

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

class RestaurantAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.setup_logging()
        self.setup_llm()
        self.conversation_context = {
            "current_restaurant": None,
            "current_location": None,
            "previous_actions": [],
            "health_data": None,
            "budget": None,
            "food_preference": None,
            "chat_history": [],
            "current_round": 0
        }


        self.location_search_tool = LocateRestaurantTool()
        self.menu_tool = RestaurantMenuTool()
        self.delivery_menu_tool = FindMenuOnDeliverySiteTool()
        self.recommendations_tool = RestaurantRecommendationsTool(agent=self)

        self.action_registry = {}
        self._register_default_actions()

    def update_meal_time(self, meal_time: str):
        self.conversation_context["meal_time"] = meal_time

    def _register_default_actions(self):
        self.register_action(
            name="search_restaurant",
            description="Search for a restaurant location",
            handler=self._handle_search_restaurant
        )
        self.register_action(
            name="get_menu",
            description="Get restaurant menu",
            handler=self._handle_get_menu
        )
        self.register_action(
            name="get_recommendations",
            description="Get personalized dish recommendations",
            handler=self._handle_recommendations
        )
        self.register_action(
            name="find_menu_on_doordash",
            description="Find DoorDash menu link using Google Search",
            handler=lambda: self.delivery_menu_tool.find_doordash_menu(
                self.conversation_context.get("current_restaurant", ""),
                self.conversation_context.get("current_location", "")
            )
        )
        self.register_action(
            name="general_conversation",
            description="Handle general conversation and questions about restaurants, food, or previous context",
            handler=self._handle_general_conversation
        )
        self.register_action(
            name="health_query",
            description="Answer health-related questions about food or dietary advice",
            handler=self._handle_health_query
        )

    def register_action(self, name: str, description: str, handler: callable):
        self.action_registry[name] = {
            "description": description,
            "handler": handler
        }

    def get_available_actions(self) -> List[str]:
        return list(self.action_registry.keys())

    def _handle_search_restaurant(self):
        restaurant_name = self.conversation_context.get("current_restaurant", "")
        zip_code = self.conversation_context.get("current_location", "")
        result = self.location_search_tool.search_restaurant(restaurant_name, zip_code)

        if result["status"] == "user_select":
            self.logger.info("Multiple results — prompting user selection.")
            return {
                "status": "user_select",  # 🛠️ ensure status is consistent
                "message": "Multiple restaurants found. Please choose one.",
                "restaurants": result["restaurants"],
                "screenshot_path": result.get("screenshot_path", "")
            }

        if result["status"] == "success":
            self.logger.info("Single result found. Proceeding even if no URL.")

            # Save name and URL (if any)
            if "url" in result and result["url"]:
                self.conversation_context["restaurant_url"] = result["url"]
            else:
                self.logger.warning("No URL found — will rely on fallback during menu extraction.")

            return {
                "status": "success",
                "message": result.get("message", "Restaurant selected"),
                "url": result.get("url", "")
            }
        # fallback — even if search failed, let downstream try DoorDash or prompt upload
        self.logger.warning(f"search_restaurant failed with result: {result} — fallback to menu fetch anyway")
        return {
            "status": "success",
            "message": f"Restaurant not found in Google, but fallback will try menu fetch.\nOriginal error: {result.get('message', '')}",
            "url": ""
        }

    def confirm_selected_restaurant(self, restaurant_info: Dict) -> Dict:
        """
        Called when user selects one specific restaurant from multiple.
        `restaurant_info` should contain 'name' and 'url' fields.
        """
        self.logger.info(f"User selected restaurant: {restaurant_info}")
        self.conversation_context["current_restaurant"] = restaurant_info.get("name", "")
        self.conversation_context["restaurant_url"] = restaurant_info.get("url", "")
        return self._handle_get_menu()  # proceed to fetch menu + recommend

    def _handle_get_menu(self) -> Dict:
        try:
            restaurant = self.conversation_context.get("current_restaurant", "")
            website = self.conversation_context.get("restaurant_url", "")
            zipcode = self.conversation_context.get("current_location", "00000")
            self.logger.info(f"Trying to fetch menu from website: {website}")

            result = self.menu_tool.get_menu(
                restaurant,
                restaurant_url=website,
                zipcode=zipcode
            )

            if result.get("status") == "success" and result.get("menu_items"):
                self.conversation_context["menu_items"] = result["menu_items"]
                self.logger.info(f"Stored {len(result['menu_items'])} items into context")
                if self.conversation_context["current_location"] and not self.conversation_context.get("meal_time"):
                    return {
                        "status": "user_select_meal_time",
                        "options": ["Breakfast", "Lunch", "Dinner"],
                        "message": "Please select a meal time."
                    }    
                # No longer automatically chain to recommendations
                menu_items_count = len(result["menu_items"])
                success_message = f"I found the menu for {restaurant} with {menu_items_count} items. Would you like me to recommend some dishes based on your preferences?"
                
                return {
                    "status": "success",
                    "message": success_message,
                    "menu_items": result["menu_items"]
                }

            self.logger.info("Website scrape failed or incomplete — trying DoorDash...")
            dd_result = self.delivery_menu_tool.find_doordash_menu(restaurant, zipcode)

            if isinstance(dd_result, dict) and dd_result.get("status") == "success":
                self.conversation_context["restaurant_url"] = dd_result.get("url")
                fallback_result = self.menu_tool.get_menu(
                    restaurant,
                    restaurant_url=dd_result.get("url"),
                    zipcode=zipcode
                )
                if fallback_result.get("status") == "success" and fallback_result.get("menu_items"):
                    self.conversation_context["menu_items"] = fallback_result["menu_items"]
                    self.logger.info(f"[DOORDASH] Stored {len(fallback_result['menu_items'])} items into context")
                    
                    # No longer automatically chain to recommendations
                    menu_items_count = len(fallback_result["menu_items"])
                    success_message = f"I found the menu for {restaurant} on DoorDash with {menu_items_count} items. Would you like me to recommend some dishes based on your preferences?"
                    
                    return {
                        "status": "success",
                        "message": success_message,
                        "menu_items": fallback_result["menu_items"]
                    }

            return {
                "status": "request_upload",
                "message": "Couldn't find the menu online. Please upload it manually.",
                "menu_items": []
            }

        except Exception as e:
            self.logger.error(f"Error in _handle_get_menu: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error retrieving menu: {str(e)}",
                "menu_items": []
            }

    def _handle_recommendations(self) -> Dict:
        try:
            menu_items = self.conversation_context.get("menu_items", [])
            self.logger.info(f"Ready to recommend from {len(menu_items)} items")
            if not menu_items:
                restaurant = self.conversation_context.get("current_restaurant")
                zipcode = self.conversation_context.get("current_location")

                if not restaurant or not zipcode:
                    return {"status": "error", "message": "No restaurant or location info available. Please select a restaurant first.", "menu_items": []}
                self.logger.info(f"No menu items found, calling _handle_get_menu for {restaurant}")
                menu_result = self._handle_get_menu()   
                if menu_result.get("status") == "success" and menu_result.get("menu_items"):
                    self.conversation_context["menu_items"] = menu_result["menu_items"]
                    menu_items = menu_result["menu_items"]
                    self.logger.info(f"Successfully got menu with {len(menu_items)} items")
                else:
                    self.logger.warning(f"Menu fetch failed with status: {menu_result.get('status')}")
                    menu_items = []

            health_data = self.conversation_context.get("health_data", {})
            budget = self.conversation_context.get("budget")
            food_preference = self.conversation_context.get("food_preference")
            generate_images = self.conversation_context.get("generate_images", False) # Check if image generation is requested
            
            # Only execute if the user has requested dish images
            if generate_images:
                self.logger.info("Generate images flag is True, generating dish images instead of recommendations")
                # Call the dedicated image generation method
                image_result = self.recommendations_tool.generate_dish_images(menu_items)
                # Reset the flag to avoid auto-generating images next time
                self.conversation_context["generate_images"] = False
                return {
                    "status": image_result["status"],
                    "message": image_result["message"],
                    "menu_items": [],
                    "dish_images": image_result.get("dish_images", [])
                }
            
            # Normal recommendation process, execute if no image generation requested
            self.logger.info(f"Using budget for recommendations: {budget}")
            self.logger.info(f"Using food preference for recommendations: {food_preference}")
            
            recommendations = self.recommendations_tool.get_recommendations(
                menu_items, 
                health_data, 
                budget,
                food_preference,
                debug_prompt=True
            )
            if recommendations.get("status") == "success" and recommendations.get("message"):
                self.conversation_context["last_recommendations"] = recommendations["message"]

            return {
                "status": recommendations["status"],
                "message": recommendations["message"],
                "menu_items": recommendations.get("menu_items", []),
                "dish_images": []  # Ensure empty list since regular recommendations don't generate images
            }
            
        except Exception as e:
            self.logger.error(f"Error handling recommendations: {str(e)}")
            return {"status": "error", "message": f"Error handling recommendations: {str(e)}", "menu_items": [], "dish_images": []}
    
    def _handle_general_conversation(self) -> Dict:
        """Handle general conversation and questions that don't fit other actions"""
        try:
            # Get the last user message
            current_history = self.get_current_round_history()
            if not current_history:
                return {"status": "error", "message": "No conversation history available", "menu_items": []}
                
            user_messages = [msg for msg in current_history if msg["role"] == "user"]
            if not user_messages:
                return {"status": "error", "message": "No user messages found", "menu_items": []}
                
            last_user_message = user_messages[-1]["content"]
            
            # Get relevant context from the restaurant and conversation
            restaurant = self.conversation_context.get("current_restaurant", "")
            food_preference = self.conversation_context.get("food_preference", "")
            menu_items = self.conversation_context.get("menu_items", [])
            menu_available = len(menu_items) > 0
            budget = self.conversation_context.get("budget")
            
            # Generate a contextual response
            prompt = f"""
            You are a helpful restaurant assistant. Please respond to the following user message.
            
            Current restaurant: {restaurant if restaurant else "Not selected yet"}
            Food preferences: {food_preference if food_preference else "Not specified"}
            Menu available: {"Yes with " + str(len(menu_items)) + " items" if menu_available else "No"}
            Budget: ${budget if budget else "Not specified"}
            
            User message: "{last_user_message}"
            
            Provide a helpful, conversational response that directly addresses the user's request or question.
            If they're asking about the restaurant or menu, be informative.
            If they're making small talk, respond naturally.
            If they're asking about dishes, discuss relevant options but don't make a full recommendation list.
            If they're asking about pricing or budget, be helpful and informative about costs.
            Keep your response friendly and concise.
            """
            
            response = self.ask_llm(prompt)
            
            return {
                "status": "success",
                "message": response,
                "menu_items": []
            }
            
        except Exception as e:
            self.logger.error(f"Error handling general conversation: {str(e)}")
            return {"status": "error", "message": f"I'm sorry, I do not understand that. Would you mind asking in a different way?", "menu_items": []}
    
    def _handle_health_query(self) -> Dict:
        """Handle health-related questions about food or dietary advice"""
        try:
            # Get the last user message
            current_history = self.get_current_round_history()
            last_user_message = [msg["content"] for msg in current_history if msg["role"] == "user"][-1]
            
            # Get health data context
            health_data = self.conversation_context.get("health_data", {})
            restaurant = self.conversation_context.get("current_restaurant", "")
            menu_items = self.conversation_context.get("menu_items", [])
            
            prompt = f"""
            You are a restaurant assistant providing health-conscious guidance. Answer the following health-related question.
            
            User's health profile: {json.dumps(health_data, indent=2)}
            Current restaurant: {restaurant if restaurant else "Not selected yet"}
            Menu available: {"Yes with " + str(len(menu_items)) + " items" if len(menu_items) > 0 else "No"}
            
            User question: "{last_user_message}"
            
            Provide a helpful response that considers their health profile and dietary needs.
            Be informative but emphasize you're not providing medical advice.
            If they ask about healthy options, suggest general approaches rather than specific nutritional prescriptions.
            Keep your response friendly and helpful.
            """
            
            response = self.ask_llm(prompt)
            
            return {
                "status": "success",
                "message": response,
                "menu_items": []
            }
            
        except Exception as e:
            self.logger.error(f"Error handling health query: {str(e)}")
            return {"status": "error", "message": "I'm sorry, but I could not provide any medical advice. Is there anything else I can help you with?", "menu_items": []}
            
    def extract_contextual_preferences(self, conversation_history: List[Dict]) -> str:
        """
        Extract implicit food preferences based on the current round's conversation history
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            str: Extracted food preferences as a comma-separated string
        """
        if not conversation_history:
            return ""
            
        # Combine all user messages in the current round
        combined_messages = " ".join([
            msg["content"] for msg in conversation_history 
            if msg["role"] == "user"
        ])
        
        if not combined_messages:
            return ""
            
        # Ask LLM to extract food preferences
        prompt = f"""
        Extract food preferences from the following conversation:
        
        "{combined_messages}"
        
        Return ONLY a comma-separated list of food preferences (ingredients, types of food, dietary preferences).
        If no preferences are found, return an empty string.
        Examples: "spicy, chicken, low-calorie" or "vegetarian, no onions, dairy-free"
        """
        
        try:
            preferences = self.ask_llm(prompt).strip()
            # Remove any quotes that might be in the response
            preferences = preferences.replace('"', '').replace("'", "")
            return preferences
        except Exception as e:
            self.logger.error(f"Error extracting contextual preferences: {str(e)}")
            return ""

    def extract_restaurant_info_llm(self, user_input: str) -> tuple[str, str]:
        prompt = f"""
        Your task is to extract structured information from user input.

        Input:
        "{user_input}"

        Return ONLY a JSON object in the following format:
        {{
            "restaurant": "RESTAURANT_NAME",
            "zipcode": "ZIPCODE"
        }}

        For restaurant, extract the specific restaurant name.
        For zipcode, extract a 5-digit US zip code if present.
        If the user mentions 'eat at' or 'go to' a restaurant, that's likely the restaurant name.
        If any value is missing, return an empty string for that field.
        """
        response = self.ask_llm(prompt)
        try:
            parsed = json.loads(response)
            restaurant = parsed.get("restaurant", "").strip()
            zipcode = parsed.get("zipcode", "").strip()
            return restaurant, zipcode
        except Exception as e:
            self.logger.warning(f"LLM parsing failed: {e}, fallback to regex")
            # Try to extract restaurant name
            restaurant_match = re.search(r"(?:eat|eating|at|go to|visit|find)\s+(?:at\s+)?([A-Za-z0-9\s'&]+?)(?:\s+in|\s+at|\s+near|\s+\d{5}|$)", user_input, re.IGNORECASE)
            restaurant = restaurant_match.group(1).strip() if restaurant_match else ""
            
            # Try to extract zip code
            zip_match = re.search(r'\b(\d{5})\b', user_input)
            zipcode = zip_match.group(1) if zip_match else ""
            
            self.logger.info(f"Regex extracted: restaurant='{restaurant}', zipcode='{zipcode}'")
            return restaurant, zipcode

    def start_new_conversation_round(self):
        """Start a new conversation round"""
        self.conversation_context["current_round"] += 1
        self.logger.info(f"Starting new conversation round: {self.conversation_context['current_round']}")

    def add_to_chat_history(self, role: str, content: str):
        """Add a message to the chat history"""
        self.conversation_context["chat_history"].append({
            "role": role,
            "content": content,
            "round": self.conversation_context["current_round"]
        })
        self.logger.info(f"Added {role} message to chat history (round {self.conversation_context['current_round']})")

    def get_current_round_history(self) -> List[Dict]:
        """Get chat history for the current round only"""
        current_round = self.conversation_context["current_round"]
        return [
            msg for msg in self.conversation_context["chat_history"] 
            if msg["round"] == current_round
        ]
        
    def analyze_user_input(self, user_input: str) -> str:
        """
        Analyze user input intention to determine the most appropriate action 
        
        Args:
            user_input: User message text
            
        Returns:
            str: Suggested action name
        """
        current_history = self.get_current_round_history()
        restaurant = self.conversation_context.get("current_restaurant")
        
        # Basic rule-based analysis first
        lower_input = user_input.lower()
        
        # Check for restaurant search intent
        if ("where" in lower_input or "find" in lower_input or "locate" in lower_input) and "restaurant" in lower_input:
            return "search_restaurant"
            
        # Check for menu request
        if "menu" in lower_input or "what do they have" in lower_input or "what do they offer" in lower_input:
            if restaurant:
                return "get_menu"
                
        # Check for recommendation request
        if "recommend" in lower_input or "suggestion" in lower_input or "what should i" in lower_input:
            if restaurant:
                return "get_recommendations"
                
        # Check for health-related queries
        if "health" in lower_input or "calories" in lower_input or "diet" in lower_input or "nutrition" in lower_input:
            return "health_query"
        
        # Budget questions now handled by general conversation
        
        # If no clear match from rules, ask LLM for classification
        action_prompt = f"""
        Classify the following user input into one of these categories:
        
        User input: "{user_input}"
        Current restaurant: {restaurant if restaurant else "None"}
        
        Categories:
        1. search_restaurant - User wants to find or learn about a restaurant
        2. get_menu - User wants to see a menu for a restaurant
        3. get_recommendations - User wants food recommendations 
        4. general_conversation - General chat, questions, or small talk
        5. health_query - Questions about health aspects of food
        
        Return ONLY the category name (e.g., "search_restaurant").
        """
        
        try:
            # Use a simpler LLM call to avoid recursion
            action_type = self.ask_llm(action_prompt).strip().lower()
            
            # Extract just the action name if there's extra text
            for action in self.action_registry:
                if action in action_type:
                    return action
                    
            # Default to general conversation if no match
            return "general_conversation"
            
        except Exception as e:
            self.logger.error(f"Error analyzing user input: {str(e)}")
            return "general_conversation"  # Default fallback

    def process_input(self, user_input: str) -> Dict:
        try:
            self.logger.info(f"Processing input: {user_input}")
            
            # Add user message to chat history
            self.add_to_chat_history("user", user_input)

            if user_input == "process_uploaded_menu":
                if not hasattr(self, 'uploaded_menu_data'):
                    return {"status": "error", "message": "No menu data uploaded", "menu_items": []}
                menu_result = self.menu_tool.get_menu(
                    self.conversation_context.get("current_restaurant", "Unknown Restaurant"),
                    uploaded_menu=self.uploaded_menu_data
                )
                if menu_result["status"] == "success":
                    self.conversation_context["menu_items"] = menu_result["menu_items"]
                return menu_result

            # Extract restaurant name and zip code
            restaurant_name, zip_code = self.extract_restaurant_info_llm(user_input)
            self.logger.info(f"LLM-extracted: restaurant='{restaurant_name}', zip='{zip_code}'")

            # Update context with restaurant and location if found
            if restaurant_name:
                prev_restaurant = self.conversation_context.get("current_restaurant", "")
                if prev_restaurant and prev_restaurant.lower() != restaurant_name.lower():
                    self.logger.info(f" Restaurant changed from '{prev_restaurant}' to '{restaurant_name}', clearing old menu and URL")
                    self.conversation_context["menu_items"] = []
                    self.conversation_context["restaurant_url"] = ""
                self.conversation_context["current_restaurant"] = restaurant_name.strip()
                self.logger.info(f"Updated conversation context with restaurant: '{self.conversation_context['current_restaurant']}'")

            if zip_code:
                self.conversation_context["current_location"] = zip_code
                self.logger.info(f"Updated conversation context with location: '{self.conversation_context['current_location']}'")

            # Debug log to verify context before search
            self.logger.info(f"Current context before action: restaurant='{self.conversation_context.get('current_restaurant')}', zip='{self.conversation_context.get('current_location')}'")

            # If both restaurant and zip are provided, perform a restaurant search but don't automatically chain to menu/recommendations
            if restaurant_name and zip_code:
                self.logger.info(f"Restaurant '{restaurant_name}' and location '{zip_code}' detected, searching first")
                search_result = self._handle_search_restaurant()
                
                if search_result.get("status") == "user_select":
                    # Return for user selection
                    self.add_to_chat_history("assistant", search_result.get("message", "Please select a restaurant."))
                    return search_result
                elif search_result.get("status") == "success":
                    # Success message confirming restaurant was found, but don't chain to menu/recommendations
                    self.logger.info("Search successful, waiting for user's next instruction")
                    confirmation_message = f"I found {restaurant_name}. Would you like to get dish recommendations for this restaurant?"
                    self.add_to_chat_history("assistant", confirmation_message)
                    return {
                        "status": "success",
                        "message": confirmation_message,
                        "url": search_result.get("url", "")
                    }
                else:
                    # Search failed
                    self.add_to_chat_history("assistant", search_result.get("message", "I couldn't find that restaurant."))
                    return search_result
            
            # For all other cases, use intent detection
            action = self.analyze_user_input(user_input)
            
            # Check if necessary requirements are met for this action
            if action == "get_menu" or action == "get_recommendations":
                if not self.conversation_context.get("current_restaurant"):
                    response = {
                        "status": "error",
                        "message": "I need to know which restaurant you're interested in first. Could you tell me the name?",
                        "menu_items": []
                    }
                    self.add_to_chat_history("assistant", response["message"])
                    return response
                    
            # If we're asking for menu or recommendations without location, ask for it
            if (action == "get_menu" or action == "get_recommendations") and not self.conversation_context.get("current_location"):
                response = {
                    "status": "error", 
                    "message": f"I need to know where {self.conversation_context.get('current_restaurant')} is located. Could you provide a zip code?",
                    "menu_items": []
                }
                self.add_to_chat_history("assistant", response["message"])
                return response
            
            # Handle the action
            if action == "search_restaurant":
                result = self._handle_search_restaurant()
            elif action == "get_menu":
                result = self._handle_get_menu()
            elif action == "get_recommendations":
                result = self._handle_recommendations()
            elif action == "health_query":
                result = self._handle_health_query()
            else:  # general_conversation
                result = self._handle_general_conversation()
            
            # Add result to chat history
            if result.get("status") != "user_select":  # Don't add user_select to chat history as we'll add it in UI
                self.add_to_chat_history("assistant", result.get("message", ""))
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}")
            error_response = {
                "status": "error",
                "message": f"I'm sorry, I encountered an error: {str(e)}",
                "menu_items": []
            }
            self.add_to_chat_history("assistant", error_response["message"])
            return error_response

    def handle_input(self, user_input: str, force_action: str = None) -> Dict:
        """Process user input with option to force a specific action"""
        try:
            self.logger.info(f"Handling input with forced action={force_action}: {user_input}")
            
            # If no forced action, use regular process_input
            if not force_action:
                return self.process_input(user_input)
                
            # Add user message to chat history if it's a real message
            if user_input != "process_uploaded_menu":
                self.add_to_chat_history("user", user_input)
            
            # Execute direct user selection action
            if force_action == "search_restaurant":
                result = self._handle_search_restaurant()
            elif force_action == "get_menu":
                result = self._handle_get_menu()
            elif force_action == "recommendations":
                if not self.conversation_context.get("current_restaurant"):
                    return {
                        "status": "error",
                        "message": "Please select a restaurant first before getting recommendations.",
                        "menu_items": []
                    }               
                if not self.conversation_context.get("current_location"):
                    return {
                        "status": "error",
                        "message": f"I need to know where {self.conversation_context.get('current_restaurant')} is located. Could you provide a zip code?",
                        "menu_items": []
                    }
                
                menu_items = self.conversation_context.get("menu_items", [])
                if not menu_items:
                    self.logger.info("No menu items available, attempting to fetch menu first")
                    menu_result = self._handle_get_menu()
                    
                    if menu_result.get("status") != "success" or not self.conversation_context.get("menu_items"):
                        return {
                            "status": "error",
                            "message": "I couldn't find the menu for this restaurant. Please try a different restaurant or upload a menu manually.",
                            "menu_items": []
                        }
                    
                    self.logger.info(f"Successfully fetched menu with {len(self.conversation_context.get('menu_items', []))} items")
                
                print("="*10)
                print("Everything before _handle_recommendations looks good!")
                result = self._handle_recommendations()
                if not self.conversation_context.get("generate_images", False):
                    if result.get("status") == "success" and result.get("message"):
                        self.conversation_context["last_recommendations"] = result["message"]

                # Add result to chat history for most response types
                if result.get("status") != "user_select":
                    self.add_to_chat_history("assistant", result.get("message", ""))

                return result
            elif force_action == "general_conversation":
                result = self._handle_general_conversation()
            elif force_action == "health_query":
                result = self._handle_health_query()
            else:
                self.logger.warning(f"Unknown forced action: {force_action}")
                result = {
                    "status": "error",
                    "message": f"Unknown action: {force_action}",
                    "menu_items": []
                }
            
            # Add result to chat history for most response types
            if result.get("status") != "user_select":
                self.add_to_chat_history("assistant", result.get("message", ""))
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error handling input with forced action: {str(e)}")
            error_response = {
                "status": "error",
                "message": f"I'm sorry, I encountered an error: {str(e)}",
                "menu_items": []
            }
            self.add_to_chat_history("assistant", error_response["message"])
            return error_response

    def setup_logging(self):
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'agent_{self.user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ])
        self.logger = logging.getLogger(self.__class__.__name__)

    def setup_llm(self):
        self.config_list = [{"model": "gpt-4o-mini", "api_key": os.getenv("OPENAI_API_KEY") }]
        self.assistant = autogen.AssistantAgent(name="assistant", llm_config={"config_list": self.config_list})
        self.user_proxy = autogen.UserProxyAgent(name="user_proxy", human_input_mode="NEVER", max_consecutive_auto_reply=10, code_execution_config={"work_dir": "workspace", "use_docker": False})

    def ask_llm(self, prompt: str) -> str:
        try:
            # Add conversation history from the current round as context
            current_round_history = self.get_current_round_history()
            context_prompt = ""
            
            if current_round_history:
                context_prompt = "\nConversation history for this round:\n"
                for msg in current_round_history:
                    role_display = "User" if msg["role"] == "user" else "Assistant"
                    context_prompt += f"{role_display}: {msg['content']}\n"
                    
                context_prompt += "\nNow respond to the current request:\n"
            
            # Prepend the context to the prompt
            enhanced_prompt = context_prompt + prompt if context_prompt else prompt
            
            chat_result = self.user_proxy.initiate_chat(self.assistant, message=enhanced_prompt, max_turns=1)
            for msg in reversed(chat_result.chat_history):
                content = msg.get('content', '').strip()
                if content:
                   return content.replace("TERMINATE", "").strip()
            return "No response from LLM"
        except Exception as e:
            self.logger.error(f"Error asking LLM: {str(e)}")
            return f"Error: {str(e)}"

    def close(self):
        self.location_search_tool.close()
        self.menu_tool.close()
        self.recommendations_tool.close()
        self.logger.info("Restaurant agent closed")

def main():
    agent = RestaurantAgent("user1")
    try:
        print("Step 1: User asks where to eat")
        result = agent.process_input("I want to eat Starbucks in 92037")
        print(result)
        print("\nStep 2: User asks for recommendations")
        result = agent.process_input("give me some recommendations")
        print(result)

    finally:
        agent.close()
    # try:
    #     result = agent.process_input("I want to eat Urban Plates in 92037")
    #     if result.get("status") == "user_select":
    #         print("🔔 Multiple locations found. Automatically selecting the first one for test...")
    #         first_option = result["restaurants"][0]
    #         selected_restaurant = {
    #             "name": first_option["title"],
    #             "url": first_option["url"]
    #         }
    #         confirm_result = agent.confirm_selected_restaurant(selected_restaurant)
    #         print("✅ Confirmed selection. Now fetching menu...")

    #         if confirm_result.get("status") == "success":
    #             print("✅ Menu fetched and stored. Proceeding to recommendations...")
    #             final = agent.process_input("give me some recommendations")
    #             print(final["message"])
    #             if "recommendations" in final:
    #                 print("\n🍽️ Recommendations:\n", final["recommendations"])

    # finally:
    #     agent.close()

if __name__ == "__main__":
    main()
