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

    // Map that associates for each metric its threshold (es: "cpu" -> 10.0)
    private final Map<String, Double> thresholds = new HashMap<>();

    @PostConstruct
    public void init() {
        try {
            File configFile = new File("config.ini"); 
            Wini ini = new Wini(configFile);

            // 1. We first read what metrics are defined (cpu, memory, ecc.)
            String metricsString = ini.get("general", "metrics");
            if (metricsString != null) {
                String[] metricNames = metricsString.split(",\\s*");

                // 2. For each metric we find its section [metric_name]
                for (String name : metricNames) {
                    String sectionName = "metric_" + name.trim();
                    String thresholdValue = ini.get(sectionName, "threshold");
                    
                    if (thresholdValue != null) {
                        thresholds.put(name.trim(), Double.parseDouble(thresholdValue));
                    }
                }
            }
            System.out.println("Thresholds loaded: " + thresholds);
            
        } catch (IOException e) {
            System.err.println("There was an error during config.ini loading: " + e.getMessage());
        }
    }

    public Map<String, Double> getThresholds() {
        return thresholds;
    }
}