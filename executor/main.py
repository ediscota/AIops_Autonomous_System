import os
import time
import json
import paho.mqtt.client as mqtt

# Config parsing
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

PLANNER_TOPIC = "AIops/planner"
EXECUTE_TOPIC = "AIops/execute"

# Helper functions
def parse_cluster_id(cluster_str: str) -> int:
    # 'cluster_0' -> 0
    if isinstance(cluster_str, str) and cluster_str.startswith("cluster_"):
        return int(cluster_str.split("_")[1])
    return int(cluster_str)

def parse_container_name(container_str: str) -> str:
    # 'container_auth-service' -> 'auth-service'
    if isinstance(container_str, str) and container_str.startswith("container_"):
        return container_str.replace("container_", "", 1)
    return container_str

# MQTT callback
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        actions = payload.get("actions", [])

        if not actions:
            print("[Executor] No actions received")
            return

        for action in actions:
            # Normalization
            cluster_id = parse_cluster_id(action["cluster"])
            container_name = parse_container_name(action["container"])

            command = {
                "timestamp": time.time(),
                "cluster": cluster_id,        # int id ready
                "container": container_name,  # name without the prefix "container_"
                "action": action["action"],
                "metric": action.get("metric"),
                "severity": action.get("severity", "warning")
            }

            client.publish(EXECUTE_TOPIC, json.dumps(command))

            print(f"[Executor] Published command: {command}")

    except Exception as e:
        print(f"[Executor] Error processing message: {e}")

# Main
if __name__ == "__main__":
    while True:
        try:
            client = mqtt.Client()
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.subscribe(PLANNER_TOPIC)
            client.on_message = on_message
            client.loop_start()
            print("[Executor] MQTT ready")
            break
        except Exception as e:
            print(f"[Executor] MQTT not ready: {e}")
            time.sleep(2)

    print("[Executor] Started")

    while True:
        time.sleep(1)