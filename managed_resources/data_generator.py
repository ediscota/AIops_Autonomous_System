import time
import json
import configparser
import paho.mqtt.client as mqtt

from queue import Queue
from webapp import Cluster, Container

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

NUM_CONTAINERS = int(config["general"]["num_containers"])
NUM_CLUSTERS = int(config["general"]["num_clusters"])

PUBLISH_INTERVAL = 20 # seconds
EXECUTE_TOPIC = "AIops/execute"

# Simulation state
containers = []
for i in range(NUM_CONTAINERS):
    section = f"container_{i}"
    name = config[section]["name"]
    cluster_id = int(config[section]["cluster"])
    containers.append(Container(name, cluster_id))

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

# MQTT setup
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

# Main simulation loop
while True:

    # 1. Execute pending commands
    while not execute_queue.empty():
        command = execute_queue.get()

        cluster_id = command["cluster"]
        container_name = command["container"]

        cluster = clusters.get(cluster_id)
        if not cluster:
            print(f"[Managed Resources] Cluster {cluster_id} not found")
            continue

        action_payload = {
            "action": command["action"],
            "container": container_name,
            "metric": command.get("metric"),
            "severity": command.get("severity", "warning")
        }

        executed = cluster.execute_action(action_payload)

        if executed:
            print(f"[Managed Resources] Executed command: {action_payload}")

            # Publish UPDATED metrics immediately
            container = next(
                (c for c in cluster.containers if c.name == container_name),
                None
            )

            if container:
                topic_base = (
                    f"AIops/metrics/cluster_{cluster.cluster_id}/"
                    f"container_{container.name}/"
                )

                metrics = {
                    "cpu": round(container.cpu_usage, 2),
                    "memory": round(container.memory_usage, 2),
                    "service_time": round(container.service_time, 2),
                    "instances": container.number_of_instances,
                }

                timestamp = time.time()
                for metric, value in metrics.items():
                    payload = {"timestamp": timestamp, "value": value}
                    client.publish(topic_base + metric, json.dumps(payload))
        else:
            print(f"[Managed Resources] Action failed: {action_payload}")

    # 2. Update simulation state
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

            metrics = {
                "cpu": round(container.cpu_usage, 2),
                "memory": round(container.memory_usage, 2),
                "service_time": round(container.service_time, 2),
                "instances": container.number_of_instances,
                #"throughput": round(container.throughput, 2) TODO: add throughput to dashboard
            }

            for metric, value in metrics.items():
                payload = {"timestamp": timestamp, "value": value}
                client.publish(topic_base + metric, json.dumps(payload))

    time.sleep(PUBLISH_INTERVAL)