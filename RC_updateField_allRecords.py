import requests
from dotenv import load_dotenv
import os
import json
import re

# Load environment variables
load_dotenv()

# Get API credentials
API_URL = os.getenv('REDCAP_API_URL')
API_TOKEN = os.getenv('REDCAP_API_TOKEN_CPAT')

if not API_URL or not API_TOKEN:
    print("❌ ERROR: Missing API URL or API Token. Check your .env file.")
    exit()

# Ask user for the field to update
field_name_to_update = input("Enter the calculated field name to update: ").strip()

# Fetch metadata to get the calculation formula
metadata_params = {
    'token': API_TOKEN,
    'content': 'metadata',
    'format': 'json'
}
metadata_response = requests.post(API_URL, data=metadata_params)
metadata = metadata_response.json() if metadata_response.status_code == 200 else []

# Find the field metadata to get action tag and formula
field_metadata = next(
    (field for field in metadata if field['field_name'] == field_name_to_update),
    None
)

if not field_metadata:
    print(f"❌ ERROR: No metadata found for '{field_name_to_update}'.")
    exit()

# Get the action tag (if it exists)
action_tag = field_metadata.get('action_tag', '')

# Check if the field is a text field with @CALCTEXT action tag
def handle_calctext_formula(formula):
    """ Handle the conversion of the @CALCTEXT formula to Python-compatible string formula. """
    if '@CALCTEXT' in formula:
        # Extract everything inside @CALCTEXT()
        formula = re.search(r'@CALCTEXT\((.+?)\)', formula).group(1)
        # Convert any necessary REDCap function to Python-compatible syntax, like replacing isnumber with isnumeric
        formula = formula.replace("isnumber", "str.isnumeric")  # Convert isnumber to Python's isnumeric for strings
    return formula

# If it's a text field and has an @CALCTEXT tag, handle the formula
if action_tag == '@CALCTEXT':
    field_formula = handle_calctext_formula(field_metadata['select_choices_or_calculations'])
else:
    field_formula = field_metadata['select_choices_or_calculations']

# Convert REDCap if-statements to Python syntax
def convert_redcap_if_statements(formula):
    """ Convert REDCap-style if statements to Python-compatible syntax. """
    formula = re.sub(r'if\(([^,]+),([^,]+),(.+)\)', r'(\2 if \1 else \3)', formula)
    return formula

# Modify formula to be Python-compatible
field_formula = convert_redcap_if_statements(field_formula)

# Fetch all records
params = {
    'token': API_TOKEN,
    'content': 'record',
    'format': 'json'
}
response = requests.post(API_URL, data=params)

if response.status_code == 200:
    records = response.json()
    records_to_update = []

    print("\n🔍 Checking records...\n")

    def calculate_expected_value(record, formula):
        """ Replace variables in formula with actual values and evaluate it safely. """
        try:
            modified_formula = formula

            # Find all variable placeholders in the formula
            variables = re.findall(r'\[([a-zA-Z0-9_]+)\]', formula)

            for var in variables:
                value = record.get(var, "0")  # Default to "0" if field is missing
                
                # Log for debugging
                # print(f"🔹 Replacing [{var}] with '{value}' in formula.")

                if isinstance(value, str) and value.replace('.', '', 1).isdigit():
                    value = float(value)  # Convert numeric strings to float
                elif not isinstance(value, (int, float)):  # Handle non-numeric values
                    print(f"⚠️ WARNING: Skipping [{var}] because it has a non-numeric value: '{value}'")
                    return f"Error: Non-numeric value in [{var}]"

                # Replace REDCap-style [field_name] with actual values
                modified_formula = modified_formula.replace(f'[{var}]', str(value))

            # Debug: Print the modified formula before evaluating
            # print(f"🔢 Evaluating formula: {modified_formula}")

            # Safely evaluate formula
            return eval(modified_formula)
        
        except SyntaxError as e:
            return f"Error: Invalid syntax in formula ({e})"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except Exception as e:
            return f"Error: {e}"

    # Loop through records and check for discrepancies
    for record in records:
        actual_value = record.get(field_name_to_update, "N/A")
        expected_value = calculate_expected_value(record, field_formula)

        if str(actual_value) != str(expected_value):
            print(f"Record ID: {record['record_id']}")
            # print(f"   ✅ Current: {actual_value}  ➝  🔢 Expected: {expected_value}\n")
            records_to_update.append({'record_id': record['record_id'], field_name_to_update: expected_value})

    if not records_to_update:
        print("✅ All records already have the correct values. No updates needed.")
        exit()

    # Ask for confirmation before applying updates (accept 'y' for yes and 'n' for no)
    confirm = input("Do you want to update all records with the expected values? (y/n): ").strip().lower()

    if confirm in ['y', 'yes']:
        # Send update request to REDCap
        update_params = {
            'token': API_TOKEN,
            'content': 'record',
            'format': 'json',
            'data': json.dumps(records_to_update)
        }
        update_response = requests.post(API_URL, data=update_params)

        if update_response.status_code == 200:
            print("✅ All records have been updated successfully!")
        else:
            print(f"❌ ERROR: Failed to update records. {update_response.text}")
    else:
        print("⏸️ No changes were made.")
else:
    print(f"❌ ERROR: {response.status_code}")
    print(response.text)  # Print error details
