import time
from influxdb_client import InfluxDBClient

INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "my-super-secret-admin-token"
INFLUX_ORG = "AIops_org"
INFLUX_BUCKET = "AIops_bucket"

CPU_THRESHOLD = 5.0 # TODO
MEMORY_THRESHOLD = 5.0 # TODO
LATENCY_THRESHOLD = 5.0 # TODO
ANALYSIS_INTERVAL = 5 # seconds

class Analyzer:
    def __init__(self):
        while True:
            try:
                self.client = InfluxDBClient(
                    url=INFLUX_URL,
                    token=INFLUX_TOKEN,
                    org=INFLUX_ORG
                )
                self.query_api = self.client.query_api()

                print("[Analyzer] Connected to InfluxDB")
                break

            except Exception as e:
                print(f"[Analyzer] Waiting for InfluxDB... ({e})")
                time.sleep(5)

    def analyze_metrics(self):
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

        tables = self.query_api.query(query)

        if not tables:
            print("[Analyzer] No data returned")
            return

        for table in tables:
            for record in table.records:
                metric = record["metric"]
                value = record.get_value()
                cluster = record["cluster"]
                container = record["container"]

                print(
                    f"cluster={cluster} "
                    f"container={container} "
                    f"{metric}={value}"
                )

    def run(self):
        while True:
            self.analyze_metrics()
            time.sleep(ANALYSIS_INTERVAL)


if __name__ == "__main__":
    Analyzer().run()