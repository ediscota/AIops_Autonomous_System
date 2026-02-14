import os
import time
import json
import requests
import configparser
import llm_service
import paho.mqtt.client as mqtt

# Config parsing
config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

# Environment Variables
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_PLANNER_USER")
MQTT_PASSWORD = os.getenv("MQTT_PLANNER_PASSWORD")

INPUT_TOPIC = "AIops/analyzer"
OUTPUT_TOPIC = "AIops/planner"

MODEL_NAME = os.environ.get("MODEL_NAME")
MODEL_URL = os.environ.get("MODEL_URL")

# We load only the available metrics
try:
    ENABLED_METRICS = [m.strip() for m in config["general"]["metrics"].split(",")]
    print(f"[Planner] Monitoring metrics: {ENABLED_METRICS}")
except Exception as e:
    print(f"[Planner] Error loading metrics from config: {e}")
    ENABLED_METRICS = []

def decide_action(metric, severity):
    """
    Logica decisionale centralizzata.
    Ritorna l'azione stringa o None se non è richiesto alcun intervento.
    """
    if metric not in ENABLED_METRICS:
        return None

    if severity == "critical":
        return "restart"
    elif severity == "warning":
        return "scale_up"
    elif severity == "under_usage":
        return "scale_down"
    elif severity == "normal":
        # Return None -> no actions required, we're in the 'Dead Zone'
        return None
    
    return None

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        report = payload.get("anomalies", {})

        if not report:
            return

        actions = []

        for cluster_id, containers in report.items():
            for container_name, metrics in containers.items():
                for metric_name, data in metrics.items():
                    severity = data["severity"]
                    action = decide_action(metric_name, severity)
                    
                    # If action is None ('normal' case) the list remains empty
                    if action:
                        actions.append({
                            "cluster": int(cluster_id) if cluster_id.isdigit() else cluster_id,
                            "container": container_name,
                            "metric": metric_name,
                            "action": action,
                            "severity": severity,
                            "value": data["value"],
                            "threshold": data["threshold"]
                        })

        if actions:
            print(f"[Planner] Decisions made: {len(actions)} actions queued")
            client.publish(
                OUTPUT_TOPIC,
                json.dumps({
                    "timestamp": time.time(),
                    "actions": actions
                })
            )
            llm_service.send_to_llm(actions) 
        else:
            # If the list is empty (because all the metrics are 'normal') the system doesn't publish anything to MQTT nor to the LLM
            print("[Planner] System status: NORMAL. No actions required.")

    except Exception as e:
        print(f"[Planner] Error processing message: {e}")

# MQTT and Ollama Setup
while True:
    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(INPUT_TOPIC)
        client.on_message = on_message
        client.loop_start()
        print("[Planner] MQTT ready")
        break
    except Exception as e:
        print(f"[Planner] MQTT not ready: {e}")
        time.sleep(2)

payload_ping = {"model": MODEL_NAME, "prompt": "ping", "stream": False}
while True:
    try:
        r = requests.post(MODEL_URL, json=payload_ping, timeout=120)
        r.raise_for_status()
        print("[Planner] Ollama ready")
        break
    except Exception as e:
        print(f"[Planner] Ollama not ready: {e}")
        time.sleep(5)

print("[Planner] Started and waiting for reports...")
while True:
    time.sleep(1)