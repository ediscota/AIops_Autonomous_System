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

PLANNER_LLM_TOPIC = "AIops/planner_llm_response"
PLANNER_PROMPT = """
You are an AIOps expert explaining a remediation plan for a Kubernetes system.

Your task is to clearly explain *why* the proposed actions were chosen, based strictly on the provided planner decision.

Rules:
1. Explain the rationale behind the actions.
2. Reference the affected cluster and container when relevant.
3. Be concise. Use maximum 3 sentences.

Planner Decision:
{plan}
"""

# MQTT setup
while True:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("[Planner LLM Service] MQTT ready")
        break
    except Exception as e:
        print(f"[Planner LLM Service] MQTT not ready: {e}")
        time.sleep(2)

# Private method (blocking)
def _send_to_llm_blocking(data):
    payload = {
        "model": MODEL_NAME,
        "prompt": PLANNER_PROMPT.format(plan=data),
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
            PLANNER_LLM_TOPIC,
            json.dumps({
                "timestamp": time.time(),
                "response": response.json().get("response")
            })
        )

        print("[Planner LLM Service] Response published")

    except requests.exceptions.ReadTimeout:
        print("[Planner LLM Service] Ollama timeout")

    except Exception as e:
        print("[Planner LLM Service] Ollama error:", e)


# Public method (async)
def send_to_llm(data):
    thread = threading.Thread(
        target=_send_to_llm_blocking,
        args=(data,),
        daemon=True
    )
    thread.start()