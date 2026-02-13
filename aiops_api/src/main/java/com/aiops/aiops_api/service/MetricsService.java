package com.aiops.aiops_api.service;

import com.influxdb.client.InfluxDBClient;
import com.influxdb.query.FluxRecord;
import com.influxdb.query.FluxTable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class MetricsService {

    @Autowired
    private InfluxDBClient influxDBClient;

    @Value("${influx.bucket}")
    private String bucket;

    // QUERY 1: Real-time Metrics (DYNAMIC & DATA-DRIVEN)
    public List<Map<String, Object>> getLiveMetrics() {
        String query = String.format("""
            from(bucket: "%s")
              |> range(start: -5m)
              |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
              |> filter(fn: (r) => r["_field"] == "value")
              |> last()
              // We keep only the essential columns
              |> keep(columns: ["cluster", "container", "metric", "_value"])
              // Pivot: transforms the values of the "metric" column into new columns(es. cpu, memory, gpu)
              |> pivot(rowKey:["cluster", "container"], columnKey: ["metric"], valueColumn: "_value")
            """, bucket);

        List<FluxTable> tables = influxDBClient.getQueryApi().query(query);
        List<Map<String, Object>> results = new ArrayList<>();

        for (FluxTable table : tables) {
            for (FluxRecord record : table.getRecords()) {
                Map<String, Object> data = new HashMap<>();

                // DYNAMIC LOGIC
                // We cycle on all the columns that the query gives us, we don't care about their name
                Map<String, Object> values = record.getValues();

                for (Map.Entry<String, Object> entry : values.entrySet()) {
                    String key = entry.getKey();
                    Object val = entry.getValue();

                    // We filter the internal InfluxDB columns which we don't need for the frontend
                    // _start, _stop, _time, result, table are metadata from the Flux query
                    if (!key.startsWith("_") && !key.equals("result") && !key.equals("table")) {
                        
                        // null safety: if a value is null, we put 0.0
                        if (val == null && !key.equals("cluster") && !key.equals("container")) {
                             data.put(key, 0.0);
                        } else {
                             data.put(key, val);
                        }
                    }
                }
                
                results.add(data);
            }
        }
        return results;
    }

    // QUERY 2: LLM Analysis - PLANNER
    public String getLatestLlmPlanner() {
        String query = String.format("""
            from(bucket: "%s")
              |> range(start: -24h)
              |> filter(fn: (r) => r["_measurement"] == "llm_planner")
              |> filter(fn: (r) => r["_field"] == "response")
              |> last()
            """, bucket);

        List<FluxTable> tables = influxDBClient.getQueryApi().query(query);
        if (!tables.isEmpty() && !tables.get(0).getRecords().isEmpty()) {
            Object val = tables.get(0).getRecords().get(0).getValue();
            return val != null ? val.toString() : "No data.";
        }
        return "Waiting for LLM analysis...";
    }
}