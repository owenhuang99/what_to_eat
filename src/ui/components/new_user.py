"""
This file contains the new user registration workflow.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from src.utils.data_utils import process_health_data, update_health_data
from src.agent.agent import RestaurantAgent
from src.utils.constants import HEALTH_REPORT_FORMAT, HEALTH_REPORT_TIPS

def new_user_workflow():
    """Handle new user registration process"""
    st.subheader("New User Registration")

    # Add tabs for different input methods
    tab1, tab2 = st.tabs(["Upload File", "Fill Form"])

    with tab1:
        st.write("Please upload your health report in the following format:")
        st.code(HEALTH_REPORT_FORMAT)
        st.info(HEALTH_REPORT_TIPS)

        uploaded_file = st.file_uploader("Upload your health report (txt file)", type=['txt'])

        if uploaded_file:
            st.success("File uploaded successfully")
            st.write("If you want to process this file, click 'Process File' below.")

            if st.button("Process File", key="process_health_file"):
                content = uploaded_file.getvalue().decode()
                health_info = process_health_data(content)
                if health_info:
                    st.success("Health data processed successfully!")
                    
                    # update health data
                    success, new_user_id = update_health_data(None, health_info, is_new_user=True)
                    if success:
                        st.success(f"Registration successful! Your user ID is: {new_user_id}")
                        st.info("Please save this ID for future reference")
                        st.session_state.user_id = new_user_id
                        st.session_state.is_new_user = False
                        # initialize agent
                        st.session_state.agent = RestaurantAgent(new_user_id)
                        # add processed health data to agent conversation_context
                        st.session_state.agent.conversation_context["health_data"] = health_info
                        st.rerun()

    with tab2:
        # Manual entry form
        with st.form("health_data_form"):
            col1, col2 = st.columns(2)

            with col1:
                age = st.number_input("Age", min_value=0, max_value=120, help="Enter your age in years")
                gender = st.selectbox("Gender", options=["Male", "Female", "Other"])
                ethnicity = st.text_input("Ethnicity")
                height = st.number_input("Height (cm)", min_value=0.0, max_value=300.0,
                                     help="Enter your height in centimeters")
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0,
                                     help="Enter your weight in kilograms")
                bmi = st.number_input("BMI", min_value=0.0, max_value=100.0, help="Enter your BMI (Body Mass Index)")

            with col2:
                blood_sugar = st.number_input("Blood Sugar Level", min_value=0.0, help="Enter your blood sugar level")
                blood_pressure = st.text_input("Blood Pressure", help="Enter your blood pressure (systolic)")
                cholesterol = st.number_input("Cholesterol Level", min_value=0.0, help="Enter your cholesterol level")
                body_fat = st.number_input("Body Fat Percentage", min_value=0.0, max_value=100.0,
                                       help="Enter your body fat percentage")

            st.write("### Medical Conditions")
            col3, col4, col5 = st.columns(3)

            with col3:
                diabetes = st.radio("Diabetes", options=["No", "Yes"], horizontal=True)
            with col4:
                hypertension = st.radio("Hypertension", options=["No", "Yes"], horizontal=True)
            with col5:
                heart_disease = st.radio("Heart Disease", options=["No", "Yes"], horizontal=True)

            submit_button = st.form_submit_button("Submit Health Data")

            if submit_button:
                # Convert form data to the expected format
                health_info = {
                    "age": age,
                    "gender": gender.lower(),
                    "ethnicity": ethnicity,
                    "height": height,
                    "weight": weight,
                    "bmi": bmi,
                    "blood_sugar": blood_sugar,
                    "blood_pressure": blood_pressure,
                    "cholesterol": cholesterol,
                    "body_fat_pct": body_fat,
                    "diabetes": 1 if diabetes == "Yes" else 0,
                    "hypertension": 1 if hypertension == "Yes" else 0,
                    "heart_disease": 1 if heart_disease == "Yes" else 0
                }

                success, new_user_id = update_health_data(None, health_info, is_new_user=True)

                if success:
                    st.success(f"Registration successful! Your user ID is: {new_user_id}")
                    st.info("Please save this ID for future reference")
                    st.session_state.user_id = new_user_id
                    st.session_state.is_new_user = False
                    # initialize agent
                    st.session_state.agent = RestaurantAgent(new_user_id)
                    # add processed health data to agent conversation_context
                    st.session_state.agent.conversation_context["health_data"] = health_info
                    st.rerun() 