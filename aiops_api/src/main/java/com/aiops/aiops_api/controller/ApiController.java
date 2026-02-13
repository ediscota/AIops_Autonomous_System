package com.aiops.aiops_api.controller;

import com.aiops.aiops_api.service.MetricsService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*") // Importante per il frontend Vue.js
public class ApiController {

    @Autowired
    private MetricsService metricsService;

    @GetMapping("/metrics")
    public List<Map<String, Object>> getMetrics() {
        return metricsService.getLiveMetrics();
    }

    @GetMapping("/planning")
    public Map<String, String> getPlanning() {
        return Map.of("response", metricsService.getLatestLlmPlanner());
    }
}