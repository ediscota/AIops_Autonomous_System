<template>
  <div class="metric-card">
    <div class="card-header">
      <div class="header-top">
        <span class="container-name">{{ formattedName }}</span>
        <span class="badge">{{ formattedCluster }}</span>
      </div>
    </div>

    <div class="card-body">
      <div 
        v-for="(value, key) in displayMetrics" 
        :key="key" 
        class="metric-row"
      >
        <span class="label">{{ formatLabel(key) }}</span>
        
        <span 
          class="value" 
          :class="getDynamicClass(key, value)"
          :title="thresholds[key] ? 'Threshold: ' + thresholds[key].threshold : ''"
        >
          {{ formatValue(key, value) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "MetricCard",
  props: {
    // Current live metrics for the container
    metricData: { type: Object, required: true },
    // Configuration mapping (thresholds and units) from ConfigService
    thresholds: { type: Object, required: true }
  },
  computed: {
    // Cleans and formats the container name for display
    formattedName() {
      const name = this.metricData.container || "Unknown";
      return name.replace("container_", "").replace("-", " ").replace("_", " ").toUpperCase();
    },

    // Cleans and formats the cluster name for display
    formattedCluster() {
      const name = this.metricData.cluster || "Unknown";
      return name.replace("container_", "").replace("-", " ").replace("_", " ").toUpperCase();
    },

    // Filters out technical metadata keys that shouldn't be displayed in the UI
    displayMetrics() {
      const ignoredKeys = ['cluster', 'container', 'host', 'topic', 'result', 'table', '_start', '_stop', '_time'];
      
      const metrics = {};
      for (const [key, value] of Object.entries(this.metricData)) {
        if (!ignoredKeys.includes(key)) {
          metrics[key] = value;
        }
      }
      return metrics;
    }
  },
  methods: {
    // Converts snake_case keys to Upper Case labels (e.g., "service_time" -> "SERVICE TIME")
    formatLabel(key) {
      return key
        .replace(/_/g, " ") 
        .replace(/\b\w/g, l => l.toUpperCase()) 
        .toUpperCase();
    },

    // Formats the numeric value and appends the unit defined in config.ini
    formatValue(key, value) {
      if (typeof value !== 'number') return value;

      // Get configuration for this specific metric
      const config = this.thresholds[key];
      
      // Append unit if it exists in the configuration
      const unit = (config && config.unit) ? ' ' + config.unit : '';
      
      // Precision logic: Integers for instances, 2 decimal places for others
      const formattedNum = key.includes('instances') ? Math.round(value) : value.toFixed(2);

      return `${formattedNum}${unit}`;
    },

    // Determines the CSS class based on the current value vs the threshold
    getDynamicClass(key, value) {
      const config = this.thresholds[key];

      // If no threshold is defined for this metric, use default styles
      if (!config || config.threshold === undefined) {
        if (key.includes('instances')) return 'instance-badge-text';
        return 'normal';
      }

      const threshold = config.threshold;

      // Critical state: value strictly exceeds the threshold
      if (value > threshold) {
        return 'critical';
      }

      // Warning state: value is within the "danger zone" (50% of threshold)
      if (value > (threshold * 0.5)) {
        return 'warning';
      }

      return 'normal';
    }
  }
};
</script>

<style scoped>
.metric-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 1.2rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid #f0f0f0;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.5rem;
}

.container-name {
  font-weight: 700;
  color: #2c3e50;
  font-size: 1rem;
}

.badge {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  color: #64748b;
  font-size: 0.9rem;
}

.value {
  font-family: 'Consolas', monospace;
  font-weight: 600;
}

/* State Colors */
.normal { color: #059669; }
.warning { color: #f59e0b; }
.critical { color: #ef4444; font-weight: 800; }

/* Special Style for the Instances count */
.instance-badge-text {
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}
</style>