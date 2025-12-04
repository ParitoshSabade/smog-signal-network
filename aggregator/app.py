# aggregator/app.py
import os
import json
import threading
import time
from flask import Flask, jsonify
from flask_cors import CORS
from kafka import KafkaConsumer, errors
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9093")
ENRICHED_TOPIC = "enriched-air-quality"
CONSUMER_GROUP = "aggregator-group-final" 

LEADERBOARD_SIZE = 1000 
# --- In-Memory Storage ---
CITY_DATA_STORE = {}

app = Flask(__name__)
CORS(app)

def start_kafka_consumer():
    """
    Background thread that listens to Kafka and updates the global CITY_DATA_STORE 
    and maintains the top 1000 leaderboard, sorted by raw concentration and displaying the category.
    """
    global CITY_DATA_STORE 
    
    print(f"Aggregator connecting to Kafka broker at {KAFKA_BROKER}...")
    
    while True:
        try:
            consumer = KafkaConsumer(
                ENRICHED_TOPIC,
                bootstrap_servers=[KAFKA_BROKER],
                auto_offset_reset='earliest', 
                enable_auto_commit=True,
                group_id=CONSUMER_GROUP,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            consumer.poll(timeout_ms=1000)

            if not consumer.assignment():
                print(f"⚠️ Topic '{ENRICHED_TOPIC}' not yet created by Analyzer. Waiting...")
                time.sleep(5)
                consumer.close()
                continue
            
            print(f"✅ Aggregator Consumer successfully assigned to topic '{ENRICHED_TOPIC}'. Starting data consumption.")

            for message in consumer:
                data = message.value
                location = data.get('city_name', 'Unknown')
                
                # Metrics for console display and sorting
                current_value = data.get('value') 
                current_unit = data.get('value_unit_raw', data.get('unit', ''))
                current_category = data.get('aq_category', 'N/A') # Retrieve the new category field

                if current_value is not None and location != 'Unknown':
                    
                    # 1. ALWAYS UPDATE THE LATEST STATE FOR THE CITY
                    CITY_DATA_STORE[location] = data
                    
                    # 2. LEADERBOARD MAINTENANCE (Top 1000)
                    
                    all_cities = list(CITY_DATA_STORE.values())
                    
                    # Sort by the raw concentration value (worst/highest first)
                    sorted_cities = sorted(all_cities, key=lambda x: x.get('value', 0), reverse=True)
                    
                    # Reconstruct the store with only the top 1000 cities
                    new_store = {}
                    
                    for city_data in sorted_cities[:LEADERBOARD_SIZE]:
                        new_store[city_data['city_name']] = city_data
                        
                    CITY_DATA_STORE = new_store 
                    
                    # 3. UPDATED PRINT STATEMENT to include the category
                    print(f"✅ AGGREGATOR RECEIVED & UPDATED: {location} (Raw Value: {current_value} {current_unit}, Category: **{current_category}**). Leaderboard Size: {len(CITY_DATA_STORE)}")

            print("Consumer loop terminated unexpectedly. Retrying...")
            consumer.close()

        except errors.NoBrokersAvailable:
            print(f"❌ KAFKA ERROR: No brokers available at {KAFKA_BROKER}. Retrying in 5s.")
            time.sleep(5)
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR in Aggregator thread: {e}. Retrying in 5s.")
            time.sleep(5)


@app.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    # 1. Convert Dictionary values to a List
    all_cities = list(CITY_DATA_STORE.values())
    
    # 2. Re-sort to ensure correctness (by raw concentration value)
    sorted_cities = sorted(all_cities, key=lambda x: x.get('value', 0), reverse=True)
    
    # The API response now includes 'value' (raw concentration) and 'aq_category' (e.g., "Unhealthy")
    return jsonify(sorted_cities)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "total_cities_tracked": len(CITY_DATA_STORE)})

def main():
    # 1. Start the Kafka Consumer in a separate background thread
    consumer_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    consumer_thread.start()
    
    # 2. Start the Flask Web Server (Blocking)
    print("🚀 Aggregator API running on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001)

if __name__ == "__main__":
    main()