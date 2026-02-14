import os
import time
import json
import configparser
import paho.mqtt.client as mqtt

from queue import Queue
from webapp import Cluster, Container

# Config parsing - DISABLED INTERPOLATION
# This prevents InterpolationSyntaxError when the '%' character is used in 'unit'
config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_GENERATOR_USER")
MQTT_PASSWORD = os.getenv("MQTT_GENERATOR_PASSWORD")

NUM_CONTAINERS = int(config["general"]["num_containers"])
NUM_CLUSTERS = int(config["general"]["num_clusters"])

PUBLISH_INTERVAL = int(config["general"]["publish_interval"])
EXECUTE_TOPIC = "AIops/execute"

# Dynamic Metrics Configuration Loading 
try:
    enabled_metrics_str = config["general"]["metrics"]
    ENABLED_METRICS = [m.strip() for m in enabled_metrics_str.split(",")]
except KeyError:
    print("[Warning] 'metrics' not found in [general]. Using defaults.")
    ENABLED_METRICS = ["cpu", "memory", "service_time"]

METRIC_CONFIGS = {}

for metric in ENABLED_METRICS:
    section_name = f"metric_{metric}"
    if config.has_section(section_name):
        # 1. Load all keys from the section as a dictionary
        raw_config = dict(config[section_name])
        
        # 2. Remove UI/Planner metadata to prevent interference with math
        # We pop everything that is NOT a numeric simulation parameter
        raw_config.pop("unit", None) 

        # 3. Convert remaining parameters to float for mathematical calculations
        processed_config = {}
        for key, value in raw_config.items():
            try:
                processed_config[key] = float(value)
            except ValueError:
                # Fallback for unexpected strings
                processed_config[key] = value 
        
        METRIC_CONFIGS[metric] = processed_config
    else:
        print(f"[Warning] Configuration section [{section_name}] not found. Using defaults.")
        METRIC_CONFIGS[metric] = {
            'initial': 0.0, 'min': 0.0, 'max': 100.0, 'noise': 0.0, 
            'scale_up_delta': 0.0, 'scale_down_delta': 0.0
        }

# Simulation state initialization
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

# MQTT callback (handles incoming commands from the AI/Dashboard)
def on_execute_message(client, userdata, msg):
    try:
        command = json.loads(msg.payload.decode())
        execute_queue.put(command)
        print(f"[Managed Resources] Queued command: {command}")
    except Exception as e:
        print(f"[Managed Resources] Error queuing command: {e}")

# MQTT connection setup with retry logic
while True:
    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
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

# Main simulation loop
while True:
    # 1. Process received commands (Scaling, Healing, etc.)
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
            "container": container_name
        }

        executed = cluster.execute_action(action_payload)

        if executed:
            print(f"[Managed Resources] Executed: {action_payload}")
            # Immediate publish after state change to improve UI responsiveness
            container = next((c for c in cluster.containers if c.name == container_name), None)
            if container:
                timestamp = time.time()
                topic_base = f"AIops/metrics/cluster_{cluster.cluster_id}/container_{container.name}/"
                for metric_name, value in container.metrics.items():
                    payload = {"timestamp": timestamp, "value": round(float(value), 2)}
                    client.publish(topic_base + metric_name, json.dumps(payload))
        else:
            print(f"[Managed Resources] Action failed: {action_payload}")

    # 2. Update all containers metrics
    for cluster in clusters.values():
        cluster.update_state()

    # 3. Periodic telemetry publishing via MQTT
    timestamp = time.time()
    for cluster in clusters.values():
        for container in cluster.containers:
            topic_base = f"AIops/metrics/cluster_{cluster.cluster_id}/container_{container.name}/"
            for metric_name, value in container.metrics.items():
                payload = {"timestamp": timestamp, "value": round(float(value), 2)}
                client.publish(topic_base + metric_name, json.dumps(payload))

    time.sleep(PUBLISH_INTERVAL)