import os
import time
import json
import requests
import threading
import queue
import paho.mqtt.client as mqtt

# Config parsing
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_LLM_USER")
MQTT_PASSWORD = os.getenv("MQTT_LLM_PASSWORD")

MODEL_NAME = os.environ.get("MODEL_NAME")
MODEL_URL = os.environ.get("MODEL_URL")
TIMEOUT = int(os.environ.get("MODEL_TIMEOUT", 300))

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

# Processing Queue (FIFO) with max size to prevent memory overflow
llm_queue = queue.Queue(maxsize=10)

# MQTT setup
mqtt_client = mqtt.Client()

def start_mqtt():
    while True:
        try:
            mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            mqtt_client.loop_start()
            print("[Planner LLM Service] MQTT ready")
            break
        except Exception as e:
            print(f"[Planner LLM Service] MQTT not ready: {e}")
            time.sleep(2)

start_mqtt()

# Worker Function (Consumer) running in a separate thread
def _worker_loop():
    print("[Planner LLM Service] Worker thread started. Waiting for tasks...")
    
    while True:
        # 1. Get item from queue (blocks if empty)
        data = llm_queue.get()
        
        try:
            # 2. Process request (Blocking HTTP call)
            _process_llm_request(data)
            
        except Exception as e:
            print(f"[Planner LLM Service] Unexpected error in worker: {e}")
            
        finally:
            # 3. Mark task as done
            llm_queue.task_done()
            print(f"[Planner LLM Service] Task completed. Remaining in queue: {llm_queue.qsize()}")

# Private method (Actual HTTP logic)
def _process_llm_request(data):
    try:
        print("[Planner LLM Service] Processing new request from queue...")
        
        payload = {
            "model": MODEL_NAME,
            "prompt": PLANNER_PROMPT.format(plan=data),
            "stream": False
        }

        response = requests.post(
            MODEL_URL,
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

        print("[Planner LLM Service] Response published to MQTT")

    except requests.exceptions.ReadTimeout:
        print("[Planner LLM Service] Ollama timeout")
    except Exception as e:
        print("[Planner LLM Service] Ollama error:", e)


# Start the worker thread once
worker_thread = threading.Thread(target=_worker_loop, daemon=True)
worker_thread.start()


# Public Method (Producer)
def send_to_llm(data):
    # Non-blocking put. If queue is full, drop the request to maintain performance.
    try:
        llm_queue.put(data, block=False)
        print(f"[Planner LLM Service] Request added to queue. Current size: {llm_queue.qsize()}")
    except queue.Full:
        print("[Planner LLM Service] Queue is full (max 10). Dropping request.")