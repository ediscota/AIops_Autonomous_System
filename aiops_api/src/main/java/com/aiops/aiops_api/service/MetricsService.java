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

    // QUERY 1: Metriche Real-time (FIXED FINAL)
    public List<Map<String, Object>> getLiveMetrics() {
        String query = String.format("""
            from(bucket: "%s")
              |> range(start: -5m)
              |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
              |> filter(fn: (r) => r["_field"] == "value")
              |> last()
              // *** FIX: Manteniamo SOLO queste colonne. ***
              // Questo elimina automaticamente 'topic', 'host', '_time' e qualsiasi altra 
              // colonna che impediva l'unione dei dati.
              |> keep(columns: ["cluster", "container", "metric", "_value"])
              |> pivot(rowKey:["cluster", "container"], columnKey: ["metric"], valueColumn: "_value")
            """, bucket);

        List<FluxTable> tables = influxDBClient.getQueryApi().query(query);
        List<Map<String, Object>> results = new ArrayList<>();

        for (FluxTable table : tables) {
            for (FluxRecord record : table.getRecords()) {
                Map<String, Object> data = new HashMap<>();
                
                data.put("cluster", record.getValueByKey("cluster"));
                data.put("container", record.getValueByKey("container"));
                
                // Ora i dati saranno sicuramente sulla stessa riga
                data.put("cpu", record.getValueByKey("cpu") != null ? record.getValueByKey("cpu") : 0.0);
                data.put("memory", record.getValueByKey("memory") != null ? record.getValueByKey("memory") : 0.0);
                data.put("service_time", record.getValueByKey("service_time") != null ? record.getValueByKey("service_time") : 0.0);
                data.put("instances", record.getValueByKey("instances") != null ? record.getValueByKey("instances") : 0.0);
                
                
                results.add(data);
            }
        }
        return results;
    }

    // QUERY 2: Analisi LLM - Analyzer
    public String getLatestLlmAnalysis() {
        String query = String.format("""
            from(bucket: "%s")
              |> range(start: -24h)
              |> filter(fn: (r) => r["_measurement"] == "llm_analysis")
              |> filter(fn: (r) => r["_field"] == "response")
              |> last()
            """, bucket);

        List<FluxTable> tables = influxDBClient.getQueryApi().query(query);
        if (!tables.isEmpty() && !tables.get(0).getRecords().isEmpty()) {
            Object val = tables.get(0).getRecords().get(0).getValue();
            return val != null ? val.toString() : "Nessun dato.";
        }
        return "Waiting for LLM analysis...";
    }

    // QUERY 2: Analisi LLM - PLANNER
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
            return val != null ? val.toString() : "Nessun dato.";
        }
        return "Waiting for LLM analysis...";
    }
}