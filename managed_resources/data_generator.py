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

PUBLISH_INTERVAL = 20  # seconds
EXECUTE_TOPIC = "AIops/execute"

# Create containers and clusters
containers = []
for i in range(NUM_CONTAINERS):
    section = f"container_{i}"
    name = config[section]["name"]
    cluster_id = int(config[section]["cluster"])
    containers.append(Container(name, cluster_id))

clusters = {}
for cid in range(NUM_CLUSTERS):
    clusters[cid] = Cluster(
        cluster_id=cid,
        containers=[c for c in containers if c.cluster_id == cid]
    )

# MQTT callback
def on_execute_message(client, userdata, msg):
    # Executes the commands given by the executor
    try:
        command = json.loads(msg.payload.decode())
        cluster_id = command["cluster"]
        container_name = command["container"]

        cluster = clusters.get(cluster_id)
        if cluster:
            action_payload = {
                "action": command["action"],
                "container": container_name,
                "metric": command.get("metric"),
                "severity": command.get("severity", "warning")
            }
            cluster.execute_action(action_payload)
            print(f"[Managed Resources] Executed command: {action_payload}")
        else:
            print(f"[Managed Resources] Cluster {cluster_id} not found")
    except Exception as e:
        print(f"[Managed Resources] Error executing command: {e}")

# MQTT setup + subscribe
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

# Main loop
while True:
    # Update container state
    for cluster in clusters.values():
        cluster.update_state()

    timestamp = time.time()

    # Publish metrics on MQTT
    for cluster in clusters.values():
        for container in cluster.containers:
            topic_base = f"AIops/metrics/cluster_{cluster.cluster_id}/container_{container.name}/"
            metrics = {
                "cpu": round(container.cpu_usage, 2),
                "memory": round(container.memory_usage, 2),
                "service_time": round(container.service_time, 2),
                "instances": container.number_of_instances,
            }
            for metric, value in metrics.items():
                payload = {"timestamp": timestamp, "value": value}
                client.publish(topic_base + metric, json.dumps(payload))

    time.sleep(PUBLISH_INTERVAL)