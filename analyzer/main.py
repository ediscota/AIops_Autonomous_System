import time
import json
import requests
import configparser
import llm_service
import paho.mqtt.client as mqtt
import csv
import os

from influxdb_client import InfluxDBClient

# =======================
# Config parsing
# =======================
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

INFLUX_URL = config["influx"]["url"]
INFLUX_TOKEN = config["influx"]["token"]
INFLUX_ORG = config["influx"]["org"]
INFLUX_BUCKET = config["influx"]["bucket"]

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]

CPU_THRESHOLD = float(config["analyzer"]["cpu_threshold"])
MEMORY_THRESHOLD = int(config["analyzer"]["memory_threshold"])
SERVICE_TIME_THRESHOLD = int(config["analyzer"]["service_time_threshold"])
INSTANCES_THRESHOLD = int(config["analyzer"]["instances_threshold"])

RECORD_CSV = config["analyzer"].getboolean("record_csv", fallback=True)

MQTT_TOPIC = "AIops/analyzer"
LOOP_INTERVAL = 20  # seconds

CSV_FILE = "analyzer_dataset.csv"
CSV_HEADERS = [
    "timestamp",
    "cluster",
    "container",
    "cpu",
    "memory",
    "service_time",
    "instances",
    "anomaly_detected",
    "cpu_anomaly",
    "memory_anomaly",
    "service_time_anomaly",
    "instances_anomaly",
]

# =======================
# CSV Handling
# =======================
def init_csv():
    if not RECORD_CSV:
        print("[Analyzer] CSV recording disabled")
        return

    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
        print("[Analyzer] Previous CSV deleted")

    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

    print("[Analyzer] CSV recording enabled (fresh file)")


def save_to_csv(timestamp, metrics, anomalies):
    if not RECORD_CSV:
        return

    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)

        for cluster, containers in metrics.items():
            for container, values in containers.items():

                container_anomalies = anomalies.get(cluster, {}).get(container, {})

                writer.writerow([
                    timestamp,
                    cluster,
                    container,
                    values.get("cpu"),
                    values.get("memory"),
                    values.get("service_time"),
                    values.get("instances"),
                    int(bool(container_anomalies)),
                    int("cpu" in container_anomalies),
                    int("memory" in container_anomalies),
                    int("service_time" in container_anomalies),
                    int("instances" in container_anomalies),
                ])

# =======================
# Metrics Collection
# =======================
def collect_metrics(query_api) -> dict:
    metrics = {}

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
    |> range(start: -1m)
    |> filter(fn: (r) =>
        r._measurement == "mqtt_consumer" and
        r._field == "value"
    )
    |> last()
    '''

    try:
        tables = query_api.query(query)
        for table in tables:
            for record in table.records:
                cluster = record["cluster"]
                container = record["container"]
                metric = record["metric"]
                value = record.get_value()

                metrics.setdefault(cluster, {})
                metrics[cluster].setdefault(container, {})
                metrics[cluster][container][metric] = value

    except Exception as e:
        print(f"[Analyzer] Error querying InfluxDB: {e}")

    return metrics

# =======================
# Anomaly Evaluation
# =======================
def evaluate_metrics(metrics: dict) -> dict:
    anomalies = {}

    for cluster, containers in metrics.items():
        for container, values in containers.items():

            container_anomalies = {}

            cpu = values.get("cpu")
            if cpu is not None and cpu > CPU_THRESHOLD:
                container_anomalies["cpu"] = {"value": cpu, "threshold": CPU_THRESHOLD}

            memory = values.get("memory")
            if memory is not None and memory > MEMORY_THRESHOLD:
                container_anomalies["memory"] = {"value": memory, "threshold": MEMORY_THRESHOLD}

            service_time = values.get("service_time")
            if service_time is not None and service_time > SERVICE_TIME_THRESHOLD:
                container_anomalies["service_time"] = {
                    "value": service_time,
                    "threshold": SERVICE_TIME_THRESHOLD,
                }

            instances = values.get("instances")
            if instances is not None and instances > INSTANCES_THRESHOLD:
                container_anomalies["instances"] = {
                    "value": instances,
                    "threshold": INSTANCES_THRESHOLD,
                }

            if container_anomalies:
                anomalies.setdefault(cluster, {})
                anomalies[cluster][container] = container_anomalies

    return anomalies

# =======================
# Waiting for MQTT
# =======================
while True:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("[Analyzer] MQTT ready")
        break
    except Exception as e:
        print(f"[Analyzer] MQTT not ready: {e}")
        time.sleep(2)

# =======================
# Waiting for InfluxDB
# =======================
while True:
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        health = influx_client.health()
        if health.status == "pass":
            query_api = influx_client.query_api()
            print("[Analyzer] InfluxDB ready")
            break
        else:
            raise Exception(health.message)
    except Exception as e:
        print(f"[Analyzer] InfluxDB not ready: {e}")
        time.sleep(3)

# =======================
# Waiting for Ollama
# =======================
payload = {"model": OLLAMA_MODEL, "prompt": "ping", "stream": False}

while True:
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        print("[Analyzer] Ollama ready")
        break
    except Exception as e:
        print(f"[Analyzer] Ollama not ready: {e}")
        time.sleep(5)

# =======================
# Start Analyzer
# =======================
init_csv()
print("[Analyzer] Started")

# =======================
# Main loop
# =======================
while True:
    metrics = collect_metrics(query_api)

    if not metrics:
        print("[Analyzer] No metrics found")
        time.sleep(LOOP_INTERVAL)
        continue

    anomalies = evaluate_metrics(metrics)
    timestamp = time.time()

    save_to_csv(timestamp, metrics, anomalies)

    if anomalies:
        print("[Analyzer] Anomalies detected")
        print(anomalies)

        mqtt_client.publish(
            MQTT_TOPIC,
            json.dumps({"timestamp": timestamp, "anomalies": anomalies})
        )

        llm_service.send_to_llm(anomalies)
        print("[Analyzer] Prompt to LLM Sent")

    else:
        print("[Analyzer] No anomalies detected")
        mqtt_client.publish(
            llm_service.ANALYZER_LLM_TOPIC,
            json.dumps({
                "timestamp": timestamp,
                "response": "No anomalies detected in the monitored containers."
            })
        )

    time.sleep(LOOP_INTERVAL)
