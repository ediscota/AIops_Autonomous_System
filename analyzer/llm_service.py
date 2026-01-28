import time
import requests
import configparser
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt
import json

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]
TIMEOUT = 120 # seconds

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])
ANALYZER_LLM_TOPIC = "AIops/analyzer_llm_response"
ANALYZER_PROMPT = """
You are an AIOps expert monitoring a Kubernetes system.
Your task is to summarize the current system health based strictly on the provided anomaly logs.

Rules:
1. Identify which cluster and container is failing.
2. Mention the specific issue (e.g., High CPU, Latency, Crash).
3. Be concise. Use maximum 2 sentences.

Metrics:
{metrics}
"""

# Waiting for MQTT
while True:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("[Analyzer LLM Service] MQTT ready")
        break
    except Exception as e:
        print(f"[Analyzer LLM Service] MQTT not ready: {e}")
        time.sleep(2)

def send_to_llm(data): #asincornous
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": ANALYZER_PROMPT.format(metrics=data),
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()

        mqtt_client.publish(
            ANALYZER_LLM_TOPIC,
            json.dumps({
                "timestamp": time.time(),
                "response": response.json().get("response")
            })
            
        )
    
    except requests.exceptions.ReadTimeout:
        print("[Analyzer] Ollama still warming up, skipping this cycle")
        return None

    except Exception as e:
        print("[Analyzer] Ollama error:", e)
        return None
    