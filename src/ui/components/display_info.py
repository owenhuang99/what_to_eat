"""
This file displays the health information in main page "Health & Preference" tab.
"""

import streamlit as st

def display_health_info(user_data):
    """Display health information in a consistent format with columns defined at the top"""
    # Define the columns at the top
    col1, col2, col3 = st.columns(3)

    # Personal Information
    with col1:
        st.subheader("Personal Information")
        st.write(f"**Age**: {user_data['age'].iloc[0]}")
        st.write(f"**Gender**: {user_data['gender'].iloc[0]}")
        st.write(f"**Ethnicity**: {user_data['ethnicity'].iloc[0] if 'ethnicity' in user_data else 'Not provided'}")

    # Body Metrics
    with col2:
        st.subheader("Body Metrics")
        st.write(f"**Height**: {user_data['height'].iloc[0] if 'height' in user_data else 'Not provided'} cm")
        st.write(f"**Weight**: {user_data['weight'].iloc[0] if 'weight' in user_data else 'Not provided'} kg")
        st.write(f"**BMI**: {user_data['bmi'].iloc[0] if 'bmi' in user_data else 'Not provided'}")
        st.write(f"**Body Fat Percentage**: {user_data['body_fat_pct'].iloc[0] if 'body_fat_pct' in user_data else 'Not provided'}%")

    # Health Conditions
    with col3:
        st.subheader("Health Conditions")
        st.write(f"**Blood Sugar**: {user_data['blood_sugar'].iloc[0] if 'blood_sugar' in user_data else 'Not provided'}")
        st.write(f"**Blood Pressure**: {user_data['blood_pressure'].iloc[0] if 'blood_pressure' in user_data else 'Not provided'}")
        st.write(f"**Cholesterol**: {user_data['cholesterol'].iloc[0] if 'cholesterol' in user_data else 'Not provided'}")
        st.write(f"**Diabetes**: {'Yes' if user_data['diabetes'].iloc[0] == 1 else 'No'}" if 'diabetes' in user_data else 'Not provided')
        st.write(f"**Hypertension**: {'Yes' if user_data['hypertension'].iloc[0] == 1 else 'No'}" if 'hypertension' in user_data else 'Not provided')
        st.write(f"**Heart Disease**: {'Yes' if user_data['heart_disease'].iloc[0] == 1 else 'No'}" if 'heart_disease' in user_data else 'Not provided') 