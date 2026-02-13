import os
import time
import json
import configparser
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

# Environment Variables
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = "AIops/analyzer"

INFLUX_URL = os.environ.get("INFLUXDB_URL")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUX_ORG = os.environ.get("INFLUXDB_ORG")
INFLUX_BUCKET = os.environ.get("INFLUXDB_BUCKET")

ANALYZER_INTERVAL = int(config["general"]["analyzer_interval"])

# Dynamic Configuration Loading from the config.ini file
METRIC_RULES = {} 

try:
    enabled_metrics_str = config["general"]["metrics"]
    enabled_metrics = [m.strip() for m in enabled_metrics_str.split(",")]
    
    for metric in enabled_metrics:
        section_name = f"metric_{metric}"
        if config.has_section(section_name):
            threshold = config[section_name].get("threshold")
            if threshold:
                METRIC_RULES[metric] = float(threshold)
                print(f"[Config] Loaded rule for '{metric}': threshold > {threshold}")
            else:
                print(f"[Config] Warning: No threshold defined for '{metric}'")

except Exception as e:
    print(f"[Config] Error loading metric rules: {e}")


def collect_metrics(query_api) -> dict:
    """
    Queries InfluxDB to get the latest values for all metrics
    returns a dictionary: {cluster: {container: {metric: value}}}
    """
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
                metric_name = record.values.get("metric")
                
                # Fallback: if metric_name doesn't exist as a tag, try to parse it from the topic
                if not metric_name and "topic" in record.values:
                    # Topic format: AIops/metrics/cluster_X/container_Y/METRIC_NAME
                    topic_parts = record["topic"].split("/")
                    metric_name = topic_parts[-1]

                value = record.get_value()

                if metric_name and value is not None:
                    metrics.setdefault(cluster, {})
                    metrics[cluster].setdefault(container, {})
                    metrics[cluster][container][metric_name] = value

    except Exception as e:
        print(f"[Analyzer] Error querying InfluxDB: {e}")

    return metrics


def evaluate_metrics(metrics: dict) -> dict:
    """
    Evaluates the collected metrics with the dynamically loaded rules from the config.ini file
    """
    anomalies = {}

    for cluster, containers in metrics.items():
        for container, container_metrics in containers.items():
            
            container_anomalies = {}

            for metric_name, value in container_metrics.items():
                if metric_name in METRIC_RULES:
                    threshold = METRIC_RULES[metric_name]
                    if value > threshold:
                        container_anomalies[metric_name] = {
                            "value": value,
                            "threshold": threshold,
                            "severity": "critical" if value > threshold * 1.5 else "warning"
                        }

            if container_anomalies:
                anomalies.setdefault(cluster, {})
                anomalies[cluster][container] = container_anomalies

    return anomalies


# Connection Setup
# 1. MQTT
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

# 2. InfluxDB
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


# Main Loop
print(f"[Analyzer] Started monitoring. Interval: {ANALYZER_INTERVAL}s")

while True:
    current_metrics = collect_metrics(query_api)
    if not current_metrics:
        print("[Analyzer] No metrics found in InfluxDB recently.")
    else:
        anomalies = evaluate_metrics(current_metrics)
        
        if anomalies:
            print(f"[Analyzer] Anomalies Detected: {json.dumps(anomalies)}")
            mqtt_client.publish(
                MQTT_TOPIC,
                json.dumps({
                    "timestamp": time.time(),
                    "anomalies": anomalies
                })
            )
        else:
            print("[Analyzer] System Healthy (No anomalies)")

    time.sleep(ANALYZER_INTERVAL)