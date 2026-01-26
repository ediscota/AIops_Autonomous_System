import time
import json
import requests
import configparser
import llm_service
import paho.mqtt.client as mqtt

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]

INPUT_TOPIC = "AIops/analyzer"
OUTPUT_TOPIC = "AIops/planner"

def on_message(client, userdata, msg):
    try:
        description = msg.payload.decode()
        if not description.strip():
            print("[Planner] Empty description received, skipping")
            return

        print("[Planner] Description received from Analyzer")

        # Pass the text directly to the LLM, which is expected to return JSON
        plan_raw = llm_service.send_to_llm(description)
        if not plan_raw:
            print("[Planner] LLM returned no output, skipping")
            return

        try:
            plan = json.loads(plan_raw)
        except json.JSONDecodeError:
            print("[Planner] Invalid JSON returned by LLM:")
            print(plan_raw)
            return

        print("[Planner] Publishing plan")
        client.publish(
            OUTPUT_TOPIC,
            json.dumps({
                "timestamp": time.time(),
                "plan": plan
            })
        )

    except Exception as e:
        print(f"[Planner] Unexpected error: {e}")


# Waiting for MQTT
while True:
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("[Planner] MQTT ready")
        break
    except Exception as e:
        print(f"[Planner] MQTT not ready: {e}")
        time.sleep(2)

client.subscribe(INPUT_TOPIC)
client.on_message = on_message

# Waiting for Ollama
payload = {
        "model": OLLAMA_MODEL,
        "prompt": "ping",
        "stream": False
    }

while True:
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        r.raise_for_status()
        print("[Planner] Ollama ready")
        break
    except Exception as e:
        print(f"[Planner] Ollama not ready: {e}")
        time.sleep(5)

print("[Planner] Started")
print("[Planner] Waiting for anomalies...")

while True:
    time.sleep(1)