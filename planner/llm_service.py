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
TIMEOUT = 300 # Aumentiamo a 5 minuti per sicurezza

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

PLANNER_LLM_TOPIC = "AIops/planner_llm_response"
PLANNER_PROMPT = """
You are an AIOps expert explaining a remediation plan for a Kubernetes system.
Your task is to clearly explain *why* the proposed actions were chosen.
Rules:
1. Explain the rationale behind the actions.
2. Reference the affected cluster and container.
3. Be concise. Use maximum 3 sentences.

Planner Decision:
{plan}
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
            print("[Planner LLM Service] MQTT ready")
            break
        except Exception as e:
            print(f"[Planner LLM Service] MQTT not ready: {e}")
            time.sleep(2)

start_mqtt()

# ---- Private method (blocking) ----
def _send_to_llm_blocking(data):
    try:
        print("[Planner LLM Service] Sending request to Ollama...")
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": PLANNER_PROMPT.format(plan=data),
            "stream": False
        }

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()

        response_text = response.json().get("response")

        mqtt_client.publish(
            PLANNER_LLM_TOPIC,
            json.dumps({
                "timestamp": time.time(),
                "response": response_text
            })
        )

        print("[Planner LLM Service] Response published!")

    except requests.exceptions.ReadTimeout:
        print("[Planner LLM Service] Ollama TIMEOUT - System overloaded")
    except Exception as e:
        print(f"[Planner LLM Service] Error: {e}")
    finally:
        # FONDAMENTALE: Rilascia il semaforo
        if llm_lock.locked():
            llm_lock.release()
            print("[Planner LLM Service] Lock released. Ready for next task.")


# ---- Public method (Smart Async) ----
def send_to_llm(data):
    # --- FIX CRUCIALE ---
    # Se il semaforo è rosso (c'è già un thread che lavora), SCARTIAMO la richiesta.
    # Inutile accodare richieste che andranno in timeout.
    if llm_lock.locked():
        print("[Planner LLM Service] SKIPPING: Ollama is busy with a previous request.")
        return

    # Se è verde, lo blocchiamo e partiamo
    llm_lock.acquire()
    
    thread = threading.Thread(
        target=_send_to_llm_blocking,
        args=(data,),
        daemon=True
    )
    thread.start()