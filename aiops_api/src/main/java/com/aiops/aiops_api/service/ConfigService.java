package com.aiops.aiops_api.service;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import org.ini4j.Wini;
import org.springframework.stereotype.Service;
import jakarta.annotation.PostConstruct;

@Service
public class ConfigService {

    // Internal storage: maps metric name to its UI configuration (threshold and unit)
    // Structure: "cpu" -> { "threshold": 40.0, "unit": "%" }
    private final Map<String, Map<String, Object>> metricsConfig = new HashMap<>();

    @PostConstruct
    public void init() {
        try {
            File configFile = new File("config.ini"); 
            Wini ini = new Wini(configFile);

            // 1. Retrieve the list of enabled metrics from the [general] section
            String metricsString = ini.get("general", "metrics");
            if (metricsString != null) {
                String[] metricNames = metricsString.split(",\\s*");

                // 2. Iterate through each metric to extract UI-relevant metadata
                for (String name : metricNames) {
                    String cleanName = name.trim();
                    String sectionName = "metric_" + cleanName;
                    
                    String thresholdValue = ini.get(sectionName, "threshold");
                    String unitValue = ini.get(sectionName, "unit");
                    
                    if (thresholdValue != null) {
                        Map<String, Object> details = new HashMap<>();
                        
                        // Parse the threshold as Double for numeric comparison in the frontend
                        details.put("threshold", Double.parseDouble(thresholdValue));
                        
                        // Store the unit string; default to empty string if not provided in config.ini
                        details.put("unit", (unitValue != null && !unitValue.isEmpty()) ? unitValue : "");
                        
                        metricsConfig.put(cleanName, details);
                    }
                }
            }
            System.out.println("UI Metrics Configuration loaded: " + metricsConfig);
            
        } catch (IOException e) {
            System.err.println("Error loading config.ini for UI thresholds: " + e.getMessage());
        }
    }

    /**
     * Returns the complete metrics configuration to be exposed via REST API.
     */
    public Map<String, Map<String, Object>> getThresholds() {
        return metricsConfig;
    }
}