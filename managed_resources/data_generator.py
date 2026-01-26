import time
import json
import os
import configparser
import paho.mqtt.client as mqtt
from webapp import Cluster, Container

CONFIG_FILE = "config.ini"

# Config parsing
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
print("===========================================\n")

# MQTT Setup
client = mqtt.Client()

while True:
    try:
        client.connect(BROKER, PORT, 60)
        break
    except:
        print("Waiting for Mosquitto broker...")
        time.sleep(3)

client.loop_start()
print("Simulation started...")

# Main loop
import time
import json

PUBLISH_INTERVAL = 30  # seconds

while True:
    timestamp = time.time()

    # Update all clusters states
    for cluster in clusters.values():
        cluster.update_state()

    # Publish metrics
    for cluster in clusters.values():
        for container in cluster.containers:
            topic_base = (
                f"AIops/metrics/cluster_{cluster.cluster_id}/"
                f"container_{container.name}/"
            )

            metrics = {
                "cpu": round(container.cpu_usage, 2),
                "memory": round(container.memory_usage, 2),
                "latency": round(container.latency, 2),
                "rps": container.requests_per_second,
            }

            for metric, value in metrics.items():
                payload = {
                    "timestamp": timestamp,
                    "value": value
                }
                client.publish(topic_base + metric, json.dumps(payload))

    # Sleep
    time.sleep(PUBLISH_INTERVAL)