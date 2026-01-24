import time
from influxdb_client import InfluxDBClient

INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "my-super-secret-admin-token"
INFLUX_ORG = "AIops_org"
INFLUX_BUCKET = "AIops_bucket"

ANALYSIS_INTERVAL = 5 # seconds

class Analyzer:
    def __init__(self):
        print("[Analyzer] Connecting to InfluxDB...")
        while True:
            try:
                self.client = InfluxDBClient(
                    url=INFLUX_URL,
                    token=INFLUX_TOKEN,
                    org=INFLUX_ORG
                )
                self.query_api = self.client.query_api()
                # Simple health check query
                self.client.health()
                print("[Analyzer] Connected to InfluxDB!")
                break
            except Exception as e:
                print(f"[Analyzer] Waiting for InfluxDB... ({e})")
                time.sleep(2)  # Wait before retrying

    def analyze_metrics(self):
        user_prompt = "" 

        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -1m)
        |> filter(fn: (r) =>
            r._measurement == "mqtt_consumer" and
            r._field == "value" and
            (r.metric == "cpu" or
            r.metric == "memory" or
            r.metric == "latency")
        )
        |> last()
        '''

        try:
            tables = self.query_api.query(query)

            # If Influx is ready but simply has no data yet (Telegraf buffering)
            if not tables:
                print("[Analyzer] Query executed successfully, but no data found yet (waiting for Monitor)...")
                return

            for table in tables:
                for record in table.records:
                    metric = record["metric"]
                    value = record.get_value()
                    cluster = record["cluster"]
                    container = record["container"]
                    
                    user_prompt += (
                        f"[METRIC] cluster={cluster} "
                        f"container={container} "
                        f"{metric}={value}\n"
                    )

            if user_prompt:
                print("--- Data for LLM ---")
                print(user_prompt)
                print("--------------------")

        except Exception as e:
            print(f"[Analyzer] Error during query: {e}")

    def run(self):
        print("[Analyzer] Starting analysis loop...")
        while True:
            self.analyze_metrics()
            time.sleep(ANALYSIS_INTERVAL)


if __name__ == "__main__":
    Analyzer().run()