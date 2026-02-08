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
TIMEOUT = 300 # 5 minuti

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

ANALYZER_LLM_TOPIC = "AIops/analyzer_llm_response"
ANALYZER_PROMPT = """
You are an AIOps expert monitoring a Kubernetes system.
Summarize the current system health based strictly on the provided anomaly logs.
Rules:
1. Identify failing cluster/container.
2. Mention the specific issue.
3. Be concise (max 2 sentences).

Metrics:
{metrics}
"""

# --- FIX: SEMAFORO GLOBALE ---
llm_lock = threading.Lock()

# MQTT setup
mqtt_client = mqtt.Client()

def start_mqtt():
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            mqtt_client.loop_start()
            print("[Analyzer LLM Service] MQTT ready")
            break
        except Exception as e:
            print(f"[Analyzer LLM Service] MQTT not ready: {e}")
            time.sleep(2)

start_mqtt()

# ---- Private method (blocking) ----
def _send_to_llm_blocking(data):
    try:
        print("[Analyzer LLM Service] Sending request to Ollama...")
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": ANALYZER_PROMPT.format(metrics=data),
            "stream": False
        }

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

        print("[Analyzer LLM Service] Response published")

    except requests.exceptions.ReadTimeout:
        print("[Analyzer LLM Service] Ollama TIMEOUT")
    except Exception as e:
        print(f"[Analyzer LLM Service] Error: {e}")
    finally:
        if llm_lock.locked():
            llm_lock.release()
            print("[Analyzer LLM Service] Lock released.")


# ---- Public method (Smart Async) ----
def send_to_llm(data):
    # STESSO FIX DEL PLANNER: SCARTA SE OCCUPATO
    if llm_lock.locked():
        print("[Analyzer LLM Service] SKIPPING: Ollama is busy.")
        return

    llm_lock.acquire()
    
    thread = threading.Thread(
        target=_send_to_llm_blocking,
        args=(data,),
        daemon=True
    )
    thread.start()