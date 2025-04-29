"""
This file contains initialization functions for the application.
"""

import streamlit as st
import pandas as pd
from src.agent.agent import RestaurantAgent

def initialize_agent():
    """Initialize the RestaurantAgent if it doesn't exist"""
    if 'agent' not in st.session_state or st.session_state.agent is None:
        # Check if user_id is available
        if 'user_id' in st.session_state and st.session_state.user_id is not None:
            st.session_state.agent = RestaurantAgent(st.session_state.user_id)
        else:
            st.warning("Cannot initialize agent: user ID is not available")
            return False
    return True

def initialize_session_state():
    """Initialize session state variables"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'menu_data' not in st.session_state:
        st.session_state.menu_data = None
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'is_new_user' not in st.session_state:
        st.session_state.is_new_user = None
    if 'zipcode' not in st.session_state:
        st.session_state.zipcode = None
    if 'restaurant' not in st.session_state:
        st.session_state.restaurant = None
    if 'menu_upload' not in st.session_state:
        st.session_state.menu_upload = None
    if 'meal_type' not in st.session_state:
        st.session_state.meal_type = None
    if 'budget_range' not in st.session_state:
        st.session_state.budget_range = None
    if 'budget_min' not in st.session_state:
        st.session_state.budget_min = None
    if 'budget_max' not in st.session_state:
        st.session_state.budget_max = None
    if 'meal_pref' not in st.session_state:
        st.session_state.meal_pref = None
    if 'meal_pref_options' not in st.session_state:
        st.session_state.meal_pref_options = None
    if "meal_feedback" not in st.session_state or st.session_state["meal_feedback"] is None:
        st.session_state["meal_feedback"] = {}
    if 'budget' not in st.session_state:
        st.session_state.budget = None
    if 'food_preference' not in st.session_state:
        st.session_state.food_preference = None
    if 'edit_health_info' not in st.session_state:
        st.session_state.edit_health_info = False
    if 'registration_step' not in st.session_state:
        st.session_state.registration_step = 1
    if 'temp_health_info' not in st.session_state:
        st.session_state.temp_health_info = None
    if 'awaiting_meal_time_choice' not in st.session_state:
        st.session_state.awaiting_meal_time_choice = False
    if 'awaiting_location_choice' not in st.session_state:
        st.session_state.awaiting_location_choice = False
    if 'location_message' not in st.session_state:
        st.session_state.location_message = ""
    if 'restaurant_options' not in st.session_state:
        st.session_state.restaurant_options = []
    if 'recommendation_result' not in st.session_state:
        st.session_state.recommendation_result = None
    if 'recommendation_index' not in st.session_state:
        st.session_state.recommendation_index = 0
    if 'skipped_count' not in st.session_state:
        st.session_state.skipped_count = 0
    if 'show_navigation_buttons' not in st.session_state:
        st.session_state.show_navigation_buttons = False 