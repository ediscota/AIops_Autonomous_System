import time
import json
import configparser
import paho.mqtt.client as mqtt
from webapp import Cluster, Container

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

NUM_CONTAINERS = int(config["general"]["num_containers"])
NUM_CLUSTERS = int(config["general"]["num_clusters"])

# Create the containers
containers = []
for i in range(NUM_CONTAINERS):
    section = f"container_{i}"
    name = config[section]["name"]
    cluster_id = int(config[section]["cluster"])
    containers.append(Container(name, cluster_id))

# Group containers by cluster
clusters = {}
for cid in range(NUM_CLUSTERS):
    clusters[cid] = Cluster(
        cluster_id=cid,
        containers=[c for c in containers if c.cluster_id == cid]
    )

print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"Number of clusters: {NUM_CLUSTERS}")
print(f"Number of containers: {NUM_CONTAINERS}")

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

# Waiting for MQTT
while True:
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("[Managed Resources] MQTT ready")
        break
    except Exception as e:
        print(f"[Managed Resources] MQTT not ready: {e}")
        time.sleep(2)

print("[Managed Resources] Started")
# Main loop
PUBLISH_INTERVAL = 30  # seconds

while True:
    # Update all clusters states
    for cluster in clusters.values():
        cluster.update_state()

    timestamp = time.time()

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