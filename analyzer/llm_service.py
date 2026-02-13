import os
import time
import json
import requests
import threading
import paho.mqtt.client as mqtt

# Config parsing
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

MODEL_NAME = os.environ.get("MODEL_NAME")
MODEL_URL = os.environ.get("MODEL_URL")
TIMEOUT = int(os.environ.get("MODEL_TIMEOUT", 120))

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

# MQTT setup
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


# ---- Private method (blocking) ----
def _send_to_llm_blocking(data):
    payload = {
        "model": MODEL_NAME,
        "prompt": ANALYZER_PROMPT.format(metrics=data),
        "stream": False
    }

    try:
        response = requests.post(
            MODEL_URL,
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

        print("[Analyzer LLM Service] Response published")

    except requests.exceptions.ReadTimeout:
        print("[Analyzer LLM Service] Ollama timeout")

    except Exception as e:
        print("[Analyzer LLM Service] Ollama error:", e)


# ---- Public method (async) ----
def send_to_llm(data):
    thread = threading.Thread(
        target=_send_to_llm_blocking,
        args=(data,),
        daemon=True
    )
    thread.start()