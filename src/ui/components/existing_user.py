"""
This file contains the existing user login workflow.
"""

import streamlit as st
import pandas as pd
from src.agent.agent import RestaurantAgent
from src.utils.data_utils import load_health_data

def existing_user_workflow():
    """Handle existing user login process"""
    user_id = st.text_input("Enter your user ID:")
    if user_id:
        health_data = load_health_data()
        if health_data is not None and str(user_id) in health_data['user_id'].astype(str).values:
            if st.button("Start", key="existing_user_start"):
                st.session_state.user_id = user_id
                st.session_state.agent = RestaurantAgent(user_id)

                # load user's health data and add to agent conversation_contex
                user_data = health_data[health_data['user_id'].astype(str) == str(user_id)]
                if not user_data.empty:
                    # convert DataFrame to dictionary to match the expected format
                    health_data_dict = user_data.iloc[0].to_dict()
                    # remove NaN values
                    health_data_dict = {k: v for k, v in health_data_dict.items() if pd.notna(v)}
                    # add to agent conversation_context
                    st.session_state.agent.conversation_context["health_data"] = health_data_dict

                st.rerun()
        else:
            st.error("User ID not found. Please check your ID or register as a new user.") 