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

def decide_action(metric, value, threshold):
    ratio = (value - threshold) / threshold

    match metric:

        case "cpu":
            if ratio > 0.5:
                return "restart", "critical"
            elif ratio > 0.2:
                return "scale_up", "warning"
            
        case "memory":
            if ratio > 0.5:
                return "restart", "critical"
            elif ratio > 0.2:
                return "scale_up", "warning"

        case "service_time":
            if ratio > 0.3:
                return "restart", "critical"
            elif ratio > 0.1:
                return "scale_up", "warning"

        case "instances":
            if value > threshold:
                return "scale_down", "warning"

        case _:
            # unrecognized metric
            return None, None

    return None, None


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        anomalies = payload.get("anomalies", {})

        if not anomalies:
            print("[Planner] No anomalies in message")
            return

        actions = []

        for cluster, containers in anomalies.items():
            for container, metrics in containers.items():
                for metric, data in metrics.items():
                    value = data["value"]
                    threshold = data["threshold"]

                    action, severity = decide_action(metric, value, threshold)
                    if action:
                        actions.append({
                            "cluster": cluster,
                            "container": container,
                            "metric": metric,
                            "action": action,
                            "severity": severity,
                            "value": value,
                            "threshold": threshold
                        })

        if actions:
            print("[Planner] Actions decided:", actions)
            client.publish(
                OUTPUT_TOPIC,
                json.dumps({
                    "timestamp": time.time(),
                    "actions": actions
                })
            )
            llm_service.send_to_llm(actions) 
            print("[Planner] Prompt to LLM Sent")
        else:
            print("[Planner] No actions required")
            # --- MODIFICA QUI: COMMENTA QUESTO BLOCCO ---
            # Se pubblichi questo, sovrascrivi l'analisi precedente nel DB!
            # client.publish(
            #     llm_service.PLANNER_LLM_TOPIC,
            #     json.dumps({
            #         "timestamp": time.time(),
            #         "response": "No actions required in the monitored containers."
            #     })
            # )

    except Exception as e:
        print(f"[Planner] Error processing message: {e}")


# MQTT setup
while True:
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(INPUT_TOPIC)
        client.on_message = on_message
        client.loop_start()
        print("[Planner] MQTT ready")
        break
    except Exception as e:
        print(f"[Planner] MQTT not ready: {e}")
        time.sleep(2)

# Waiting for Ollama
payload = {
        "model": OLLAMA_MODEL,
        "prompt": "ping",
        "stream": False
    }

while True:
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
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