import time
import json
import os
import paho.mqtt.client as mqtt
from webapp import ClusterSimulator

# MQTT Configuration
BROKER = os.getenv("MQTT_BROKER", "mosquitto")
PORT = 1883
TOPIC_METRICS = "sensors/metrics"
TOPIC_LOGS = "sensors/logs"
TOPIC_ACTIONS = "effectors/actions"

simulator = ClusterSimulator()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC_ACTIONS)

def on_message(client, userdata, msg):
    """Handle incoming effector commands."""
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received Command: {payload}")
        simulator.execute_action(payload)
    except Exception as e:
        print(f"Error processing message: {e}")

# Setup MQTT Client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Wait for broker to be ready (rudimentary retry loop)
#cambia in data generator
while True:
    try:
        client.connect(BROKER, PORT, 60)
        break
    except:
        print("Waiting for Mosquitto broker...")
        time.sleep(3)

client.loop_start()

print("Simulation started...")

# Main Simulation Loop
while True:
    # 1. Update Simulation State
    simulator.update_state()

    # 2. Publish Metrics (Sensor)
    metrics = simulator.get_metrics()
    client.publish(TOPIC_METRICS, json.dumps(metrics))
    
    # 3. Randomly Publish Logs (Sensor)
    # Occasionally generate an error log if a service is struggling
    for service in metrics:
        if service['cpu'] > 80:
             log = {
                 "service": service['service'],
                 "level": "ERROR",
                 "message": "High CPU load detected. Potential thread starvation.",
                 "timestamp": time.time()
             }
             client.publish(TOPIC_LOGS, json.dumps(log))
        elif service['status'] == "CRASHED":
             log = {
                 "service": service['service'],
                 "level": "CRITICAL",
                 "message": "Connection refused. Service unreachable.",
                 "timestamp": time.time()
             }
             client.publish(TOPIC_LOGS, json.dumps(log))

    # Sleep to simulate ticker
    time.sleep(5)