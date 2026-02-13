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

    // QUERY 1: Metriche Real-time (DYNAMIC & DATA-DRIVEN)
    public List<Map<String, Object>> getLiveMetrics() {
        String query = String.format("""
            from(bucket: "%s")
              |> range(start: -5m)
              |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
              |> filter(fn: (r) => r["_field"] == "value")
              |> last()
              // Manteniamo solo le colonne essenziali
              |> keep(columns: ["cluster", "container", "metric", "_value"])
              // Pivot: trasforma i valori della colonna "metric" in nuove colonne (es. cpu, memory, gpu)
              |> pivot(rowKey:["cluster", "container"], columnKey: ["metric"], valueColumn: "_value")
            """, bucket);

        List<FluxTable> tables = influxDBClient.getQueryApi().query(query);
        List<Map<String, Object>> results = new ArrayList<>();

        for (FluxTable table : tables) {
            for (FluxRecord record : table.getRecords()) {
                Map<String, Object> data = new HashMap<>();

                // --- LOGICA DINAMICA ---
                // Iteriamo su TUTTE le colonne restituite dalla query.
                // Non ci importa se si chiamano "cpu", "gpu", "disk_usage" o "pippo".
                Map<String, Object> values = record.getValues();

                for (Map.Entry<String, Object> entry : values.entrySet()) {
                    String key = entry.getKey();
                    Object val = entry.getValue();

                    // Filtriamo le colonne interne di InfluxDB che non servono al frontend
                    // _start, _stop, _time, result, table sono metadati della query Flux
                    if (!key.startsWith("_") && !key.equals("result") && !key.equals("table")) {
                        
                        // Gestione null safe: se un valore è null, mettiamo 0.0 (opzionale)
                        // Ma per renderlo generico, passiamo il valore o 0 se è nullo
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

    // QUERY 2: Analisi LLM - Analyzer
    /* public String getLatestLlmAnalysis() {
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
    } */

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