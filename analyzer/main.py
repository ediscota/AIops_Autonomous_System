import time
import json
import requests
import configparser
import llm_service
import paho.mqtt.client as mqtt

from influxdb_client import InfluxDBClient

# Config parsing
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

MQTT_TOPIC = "AIops/analyzer"
LOOP_INTERVAL = 20 # seconds

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

def evaluate_metrics(metrics: dict) -> dict:
    anomalies = {}

    for cluster, containers in metrics.items():
        for container, values in containers.items():

            container_anomalies = {}

            cpu = values.get("cpu")
            if cpu is not None and cpu > CPU_THRESHOLD:
                container_anomalies["cpu"] = {
                    "value": cpu,
                    "threshold": CPU_THRESHOLD,
                }

            memory = values.get("memory")
            if memory is not None and memory > MEMORY_THRESHOLD:
                container_anomalies["memory"] = {
                    "value": memory,
                    "threshold": MEMORY_THRESHOLD,
                }

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

# Waiting for MQTT
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

# Waiting for InfluxDB
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

# Waiting for Ollama
payload = {
        "model": OLLAMA_MODEL,
        "prompt": "ping",
        "stream": False
    }

while True:
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        print("[Analyzer] Ollama ready")
        break
    except Exception as e:
        print(f"[Analyzer] Ollama not ready: {e}")
        time.sleep(5)

print("[Analyzer] Started")

# Main loop
while True:
    metrics = collect_metrics(query_api)

    if not metrics:
        print("[Analyzer] No metrics found")
        time.sleep(LOOP_INTERVAL)
        continue

    anomalies = evaluate_metrics(metrics)

    if anomalies:
        print("[Analyzer] Anomalies detected")
        print(anomalies)
        mqtt_client.publish(
            MQTT_TOPIC,
            json.dumps({
                "timestamp": time.time(),
                "anomalies": anomalies
            })
        )
    else:
        print("[Analyzer] No anomalies detected")

    time.sleep(LOOP_INTERVAL)