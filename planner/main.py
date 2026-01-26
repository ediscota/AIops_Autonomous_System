import json
import time
import llm_service
import paho.mqtt.client as mqtt

# Config
MQTT_BROKER = "mosquitto"
INPUT_TOPIC = "AIops/analyzer"
OUTPUT_TOPIC = "AIops/planner"

# Secure callback
def on_message(client, userdata, msg):
    try:
        payload_raw = msg.payload.decode()
        if not payload_raw:
            print("[Planner] Empty payload received, skipping")
            return

        print(f"[Planner] Raw message received: {payload_raw}")

        payload = json.loads(payload_raw)
        anomalies = payload.get("response")
        if not anomalies:
            print("[Planner] No anomalies in payload, skipping")
            return

        plan = llm_service.send_to_llm(json.dumps(anomalies, indent=2))
        if not plan:
            print("[Planner] LLM returned no plan, skipping")
            return

        print("[Planner] Publishing plan")
        client.publish(
            OUTPUT_TOPIC,
            json.dumps({"plan": plan})
        )

    except json.JSONDecodeError:
        print("[Planner] Received malformed JSON, skipping")
    except Exception as e:
        print(f"[Planner] Unexpected error: {e}")

# MQTT Setup with retry
mqtt_client = mqtt.Client()
connected = False
while not connected:
    try:
        mqtt_client.connect(MQTT_BROKER, 1883, 60)
        mqtt_client.loop_start()
        connected = True
    except Exception as e:
        print(f"[Planner] Waiting for MQTT broker... ({e})")
        time.sleep(2)

mqtt_client.subscribe(INPUT_TOPIC)
mqtt_client.on_message = on_message

print("[Planner] Waiting for anomalies...")

# Main loop
# With loop_forever(), the clients keeps on listening and the callback takes care of all messages
while True:
    time.sleep(1)  # keeps the main thread alivo, loop_forever is handled by the internal thread