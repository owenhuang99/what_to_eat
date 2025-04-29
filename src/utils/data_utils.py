import pandas as pd
import streamlit as st
from pathlib import Path


# Health data functions
@st.cache_data
def load_health_data():
    """Load health data from CSV"""
    try:
        # Get the current working directory (should be agent/)
        cwd = Path.cwd()
        # Calculate the data file path relative to cwd
        data_path = cwd / "src" / "data" / "health_data.csv"
        
        # if file doesn't exist, create it
        if not data_path.exists(): 
            # Create an empty DataFrame with the required columns
            empty_df = pd.DataFrame(columns=[
                'user_id', 'age', 'gender', 'ethnicity', 'height', 'weight', 
                'bmi', 'blood_sugar', 'blood_pressure', 'cholesterol', 
                'body_fat_pct', 'diabetes', 'hypertension', 'heart_disease',
                'dietary_restriction', 'dietary_goal'
            ])
            empty_df.to_csv(data_path, index=False)
            return empty_df
            
        # Read the existing file
        df = pd.read_csv(data_path)    
        return df
    except Exception as e:
        st.error(f"Error loading health data: {str(e)}")
        return None

def generate_new_user_id(health_data):
    """Generate a new user ID based on the maximum existing ID"""
    if health_data is None or health_data.empty:
        return "1"
    try:
        max_id = health_data['user_id'].astype(int).max()
        return str(max_id + 1)
    except:
        # If conversion fails, try string comparison
        max_id = max(health_data['user_id'].astype(str).astype(int))
        return str(max_id + 1)


def process_health_data(file_content):
    """
    Process the uploaded health report and extract relevant information

    Args:
        file_content (str): Content of the uploaded health report file
        - Ideal Format:
            - One health indicator per line
            - Use colon (:) to separate key and value
            - Binary values (0/1) are used for disease markers, where 0 is no and 1 is yes

    Returns:
        dict: Extracted health information stored in a dictionary
        None: If critical errors occur or required fields are missing
    """

    
    try:
        if not file_content or not file_content.strip():
            st.error("Empty health report provided")
            return None

        lines = [line.strip() for line in file_content.split('\n') if line.strip()]
        if not lines:
            st.error("No valid data found in health report")
            return None

        health_info = {}
        required_fields = {'age', 'gender'}  # Only age and gender are required

        # Define field mappings with their types and validation rules
        field_config = {
            'age': {
                'key': 'age:',
                'type': int,
                'required': True,
                'validation': lambda x: 0 <= x <= 120,
                'error_msg': "Age must be between 0 and 120"
            },
            'gender': {
                'key': 'gender:',
                'type': str,
                'required': True,
                'validation': lambda x: x.lower() in ['male', 'female', 'other'],
                'error_msg': "Gender must be Male, Female, or Other"
            },
            'ethnicity': {
                'key': 'ethnicity:',
                'type': str,
                'required': False,
                'validation': lambda x: bool(x.strip()),
                'error_msg': "Ethnicity cannot be empty"
            },
            'height': {
                'key': 'height:',
                'type': float,
                'required': False,
                'validation': lambda x: 0 < x <= 300,
                'error_msg': "Height must be between 0 and 300 cm"
            },
            'weight': {
                'key': 'weight:',
                'type': float,
                'required': False,
                'validation': lambda x: 0 < x <= 500,
                'error_msg': "Weight must be between 0 and 500 kg"
            },
            'bmi': {
                'key': 'bmi:',
                'type': float,
                'required': False,
                'validation': lambda x: 10 <= x <= 50,
                'error_msg': "BMI must be between 10 and 50"
            },
            'blood_sugar': {
                'key': 'blood sugar:',
                'type': float,
                'required': False,
                'validation': lambda x: 0 <= x <= 1000,
                'error_msg': "Blood sugar must be between 0 and 1000 mg/dL"
            },
            'blood_pressure': {
                'key': 'blood pressure:',
                'type': float,
                'required': False,
                'validation': lambda x: 0 <= x <= 300,
                'error_msg': "Blood pressure must be between 0 and 300 mmHg"
            },
            'cholesterol': {
                'key': 'cholesterol:',
                'type': float,
                'required': False,
                'validation': lambda x: 0 <= x <= 1000,
                'error_msg': "Cholesterol must be between 0 and 1000 mg/dL"
            },
            'body_fat_pct': {
                'key': 'body fat:',
                'type': float,
                'required': False,
                'validation': lambda x: 0 <= x <= 100,
                'error_msg': "Body fat percentage must be between 0 and 100"
            },
            'diabetes': {
                'key': 'diabetes:',
                'type': int,
                'required': False,
                'validation': lambda x: x in [0, 1],
                'error_msg': "Diabetes must be 0 (No) or 1 (Yes)"
            },
            'hypertension': {
                'key': 'hypertension:',
                'type': int,
                'required': False,
                'validation': lambda x: x in [0, 1],
                'error_msg': "Hypertension must be 0 (No) or 1 (Yes)"
            },
            'heart_disease': {
                'key': 'heart disease:',
                'type': int,
                'required': False,
                'validation': lambda x: x in [0, 1],
                'error_msg': "Heart disease must be 0 (No) or 1 (Yes)"
            },
            'dietary_restriction': {
                'key': 'dietary restriction:',
                'type': str,
                'required': False,
                'validation': lambda x: True,  # Accept any string
                'error_msg': "Invalid dietary restriction format"
            },
            'dietary_goal': {
                'key': 'dietary goal:',
                'type': str,
                'required': False,
                'validation': lambda x: True,  # Accept any string
                'error_msg': "Invalid dietary goal format"
            }
        }
        # Process each line
        for line in lines:
            line = line.lower().strip()
            for field, config in field_config.items():
                if config['key'] in line:
                    try:
                        # Extract and convert value
                        value = line.split(':', 1)[1].strip()
                        converted_value = config['type'](value)

                        # Validate value
                        if config['validation'](converted_value):
                            health_info[field] = converted_value
                        else:
                            st.warning(config['error_msg'])
                            if config['required']:
                                return None
                    except (ValueError, IndexError) as e:
                        st.warning(f"Invalid value for {field}: {str(e)}")
                        if config['required']:
                            return None
                    break

        # Check for missing required fields (Age, Gender)
        missing_required = [
            field for field, config in field_config.items()
            if config['required'] and field not in health_info
        ]

        if missing_required:
            st.error(f"Missing required fields: {', '.join(missing_required)}")
            return None

        return health_info

    except Exception as e:
        st.error(f"Error processing health report: {str(e)}")
        return None



