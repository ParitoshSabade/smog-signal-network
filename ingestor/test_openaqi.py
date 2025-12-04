# test_openaq.py (FINAL, FINAL, FINAL, FINAL FIX - Using requests)
import os
import requests
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")
POLLUTANT_ID = 2  # PM2.5
RESULTS_LIMIT = 5 
# ---------------------

def test_connection():
    """Attempts to connect to OpenAQ using the direct REST API endpoint."""
    if not OPENAQ_API_KEY:
        print("🛑 ERROR: OPENAQ_API_KEY is not set in your .env file.")
        return

    try:
        print(f"✅ Attempting connection with API Key: {OPENAQ_API_KEY[:4]}...{OPENAQ_API_KEY[-4:]}")
        
        # 1. Construct the URL and headers directly
        BASE_URL = "https://api.openaq.org/v3/"
        ENDPOINT = f"parameters/{POLLUTANT_ID}/latest" # Endpoint for latest values
        
        HEADERS = {
            "accept": "application/json",
            "X-API-Key": OPENAQ_API_KEY
        }
        
        PARAMS = {
            "limit": RESULTS_LIMIT
        }

        print(f"🌍 Fetching {RESULTS_LIMIT} latest PM2.5 measurements using endpoint: {ENDPOINT}...")
        
        # 2. Make the HTTP GET request
        response = requests.get(
            f"{BASE_URL}{ENDPOINT}", 
            headers=HEADERS, 
            params=PARAMS
        )
        
        # 3. Check for successful status code (200)
        response.raise_for_status() 
        
        data = response.json()
        measurements = data.get("results")

        if measurements:
            print(f"\n🎉 SUCCESS! Received {len(measurements)} measurements.")
            print("--- Sample Measurement Data Point ---")
            
            first_data_point = measurements[0]
            
            # --- THE FINAL PARSING FIX IS HERE ---
            print(f"  Location Name: {first_data_point.get('location_name')} ({first_data_point.get('country_code')})")
            
            # Accessing nested dictionaries:
            datetime_obj = first_data_point.get('datetime', {})
            coords_obj = first_data_point.get('coordinates', {})
            
            print(f"  Value: {first_data_point.get('value')} {first_data_point.get('unit')}")
            print(f"  Time (UTC): {datetime_obj.get('utc')}")
            print(f"  Coordinates: Lat={coords_obj.get('latitude')}, Lon={coords_obj.get('longitude')}")
            print("-------------------------")

            return True
        else:
            print("⚠️ WARNING: Connection succeeded, but no measurements were returned.")
            return False

    except requests.exceptions.HTTPError as http_err:
        print(f"\n❌ FATAL ERROR: HTTP error occurred (Status {response.status_code}).")
        print(f"Error details: {response.text}")
        return False
    except Exception as e:
        print(f"\n❌ FATAL ERROR: An unexpected error occurred.")
        print(f"Error details: {e}")
        return False

if __name__ == "__main__":
    test_connection()