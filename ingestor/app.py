# ingestor/app.py
import os
import json
import time
import requests
import itertools
from kafka import KafkaProducer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration (Unchanged) ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9093") 
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

CITIES_FILE = "cities_100k_coordinates.json" 
KAFKA_TOPIC = "raw-air-quality" 
BASE_URL = "https://api.openaq.org/v3/"

BATCH_SIZE = 25  
POLLING_INTERVAL_SECONDS = 60 
RADIUS_METERS = 12000 
PM25_PARAMETER_ID = 2 # OpenAQ ID for PM2.5
# ---------------------------------

def create_kafka_producer():
    """Initializes and returns a Kafka Producer instance."""
    print(f"Connecting to Kafka broker at {KAFKA_BROKER}...")
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5
    )

def load_cities():
    """Loads the list of cities from the local JSON file."""
    if not os.path.exists(CITIES_FILE):
        print(f"ERROR: City list file not found: {CITIES_FILE}")
        return []
    try:
        with open(CITIES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Could not load JSON file: {e}")
        return []

def get_nearest_location_data(latitude, longitude, city_name):
    """
    *** MODIFIED ***
    Finds the nearest PM2.5 reporting location and extracts the PM2.5 sensor ID.
    """
    
    # API Call 1: Find location reporting PM2.5
    ENDPOINT = "locations"
    HEADERS = { "accept": "application/json", "X-API-Key": OPENAQ_API_KEY }
    PARAMS = {
        "coordinates": f"{latitude},{longitude}",
        "radius": RADIUS_METERS,
        "limit": 1, 
        "parameter_id": PM25_PARAMETER_ID # Filters to PM2.5 reporting locations
    }

    try:
        response = requests.get(
            f"{BASE_URL}{ENDPOINT}", 
            headers=HEADERS, 
            params=PARAMS
        )
        response.raise_for_status() 
        data = response.json()
        
        results = data.get("results", [])

        if results:
            location = results[0]
            location_id = location.get('id')
            distance = location.get('distance')
            
            # --- NEW/REINTRODUCED LOGIC: Extract the PM2.5 Sensor ID ---
            pm25_sensor_id = None
            for sensor in location.get('sensors', []):
                # We need the sensor that corresponds to PM2.5 (ID 2)
                if sensor.get('parameter', {}).get('id') == PM25_PARAMETER_ID:
                    pm25_sensor_id = sensor['id']
                    break
            # --- END LOGIC ---
            
            if location_id and pm25_sensor_id:
                 print(f"   -> Found monitor (ID: {location_id}, Sensor ID: {pm25_sensor_id}) for {city_name} at {distance/1000:.1f} km.")
                 return {
                    "city_name": city_name,
                    "location_id": location_id,
                    "pm25_sensor_id": pm25_sensor_id, # Add sensor ID to data payload
                    "latitude": latitude,
                    "longitude": longitude
                }
            
        print(f"   -> No PM2.5 monitor found within {RADIUS_METERS/1000}km of {city_name}.")
        return None

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP Error (Status {response.status_code}) while finding location for {city_name}: {response.text}")
        return None
    except Exception as e:
        print(f"❌ General Error finding location for {city_name}: {e}")
        return None

def get_latest_measurement(location_data):
    """
    Pulls the latest PM2.5 measurement using the confirmed working endpoint:
    GET /v3/sensors/{sensor_id}/measurements
    """
    
    location_id = location_data['location_id']
    sensor_id = location_data['pm25_sensor_id']
    city_name = location_data['city_name']
    
    ENDPOINT = f"sensors/{sensor_id}/measurements"
    
    HEADERS = { "accept": "application/json", "X-API-Key": OPENAQ_API_KEY }
    PARAMS = {
        "limit": 1, 
        "sort": "desc" 
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}{ENDPOINT}", 
            headers=HEADERS, 
            params=PARAMS
        )
        response.raise_for_status() 
        data = response.json()
        
        results = data.get("results")
        
        # --- CRITICAL FIX START: Check if results list is not empty ---
        if not results:
            print(f"   -> No latest measurement available in the response for sensor ID {sensor_id} ({city_name}). (Empty Results List)")
            return None
        
        measurement = results[0] # Safely get the first measurement
        # --- CRITICAL FIX END ---
        
        if measurement.get('value') is not None:
            
            # Use the parameter from the measurement response if available, otherwise default
            parameter_name = measurement.get('parameter', {}).get('name') or "pm25"
            
            # --- Normalize Data ---
            return {
                "city_name": city_name,
                "location_id": location_id,
                "timestamp": measurement.get('datetime', {}).get('utc'),
                "latitude": location_data['latitude'],
                "longitude": location_data['longitude'],
                "value": measurement['value'],
                "unit": measurement.get('unit') or "µg/m³",
                "parameter": parameter_name
            }
        else:
            print(f"   -> Latest measurement found, but value is missing for sensor ID {sensor_id} ({city_name}).")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP Error for measurement at {city_name} (ID: {location_id}, Status: {response.status_code})")
        return None
    except Exception as e:
        # Catch any other unexpected error, like a structural issue in the JSON
        print(f"❌ Error fetching measurement for {city_name}: {e}")
        return None


def main():
    if not OPENAQ_API_KEY:
        print("ERROR: OPENAQ_API_KEY is missing. Cannot poll API.")
        return

    producer = create_kafka_producer()
    cities = load_cities()
    
    if not cities:
        return

    city_iterator = itertools.cycle(cities)
    total_cities = len(cities)
    current_cycle_count = 0

    print(f"Starting ingestion loop over {total_cities} cities. Batch size: {BATCH_SIZE}.")

    while True:
        locations_with_ids = []
        batch_start_time = time.time()

        # 1. LOCATION ID FINDING (API Call 1: Locations)
        print(f"\n--- Cycle {current_cycle_count // total_cities + 1}, Batch Start ---")
        
        # Get location IDs for BATCH_SIZE cities
        for i in range(BATCH_SIZE):
            try:
                city = next(city_iterator)
                current_cycle_count += 1
                
                # Get the location ID and Sensor ID (API Call 1)
                location_data = get_nearest_location_data(city['latitude'], city['longitude'], city['city_name'])
                
                if location_data:
                    locations_with_ids.append(location_data)

            except StopIteration:
                break
        
        # 2. MEASUREMENT POLLING (API Call 2: Measurements)
        print(f"-> Polling {len(locations_with_ids)} measurements...")
        
        successful_polls = 0
        for city_data in locations_with_ids:
            
            # Get the latest measurement (API Call 2)
            enriched_data = get_latest_measurement(city_data)
            
            if enriched_data:
                producer.send(KAFKA_TOPIC, value=enriched_data)
                print(f"   -> Sent {city_data['city_name']}: {enriched_data['value']} {enriched_data['unit']}")
                successful_polls += 1

        producer.flush()
        
        # 3. RATE LIMITING PAUSE
        time_spent = time.time() - batch_start_time
        sleep_time = max(0, POLLING_INTERVAL_SECONDS - time_spent)
        
        print(f"\nBatch completed ({successful_polls} successful polls) in {time_spent:.2f}s. Sleeping for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()