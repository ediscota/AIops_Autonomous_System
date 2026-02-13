import os
import time
import json
import configparser
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

INFLUX_URL = os.environ.get("INFLUXDB_URL")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUX_ORG = os.environ.get("INFLUXDB_ORG")
INFLUX_BUCKET = os.environ.get("INFLUXDB_BUCKET")

CPU_THRESHOLD = float(config["analyzer"]["cpu_threshold"])
MEMORY_THRESHOLD = int(config["analyzer"]["memory_threshold"])
SERVICE_TIME_THRESHOLD = int(config["analyzer"]["service_time_threshold"])
INSTANCES_THRESHOLD = int(config["analyzer"]["instances_threshold"])

MQTT_TOPIC = "AIops/analyzer"
ANALYZER_INTERVAL = int(config["general"]["analyzer_interval"])

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

print("[Analyzer] Started")

# Main loop
while True:
    metrics = collect_metrics(query_api)

    if not metrics:
        print("[Analyzer] No metrics found")
        time.sleep(ANALYZER_INTERVAL)
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

    time.sleep(ANALYZER_INTERVAL)