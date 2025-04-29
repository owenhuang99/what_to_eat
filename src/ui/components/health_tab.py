"""
This file contains the health and preferences tab implementation.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from src.utils.data_utils import load_health_data, update_health_data
from src.ui.components.display_info import display_health_info

def health_tab():
    """Health & Preferences tab implementation"""
    # Page Title
    st.markdown("<h2 style='text-align: center;'>Health & Preferences</h2>", unsafe_allow_html=True)
    # Makes a line separator in app
    st.markdown("---")

    # Load health data at the beginning of the section
    health_data = load_health_data()
    user_data = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)]

    # Initialize session state for edit modes if they don't exist
    if 'edit_health_info' not in st.session_state:
        st.session_state.edit_health_info = False
    if 'edit_allergies' not in st.session_state:
        st.session_state.edit_allergies = False
    if 'edit_dietary_restriction' not in st.session_state:
        st.session_state.edit_dietary_restriction = False
    if 'edit_dietary_goal' not in st.session_state:
        st.session_state.edit_dietary_goal = False

    # Function to toggle edit mode
    def toggle_edit_mode():
        st.session_state.edit_health_info = not st.session_state.edit_health_info

    # Function to handle update submission
    def submit_health_update():
        try:
            # Create properly formatted health data dictionary from session state
            updated_health_data = {
                "age": st.session_state.health_age,
                "gender": st.session_state.health_gender.lower() if isinstance(st.session_state.health_gender, str) else st.session_state.health_gender,
                "ethnicity": st.session_state.health_ethnicity,
                "height": st.session_state.health_height,
                "weight": st.session_state.health_weight,
                "bmi": st.session_state.health_bmi,
                "blood_sugar": st.session_state.health_blood_sugar,
                "blood_pressure": st.session_state.health_blood_pressure,
                "cholesterol": st.session_state.health_cholesterol,
                "body_fat_pct": st.session_state.health_body_fat_pct,
                "diabetes": 1 if st.session_state.health_diabetes else 0,
                "hypertension": 1 if st.session_state.health_hypertension else 0,
                "heart_disease": 1 if st.session_state.health_heart_disease else 0
            }

            # Call the update method
            success, _ = update_health_data(st.session_state.user_id, updated_health_data, is_new_user=False)

            if success:
                st.session_state.edit_health_info = False
                # Clear the cache to ensure fresh data on next load
                load_health_data.clear()
                # Reload health data to update the display
                health_data = load_health_data()
                user_data = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)]
                st.success("Health information updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update health information. Please try again.")
        except Exception as e:
            st.error(f"Error updating health data: {str(e)}")

    # User Preferences Container
    st.write("User Preferences:")
    with st.expander("User Preferences Information", expanded=True):
        # Display current meal time
        if st.session_state.agent and "meal_time" in st.session_state.agent.conversation_context:
            st.write(f"**Meal Time:** {st.session_state.agent.conversation_context['meal_time']}")
        else:
            st.write("**Meal Time:** Not set")
        
        # Display current budget
        if st.session_state.budget:
            budget_min, budget_max = st.session_state.budget
            st.write(f"**Budget Range:** ${budget_min} - ${budget_max}")
        else:
            st.write("**Budget Range:** Not set")
        
        # Display current food preferences
        if st.session_state.food_preference:
            st.write(f"**Food Preferences:** {st.session_state.food_preference}")
        else:
            st.write("**Food Preferences:** Not set")
        
        # Button to edit preferences
        st.button("Edit Preferences", key="edit_preferences", on_click=lambda: (
            setattr(st.session_state, 'budget', None),
            setattr(st.session_state, 'food_preference', None),
            st.rerun()
        ))

    # Health Info Container
    st.write("Health Information:")
    with st.expander("User General Health Information", expanded=True):
        if not user_data.empty:
            display_health_info(user_data)
        else:
            st.warning("No health data found for this user")

        # Button to toggle edit mode
        if st.button("Edit Health Information", key="edit_health_button"):
            toggle_edit_mode()
            st.rerun()

        # Show edit form if in edit mode
        if st.session_state.edit_health_info:
            with st.form("health_edit_form"):
                st.markdown("<h3 style='text-align: center;'>Edit Health Information</h3>", unsafe_allow_html=True)
                st.markdown("---")

                # Pre-fill form with existing data if available
                if not user_data.empty:
                    user_row = user_data.iloc[0]

                    # Use the same 3-column layout as the display function
                    col1, col2, col3 = st.columns(3)

                    # Personal Information
                    with col1:
                        st.subheader("Personal Information")
                        st.session_state.health_age = st.number_input("Age", min_value=0, max_value=120,
                                                                    value=int(user_row['age']) if not pd.isna(user_row['age']) else 0)

                        st.session_state.health_gender = st.selectbox("Gender",
                                                                    options=["Male", "Female", "Other"],
                                                                    index=0 if user_row['gender'] == "Male" else
                                                                    1 if user_row['gender'] == "Female" else 2)

                        st.session_state.health_ethnicity = st.text_input("Ethnicity",
                                                                        value=str(user_row['ethnicity']) if not pd.isna(user_row['ethnicity']) else "")

                    # Body Metrics
                    with col2:
                        st.subheader("Body Metrics")
                        st.session_state.health_height = st.number_input("Height (cm)", min_value=0.0,
                                                                     max_value=300.0,
                                                                     value=float(user_row['height']) if not pd.isna(user_row['height']) else 0.0)

                        st.session_state.health_weight = st.number_input("Weight (kg)", min_value=0.0,
                                                                     max_value=500.0,
                                                                     value=float(user_row['weight']) if not pd.isna(user_row['weight']) else 0.0)

                        st.session_state.health_bmi = st.number_input("BMI", min_value=0.0, max_value=50.0,
                                                                  value=float(user_row['bmi']) if not pd.isna(user_row['bmi']) else 0.0)

                        st.session_state.health_body_fat_pct = st.number_input("Body Fat %", min_value=0.0,
                                                                           max_value=100.0,
                                                                           value=float(user_row['body_fat_pct']) if not pd.isna(user_row['body_fat_pct']) else 0.0)

                    # Health Conditions
                    with col3:
                        st.subheader("Health Conditions")
                        st.session_state.health_blood_sugar = st.number_input("Blood Sugar (mg/dL)", min_value=0.0,
                                                                          max_value=1000.0,
                                                                          value=float(user_row['blood_sugar']) if not pd.isna(user_row['blood_sugar']) else 0.0)

                        st.session_state.health_blood_pressure = st.number_input("Blood Pressure (mmHg)",
                                                                             min_value=0.0, max_value=300.0,
                                                                             value=float(user_row['blood_pressure']) if not pd.isna(user_row['blood_pressure']) else 0.0)

                        st.session_state.health_cholesterol = st.number_input("Cholesterol (mg/dL)", min_value=0.0,
                                                                          max_value=1000.0,
                                                                          value=float(user_row['cholesterol']) if not pd.isna(user_row['cholesterol']) else 0.0)

                        # Convert 0/1 to boolean for checkboxes
                        st.session_state.health_diabetes = st.checkbox("Diabetes",
                                                                   value=bool(user_row['diabetes']) if not pd.isna(user_row['diabetes']) else False)

                        st.session_state.health_hypertension = st.checkbox("Hypertension",
                                                                       value=bool(user_row['hypertension']) if not pd.isna(user_row['hypertension']) else False)

                        st.session_state.health_heart_disease = st.checkbox("Heart Disease",
                                                                        value=bool(user_row['heart_disease']) if not pd.isna(user_row['heart_disease']) else False)

                # Form submission buttons
                col1, col2 = st.columns(2)
                with col1:
                    st.form_submit_button("Update Health Information", on_click=submit_health_update)
                with col2:
                    st.form_submit_button("Cancel", on_click=toggle_edit_mode)

    # Dietary Information Container
    st.write("Dietary Information:")
    with st.expander("User Dietary Information", expanded=True):
        # Allergies Section
        st.subheader("Allergies")
        current_allergies = user_data['allergies'].iloc[0] if not user_data.empty and 'allergies' in user_data else "None specified"
        st.write(f"**Current Allergies:** {current_allergies}")
        
        if st.button("Edit Allergies", key="edit_allergies_button"):
            st.session_state.edit_allergies = True
            st.rerun()
        
        if st.session_state.edit_allergies:
            with st.form("allergies_form"):
                new_allergies = st.text_input("Enter your allergies (comma separated):", 
                                            value=current_allergies if current_allergies != "None specified" else "")
                submit_allergies = st.form_submit_button("Save Allergies")
                
                if submit_allergies:
                    # Update health data
                    health_data = load_health_data()
                    user_idx = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)].index
                    
                    if not user_idx.empty:
                        health_data.loc[user_idx, 'allergies'] = new_allergies
                        # Use the same path as data_utils.py
                        cwd = Path.cwd()
                        data_path = cwd / "src" / "data" / "health_data.csv"
                        data_path.parent.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
                        health_data.to_csv(data_path, index=False)
                        st.success("Allergies updated successfully!")
                        st.session_state.edit_allergies = False
                        # Clear the cache to ensure fresh data on next load
                        load_health_data.clear()
                        # Reload health data to update the display
                        health_data = load_health_data()
                        user_data = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)]
                        st.rerun()

        st.markdown("---")

        # Dietary Restrictions Section
        st.subheader("Dietary Restrictions")
        current_restrictions = user_data['dietary_restriction'].iloc[0] if not user_data.empty and 'dietary_restriction' in user_data else "None specified"
        st.write(f"**Current Dietary Restrictions:** {current_restrictions}")
        
        if st.button("Edit Dietary Restrictions", key="edit_dietary_restriction_button"):
            st.session_state.edit_dietary_restriction = True
            st.rerun()
        
        if st.session_state.edit_dietary_restriction:
            with st.form("dietary_restriction_form"):
                new_restrictions = st.text_input("Enter your dietary restrictions (comma separated):", 
                                              value=current_restrictions if current_restrictions != "None specified" else "")
                submit_restrictions = st.form_submit_button("Save Dietary Restrictions")
                
                if submit_restrictions:
                    # Update health data
                    health_data = load_health_data()
                    user_idx = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)].index
                    
                    if not user_idx.empty:
                        health_data.loc[user_idx, 'dietary_restriction'] = new_restrictions
                        # Use the same path as data_utils.py
                        cwd = Path.cwd()
                        data_path = cwd / "src" / "data" / "health_data.csv"
                        data_path.parent.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
                        health_data.to_csv(data_path, index=False)
                        st.success("Dietary restrictions updated successfully!")
                        st.session_state.edit_dietary_restriction = False
                        # Clear the cache to ensure fresh data on next load
                        load_health_data.clear()
                        # Reload health data to update the display
                        health_data = load_health_data()
                        user_data = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)]
                        st.rerun()

        st.markdown("---")

        # Dietary Goals Section
        st.subheader("Dietary Goals")
        current_goals = user_data['dietary_goal'].iloc[0] if not user_data.empty and 'dietary_goal' in user_data else "None specified"
        st.write(f"**Current Dietary Goals:** {current_goals}")
        
        if st.button("Edit Dietary Goals", key="edit_dietary_goal_button"):
            st.session_state.edit_dietary_goal = True
            st.rerun()
        
        if st.session_state.edit_dietary_goal:
            with st.form("dietary_goal_form"):
                new_goals = st.text_input("Enter your dietary goals (comma separated):", 
                                       value=current_goals if current_goals != "None specified" else "")
                submit_goals = st.form_submit_button("Save Dietary Goals")
                
                if submit_goals:
                    # Update health data
                    health_data = load_health_data()
                    user_idx = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)].index
                    
                    if not user_idx.empty:
                        health_data.loc[user_idx, 'dietary_goal'] = new_goals
                        # Use the same path as data_utils.py
                        cwd = Path.cwd()
                        data_path = cwd / "src" / "data" / "health_data.csv"
                        data_path.parent.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
                        health_data.to_csv(data_path, index=False)
                        st.success("Dietary goals updated successfully!")
                        st.session_state.edit_dietary_goal = False
                        # Clear the cache to ensure fresh data on next load
                        load_health_data.clear()
                        # Reload health data to update the display
                        health_data = load_health_data()
                        user_data = health_data[health_data['user_id'].astype(str) == str(st.session_state.user_id)]
                        st.rerun() 