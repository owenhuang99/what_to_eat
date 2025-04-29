import json
import os
import logging
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, ValidationError

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Schema definitions
class MenuItem(BaseModel):
    category: str
    name: str
    ingredients: str
    price: str
    image_url: Optional[str] = None
    reviews: List[str] = []  # optional, default to empty list

class NormalizedMenu(BaseModel):
    restaurant_name: str
    zipcode: str
    items: List[MenuItem]

# Load text file
def load_raw_menu(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# Normalize using OpenAI
def normalize_with_llm(raw_text: str, restaurant_name: str, zipcode: str, reviews: Optional[dict] = None) -> dict:
    snippet = raw_text.replace("```", "")[:4000]  # avoid triple backticks and truncate

    prompt = (
        f"I scraped the following messy menu text from DoorDash for restaurant '{restaurant_name}' "
        f"in zipcode '{zipcode}'. Please extract as many **distinct** menu items as you can from this text.\n\n"
        
        f"Return the menu items in the following JSON format. Group them under a reasonable `category`, and include these fields:\n"
        f"- `name`\n"
        f"- `price`\n"
        f"- `ingredients`\n"
        f"- `category`\n"
        f"- `meal_time` (if applicable, like 'Breakfast', 'Lunch', or 'Dinner')\n"
        f"- `image_url` (if available, otherwise leave as empty string)\n"
        f"- `reviews` (a few short user comments, or empty list if not available)\n\n"
        
        f"Example:\n"
        f"""{{
    "restaurant_name": "{restaurant_name}",
    "zipcode": "{zipcode}",
    "items": [
        {{
            "name": "Braised Beef & Mushrooms",
            "price": "$15.99",
            "meal_time": "Dinner",
            "category": "Mains",
            "ingredients": "Braised beef with mushrooms in garlic sauce",
            "image_url": "https://doordash.com/path/to/image.jpg",
            "reviews": ["The dish was amazing!", "Could use more mushrooms."]
        }},
        ...
    ]
}}\n\n"""
        f"Only include **unique** items, and ignore anything unrelated (like reviews or duplicated lines).\n\n"
        f"Raw menu text:\n{snippet}\n\n"
        f"Include a `reviews` field with a few short representative user comments for each dish, if available in the raw text. "
        f"If no reviews are present, leave it as an empty list [].\n\n"
        f"Return ONLY the JSON object — no explanation or extra text."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    try:
        content = response.choices[0].message.content
        return NormalizedMenu.model_validate_json(content).model_dump()
    except ValidationError as ve:
        logging.warning(f"Validation error: {ve}")
        return {}
    except Exception as e:
        logging.error(f"Parsing error: {e}")
        return {}


# Chunk text helper
def chunk_text(text, max_length=4000):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

# Main
if __name__ == "__main__":
    input_path = "src/data/menus/i_want_to_eat_chipotle_in_menu.txt"
    output_path = "src/data/menus/chipotle_92037_cleaned.json"

    raw = load_raw_menu(input_path)

    all_items = []
    for chunk in chunk_text(raw):
        parsed = normalize_with_llm(chunk, "Chipotle", "92037")
        if parsed and "items" in parsed:
            all_items.extend(parsed["items"])

    # Deduplicate items by name + price
    seen = set()
    unique_items = []
    for item in all_items:
        key = (item["name"].strip().lower(), item["price"])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    final_result = {
        "restaurant_name": "Chipotle",
        "zipcode": "92037",
        "items": unique_items
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, indent=2)

    print(f"Cleaned full menu saved to: {output_path}")
