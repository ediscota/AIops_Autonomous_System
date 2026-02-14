package com.aiops.aiops_api.controller;

import com.aiops.aiops_api.service.MetricsService;
import com.aiops.aiops_api.service.ConfigService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*") // Important for the Vue.js frontend
public class ApiController {

    @Autowired
    private MetricsService metricsService;

    @Autowired
    private ConfigService configService;

    @GetMapping("/metrics")
    public List<Map<String, Object>> getMetrics() {
        return metricsService.getLiveMetrics();
    }

    @GetMapping("/planning")
    public Map<String, String> getPlanning() {
        return Map.of("response", metricsService.getLatestLlmPlanner());
    }

    @GetMapping("/thresholds")
    public Map<String, Map<String, Object>> getThresholds() {
        return configService.getThresholds();
    }
}