"""Constants used throughout the application."""

HEALTH_REPORT_FORMAT = """# Personal Information
age: 35
gender: female
ethnicity: Asian
height: 165
weight: 58
bmi: 21.3

# Health Measurements
blood sugar: 95
blood pressure: 120
cholesterol: 180
body fat: 22

# Medical History (use 0 for No, 1 for Yes)
diabetes: 0
hypertension: 0
heart disease: 0

# Dietary Information (optional)
dietary restriction: vegetarian, no nuts
dietary goal: weight loss, low carb
"""

HEALTH_REPORT_TIPS = """💡 Tips: 
- Height should be in centimeters (cm)
- Weight should be in kilograms (kg)
- Blood sugar should be in mg/dL
- Blood pressure is systolic
- Cholesterol should be in mg/dL
- Body fat should be in percentage (%)
- For dietary restrictions and goals, use commas to separate multiple values
""" 


CHAT_INTERFACE_CSS = """<style>
    .user-bubble {
        background-color: #007bff;
        color: white;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        max-width: 80%;
        margin-left: auto;
        text-align: right;
    }
    .bot-bubble {
        background-color: #e9ecef;
        color: black;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        max-width: 80%;
        margin-right: auto;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
    }
    .stButton>button {
        width: 100%;
    }
    .menu-panel {
        max-height: 300px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 5px;
        margin: 10px 0;
    }
    .menu-item {
        padding: 5px 0;
        border-bottom: 1px solid #eee;
    }
    .menu-item:last-child {
        border-bottom: none;
    }
    .menu-name {
        font-weight: bold;
    }
    .menu-price {
        color: #007bff;
        float: right;
    }
    .user-message {
        background-color: #383838;
        color: #ffffff;
        padding: 10px 15px;
        border-radius: 12px;
        margin-left: auto;
        margin-right: 10px;
        max-width: 80%;
        float: right;
        clear: both;
        margin-bottom: 10px;
    }
    .assistant-message {
        background-color: #2a2a2a;
        color: #ffffff;
        padding: 10px 15px;
        border-radius: 12px;
        margin-right: auto;
        margin-left: 10px;
        max-width: 80%;
        float: left;
        clear: both;
        margin-bottom: 10px;
    }
    .message-sender {
        font-weight: bold;
        margin-bottom: 5px;
        font-size: 0.85em;
        color: #ccc;
    }
    .message-content {
        font-size: 1em;
        line-height: 1.4;
        overflow-wrap: break-word;
    }
    .chat-history:after {
        content: "";
        display: table;
        clear: both;
    }
    </style>
"""

CHAT_HELP_TEXT = """### How to Use This Assistant

1. **Search a Restaurant**: Type a message like "I want to eat at Joy Yee Noodle in 60201" or "I want to eat at Chipotle in 90210", which explicitly includes the restaurant name and the zipcode. 
2. **Restaurant Selection**: If there are multiple restaurants with the same name in the same zipcode, you can select the right restaurant from the drop-down menu.
3. **Get Recommendations**: Once a restaurant is found and selected, you can press the "Get Dish Recommendations" button. The agent will fetch the restaurant menu, and generate recommended dishes based on your personal preference, budget and health status. The dish price, ingredients, reviews, recommendation reasoning and final cost breakdown will also be provided.
4. **Generate Dish images**: After getting the recommendations, you can press the "Generate Dish images" button. The agent will use LLM to generate an authentic picture of the recommended dishes.
5. **Get Health Advice**: You can also press the "Get Health Advice" at any time, and the agent will generate some personalized health advice based on your health status.
6. **Chit-Chat**: You can also send messages like "Hi" or other random messages you want to chit-chat with the agent.

Have a nice play with your personal restaurant recommendation helper!
"""