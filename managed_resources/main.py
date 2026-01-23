import time
import json
import os
import configparser
import paho.mqtt.client as mqtt
from webapp import Cluster, Container

CONFIG_FILE = "config.ini"

# MQTT topics
TOPIC_METRICS = "sensors/metrics"
TOPIC_LOGS = "sensors/logs"
TOPIC_ACTIONS = "effectors/actions"

# --------------------
# CONFIG PARSING
# --------------------
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

BROKER = config["mqtt"]["client_address"]
PORT = int(config["mqtt"]["port"])

num_containers = int(config["general"]["num_containers"])
num_clusters = int(config["general"]["num_clusters"])

# Create containers
containers = []
for i in range(num_containers):
    section = f"container_{i}"
    name = config[section]["name"]
    cluster_id = int(config[section]["cluster"])
    containers.append(Container(name, cluster_id))

# Group containers by cluster
clusters = {}
for cid in range(num_clusters):
    clusters[cid] = Cluster(
        cluster_id=cid,
        containers=[c for c in containers if c.cluster_id == cid]
    )

print("\n========== DEBUG CONFIGURATION ==========")
print(f"MQTT Broker: {BROKER}:{PORT}")
print(f"Num clusters: {num_clusters}")
print(f"Num containers: {num_containers}")

print("\n--- Containers ---")
for c in containers:
    print(f"Container name={c.name}, cluster={c.cluster_id}, status={c.status}")

print("\n--- Clusters ---")
for cid, cluster in clusters.items():
    print(f"Cluster {cid}:")
    if not cluster.containers:
        print("No containers in this cluster!")
    for c in cluster.containers:
        print(f"  - {c.name}")

print("========================================\n")

# --------------------
# MQTT CALLBACKS
# --------------------
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC_ACTIONS)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received Command: {payload}")

        # Try action on all clusters
        for cluster in clusters.values():
            if cluster.execute_action(payload):
                break

    except Exception as e:
        print(f"Error processing message: {e}")

# --------------------
# MQTT SETUP
# --------------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

while True:
    try:
        client.connect(BROKER, PORT, 60)
        break
    except:
        print("Waiting for Mosquitto broker...")
        time.sleep(3)

client.loop_start()
print("Simulation started...")

# --------------------
# MAIN LOOP
# --------------------
while True:
    all_metrics = []

    for cluster in clusters.values():
        cluster.update_state()
        metrics = cluster.get_metrics()
        all_metrics.extend(metrics)

    client.publish(TOPIC_METRICS, json.dumps(all_metrics))

    for m in all_metrics:
        if m["cpu"] > 80:
            client.publish(TOPIC_LOGS, json.dumps({
                "container": m["container"],
                "cluster": m["cluster"],
                "level": "ERROR",
                "message": "High CPU load detected",
                "timestamp": time.time()
            }))
        elif m["status"] == "CRASHED":
            client.publish(TOPIC_LOGS, json.dumps({
                "container": m["container"],
                "cluster": m["cluster"],
                "level": "CRITICAL",
                "message": "Service unreachable",
                "timestamp": time.time()
            }))

    time.sleep(5)