<template>
  <div class="app-container">
    <header class="dashboard-header">
      <h1>🚀 AIOps Autonomous System</h1>
      <p>Real-time monitoring & Self-healing AI</p>
    </header>

    <main>
      <section class="ai-section">
        <AiPlannerCard />
      </section>

      <section class="metrics-section">
        <div v-if="loading" class="loading-message">
          📡 Connessione al cluster in corso...
        </div>
        
        <div v-else class="metrics-grid">
          <MetricCard 
            v-for="(item, index) in metrics" 
            :key="index" 
            :metricData="item" 
          />
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import axios from 'axios';
// IMPORTAZIONE DIRETTA DEI COMPONENTI
import MetricCard from './components/MetricCard.vue';
import AiPlannerCard from './components/AIPlannerCard.vue';

export default {
  name: 'App',
  components: {
    // REGISTRAZIONE DEI COMPONENTI PER USARLI NEL TEMPLATE
    MetricCard,
    AiPlannerCard
  },
  data() {
    return {
      metrics: [],
      loading: true,
      intervalId: null
    }
  },
  methods: {
    async fetchMetrics() {
      try {
        const res = await axios.get('http://localhost:8080/api/metrics');
        this.metrics = res.data;
        this.loading = false;
      } catch (error) {
        console.error("Errore API Metriche:", error);
      }
    }
  },
  mounted() {
    this.fetchMetrics();
    this.intervalId = setInterval(this.fetchMetrics, 2000); // Aggiorna ogni 2s
  },
  beforeUnmount() {
    clearInterval(this.intervalId);
  }
}
</script>

<style>
/* STILI GLOBALI */
body {
  margin: 0;
  background-color: #f8f9fa;
  font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: #2c3e50;
}

.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 3rem;
}

.dashboard-header h1 {
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.dashboard-header p {
  color: #64748b;
  margin: 0;
}

.ai-section {
  margin-bottom: 3rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); /* Griglia responsiva automatica */
  gap: 1.5rem;
}

.loading-message {
  text-align: center;
  font-size: 1.2rem;
  color: #64748b;
  padding: 2rem;
}
</style>