def update_health_data(user_id, health_info, is_new_user=False):
    """Update health_data.csv with new user information"""
    try:
        if not health_info:
            st.error("Missing health information")
            return False, None

        # Generate new user ID for new users
        if is_new_user:
            health_data = load_health_data()
            user_id = generate_new_user_id(health_data)

        if not user_id:
            st.error("Invalid user ID")
            return False, None

        # Load existing data
        health_data = load_health_data()

        # Create new data entry
        new_data = pd.DataFrame({
            'user_id': [user_id],
            'age': [health_info.get('age')],
            'gender': [health_info.get('gender')],
            'ethnicity': [health_info.get('ethnicity')],
            'height': [health_info.get('height')],
            'weight': [health_info.get('weight')],
            'bmi': [health_info.get('bmi')],
            'blood_sugar': [health_info.get('blood_sugar')],
            'blood_pressure': [health_info.get('blood_pressure')],
            'cholesterol': [health_info.get('cholesterol')],
            'body_fat_pct': [health_info.get('body_fat_pct')],
            'diabetes': [health_info.get('diabetes')],
            'hypertension': [health_info.get('hypertension')],
            'heart_disease': [health_info.get('heart_disease')]
        })

        # Get the path for saving
        # Get the current working directory (should be agent/)
        cwd = Path.cwd()
        # Calculate the data file path relative to cwd
        data_path = cwd / "src" / "data" / "health_data.csv"

        # Update or create CSV file
        if not health_data.empty:
            if str(user_id) in health_data['user_id'].astype(str).values:
                # Update existing record
                health_data.loc[health_data['user_id'].astype(str) == str(user_id)] = new_data.iloc[0]
                updated_data = health_data
            else:
                # Append new record
                updated_data = pd.concat([health_data, new_data], ignore_index=True)
        else:
            # Create new CSV file
            updated_data = new_data

        # Save the updated data
        updated_data.to_csv(data_path, index=False)

        # Clear the cache
        load_health_data.clear()

        return True, user_id

    except Exception as e:
        st.error(f"Error updating health data: {str(e)}")
        return False, None 