# analyzer/app.py
import os
import json
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9093") 
RAW_TOPIC = "raw-air-quality" 
ENRICHED_TOPIC = "enriched-air-quality"
CONSUMER_GROUP = "analyzer-group-classification" # Updated group ID
# ---------------------

# =========================================================================
# === PM2.5 Classification Utility Functions ===
# =========================================================================

# Breakpoints for PM2.5 concentration (µg/m³) and their corresponding categories
PM25_CLASSIFICATIONS = [
    (0.0, 12.0,   "Good"),
    (12.1, 35.4,  "Moderate"),
    (35.5, 55.4,  "Unhealthy for Sensitive Groups"),
    (55.5, 150.4, "Unhealthy"),
    (150.5, 250.4, "Very Unhealthy"),
    (250.5, 500.4, "Hazardous")
]

def get_pm25_category(value):
    """
    Determines the air quality category based on the PM2.5 concentration (µg/m³).
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "Unknown"
    
    if value < 0: return "Unknown"

    # Find the correct concentration range
    for c_low, c_high, category in PM25_CLASSIFICATIONS:
        if c_low <= value <= c_high:
            return category
    
    # Handle values above the maximum breakpoint
    if value > 500.4:
        return "Hazardous"
        
    return "Unknown" 

# =========================================================================

def create_kafka_consumer():
    """Initializes and returns a Kafka Consumer instance."""
    return KafkaConsumer(
        RAW_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id=CONSUMER_GROUP,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

def create_kafka_producer():
    """Initializes and returns a Kafka Producer instance."""
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5
    )


def transform_and_produce(consumer, producer):
    print("Analyzer started. Listening for raw data and classifying air quality...")
    
    for message in consumer:
        data = message.value
        
        raw_value = data.get('value')
        parameter = data.get('parameter')
        unit = data.get('unit')
        
        # Only process if we have a value, parameter, and unit
        if raw_value is not None and parameter and unit:
            
            # 1. Determine the Classification Category
            # We assume the data is PM2.5 as the Ingestor filters for it (PM25_PARAMETER_ID=2)
            category = get_pm25_category(raw_value)
            
            # 2. Add Classification fields to the data
            data['aq_category'] = category
            data['value_unit_raw'] = unit # Preserve unit for Aggregator display
            
            # The 'value' field still holds the raw concentration for sorting as requested.
            
            # 3. PRODUCE ENRICHED DATA
            producer.send(ENRICHED_TOPIC, value=data)
            
            print(f"-> {data['city_name']} | Raw: {raw_value} {unit} | Category: **{category}**")
        
    producer.flush() 


def main():
    try:
        producer = create_kafka_producer()
        consumer = create_kafka_consumer()
        transform_and_produce(consumer, producer)
    except KeyboardInterrupt:
        print("\nShutting down Analyzer.")
    except Exception as e:
        print(f"\nFATAL ERROR in main Analyzer loop: {e}")
    finally:
        if 'producer' in locals(): producer.close()
        if 'consumer' in locals(): consumer.close()


if __name__ == "__main__":
    main()