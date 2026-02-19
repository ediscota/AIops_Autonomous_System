AIOps Autonomous System
This project implements a self-adaptive MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge) loop to manage a simulated Kubernetes microservices infrastructure. 
It leverages MQTT for communication, InfluxDB for telemetry storage, and Ollama (LLM) for explainable AI reasoning.

1. Prerequisites
Ensure you have the following installed on your machine:
Docker (Engine 20.10+)
Docker Compose (V2 recommended)

2. Configuration
The system is controlled by the config.ini and .env files.

Environment Variables: Create/check your .env file to set the model name:
MODEL_NAME=qwen2.5:1.5b
MODEL_URL=http://ollama_docker:11434/api/generate

System Rules: Adjust thresholds and managed containers in config/config.ini.

3. Running the System
Run the entire stack:
docker compose up

4. Stopping the System
To stop all services and remove the containers:
docker compose down

System Architecture
The project is composed of the following microservices:
-Managed Resources: Simulated clusters and containers generating telemetry.
-Mosquitto: The MQTT broker facilitating asynchronous communication.
-Telegraf: The Monitor agent that pipes MQTT data into the Database.
-InfluxDB: Time-series storage for system metrics.
-Analyzer: Monitors InfluxDB and identifies severity states (Warning/Critical).
-Planner: Rule-based engine that utilizes the LLM Service for explainability.
-Executor: Dispatches commands back to the Managed Resources.
-Dashboard: Web interface to visualize metrics and AI-generated explanations.
