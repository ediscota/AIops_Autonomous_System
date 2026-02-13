import os
import time
import json
import configparser
import paho.mqtt.client as mqtt

from queue import Queue
from webapp import Cluster, Container

# --- Config parsing ---
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

NUM_CONTAINERS = int(config["general"]["num_containers"])
NUM_CLUSTERS = int(config["general"]["num_clusters"])

PUBLISH_INTERVAL = int(config["general"]["publish_interval"])
EXECUTE_TOPIC = "AIops/execute"

# Dynamic Metric Configuration Loading 
try:
    enabled_metrics_str = config["general"]["enabled_metrics"]
    ENABLED_METRICS = [m.strip() for m in enabled_metrics_str.split(",")]
except KeyError:
    print("[Warning] 'enabled_metrics' not found in [general]. Using defaults.")
    ENABLED_METRICS = ["cpu", "memory"]

METRIC_CONFIGS = {}

for metric in ENABLED_METRICS:
    section_name = f"metric_{metric}"
    if config.has_section(section_name):
        METRIC_CONFIGS[metric] = dict(config[section_name])
    else:
        print(f"[Warning] Configuration section [{section_name}] not found. Using defaults.")
        METRIC_CONFIGS[metric] = {
            'initial': 0, 'min': 0, 'max': 100, 'noise': 0, 
            'scale_up_delta': 0, 'scale_down_delta': 0
        }

# --- Simulation state ---
containers = []
for i in range(NUM_CONTAINERS):
    section = f"container_{i}"
    name = config[section]["name"]
    cluster_id = int(config[section]["cluster"])
    containers.append(Container(name, cluster_id, METRIC_CONFIGS))

clusters = {
    cid: Cluster(
        cluster_id=cid,
        containers=[c for c in containers if c.cluster_id == cid]
    )
    for cid in range(NUM_CLUSTERS)
}

execute_queue = Queue()

# MQTT callback (NO STATE CHANGE)
def on_execute_message(client, userdata, msg):
    try:
        command = json.loads(msg.payload.decode())
        execute_queue.put(command)
        print(f"[Managed Resources] Queued command: {command}")
    except Exception as e:
        print(f"[Managed Resources] Error queuing command: {e}")

# --- MQTT setup ---
while True:
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(EXECUTE_TOPIC)
        client.message_callback_add(EXECUTE_TOPIC, on_execute_message)
        client.loop_start() 
        print("[Managed Resources] MQTT ready")
        break
    except Exception as e:
        print(f"[Managed Resources] MQTT not ready: {e}")
        time.sleep(2)

print("[Managed Resources] Started")

# --- Main simulation loop ---
while True:

    # 1. Execute pending commands
    while not execute_queue.empty():
        command = execute_queue.get()

        cluster_id = command.get("cluster")
        container_name = command.get("container")

        cluster = clusters.get(cluster_id)
        if not cluster:
            print(f"[Managed Resources] Cluster {cluster_id} not found")
            continue

        action_payload = {
            "action": command.get("action"),
            "container": container_name,
            "metric": command.get("metric"), 
            "severity": command.get("severity", "warning")
        }

        executed = cluster.execute_action(action_payload)

        if executed:
            print(f"[Managed Resources] Executed command: {action_payload}")
            container = next(
                (c for c in cluster.containers if c.name == container_name),
                None
            )

            if container:
                timestamp = time.time()
                topic_base = (
                    f"AIops/metrics/cluster_{cluster.cluster_id}/"
                    f"container_{container.name}/"
                )

                # Dynamic publishing
                for metric_name, value in container.metrics.items():
                    payload = {
                        "timestamp": timestamp, 
                        "value": round(float(value), 2)
                    }
                    client.publish(topic_base + metric_name, json.dumps(payload))
        else:
            print(f"[Managed Resources] Action failed: {action_payload}")

    # 2. Update simulation state (Tick)
    for cluster in clusters.values():
        cluster.update_state()

    # 3. Periodic metrics publish
    timestamp = time.time()
    for cluster in clusters.values():
        for container in cluster.containers:
            topic_base = (
                f"AIops/metrics/cluster_{cluster.cluster_id}/"
                f"container_{container.name}/"
            )

            # --- DYNAMIC PUBLISHING ---
            for metric_name, value in container.metrics.items():
                payload = {
                    "timestamp": timestamp, 
                    "value": round(float(value), 2)
                }
                client.publish(topic_base + metric_name, json.dumps(payload))

    time.sleep(PUBLISH_INTERVAL)