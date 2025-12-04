# 🌍 Smog Signal Network: Real-time Air Quality Leaderboard

A scalable, data-streaming microservices pipeline designed to ingest, process, and aggregate global PM2.5 air quality data in real-time. The system uses a local Kafka cluster for high-throughput messaging between services and presents the current Air Quality Index (AQI) leaderboard on a React frontend.

## Key Features

* **Real-time Ingestion:** Polls the **OpenAQ API** for air quality data from over 1,000 global cities with populations above 500k.
* **Event-Driven Architecture:** Uses **Apache Kafka** to decouple microservices (Ingestor, Analyzer, Aggregator).
* **Data Enrichment:** Classifies raw PM2.5 values into EPA-standard **Air Quality Index (AQI) categories** (e.g., 'Hazardous', 'Very Unhealthy').
* **Leaderboard:** Maintains an up-to-date, sorted global leaderboard showing the worst affected cities based on raw PM2.5 concentration.
* **Modern Frontend:** Built with **React** and **Tailwind CSS** for a fast, responsive, and color-coded data visualization.

---

## 🏗️ Architecture and Flow Diagram

The **Smog Signal Network** is built on an event-driven, three-tier microservices architecture. Data flows unidirectionally from the source (OpenAQ) to the user interface (React) via Kafka topics.



* **Ingestor** (`ingestor/app.py`): Fetches raw PM2.5 data from the OpenAQ API and publishes it to the `raw-air-quality` Kafka topic.
* **Analyzer** (`analyzer/app.py`): Consumes raw data, calculates and assigns an EPA-standard **Air Quality Category**, and publishes the enriched data to the `enriched-air-quality` Kafka topic.
* **Aggregator** (`aggregator/app.py`): Consumes enriched data, maintains a fast, in-memory **leaderboard** (sorted by raw concentration), and exposes it via a Flask REST API on `http://localhost:5001/leaderboard`.
* **Frontend** (`frontend/`): A React application that polls the Aggregator API every 30 seconds to display the real-time leaderboard.

---

## ⚙️ Prerequisites and Local Run Instructions

This project requires **Python 3.8+** (with `venv` recommended), **Node.js/npm**, and a local **Kafka Broker** running.

### Prerequisites

* **Python:** 3.8+
* **Node.js/npm:** For the React Frontend.
* **Apache Kafka:** Ensure your local Kafka Broker is running on `localhost:9093` (or adjust the `.env` file accordingly).
* **OpenAQ API Key:** A free API key from OpenAQ is required for the Ingestor.

### Step 1: Clone the Repository & Setup Environment

```bash
git clone <YOUR_REPO_URL>
cd smog-signal-network

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Configure Environment Variables
Create a file named .env in the root directory and populate it with your configuration.
# .env file
# Kafka Broker Address 
KAFKA_BROKER="localhost:9093" 

# Your OpenAQ API Key
OPENAQ_API_KEY="YOUR_OPENAQ_API_KEY_HERE"

### Step 3: Install Dependencies
# Install dependencies for all Python services
```bash
pip install -r ingestor/requirements.txt
pip install -r analyzer/requirements.txt
pip install -r aggregator/requirements.txt

# Install Node dependencies for the React frontend
cd frontend
npm install
cd ..
```
### Step 4: Run the Microservices (in 3 Separate Terminal Tabs)
IMPORTANT: Start the services in order (Ingestor $\rightarrow$ Analyzer $\rightarrow$ Aggregator) to ensure the Kafka topics are created and data flow is established.

# 1. Start Ingestor (Terminal Tab 1)
```Bash
(venv) python ingestor/app.py
```
# 2. Start Analyzer (Terminal Tab 2)
```Bash
(venv) python analyzer/app.py
```
# 3. Start Aggregator (Terminal Tab 3)
```Bash
(venv) python aggregator/app.py
```
# Step 5: Start Frontend
Navigate to the frontend directory and start the development server.
```Bash
cd frontend
npm run dev
```
The leaderboard will be accessible at http://localhost:5173

### Screenshots (Proof of Concept)
These screenshots validate the real-time processing and the final user experience.

# 1. Analyzer Output (Data Enrichment)
This terminal shows the Analyzer consuming raw data and successfully enriching it with the calculated AQI Category before publishing to the enriched topic.

![Analyzer Terminal Log showing categorization](Screenshot 2025-12-04 at 11.03.16 AM.png)

# 2. Aggregator Output (Leaderboard Updates)
This terminal confirms the Aggregator is successfully connected to the enriched topic and is actively updating its in-memory data store for the leaderboard.

![Aggregator Terminal Log showing updated leaderboard size](Screenshot 2025-12-04 at 11.03.35 AM.png)

# 3. Frontend Leaderboard
The final React dashboard, displaying the real-time, sorted, and color-coded air quality data consumed from the Aggregator API.

![Global PM2.5 Leaderboard Frontend UI](Screenshot 2025-12-04 at 9.53.52 AM.png)
