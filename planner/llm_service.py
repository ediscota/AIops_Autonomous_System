import time
import json
import requests
import threading
import configparser
import paho.mqtt.client as mqtt

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]
TIMEOUT = 120 # seconds

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

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

# ---- Private method (blocking) ----
def _send_to_llm_blocking(data):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": PLANNER_PROMPT.format(plan=data),
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


# ---- Public method (async) ----
def send_to_llm(data):
    thread = threading.Thread(
        target=_send_to_llm_blocking,
        args=(data,),
        daemon=True
    )
    thread.start()