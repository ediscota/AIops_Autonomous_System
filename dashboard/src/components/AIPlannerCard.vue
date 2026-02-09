<template>
  <div class="ai-card" :class="{ 'ai-active': hasPlan }">
    <div class="ai-header">
      <h3>🤖 AI Autonomous Planner</h3>
      <span v-if="loading" class="spinner">↻ Updating...</span>
      <span v-else class="last-update">Last update: {{ lastUpdate }}</span>
    </div>

    <div class="ai-body">
      <div v-if="loading && !response" class="skeleton-loader">
        Analisi in corso...
      </div>
      <div v-else class="response-text">
        {{ response }}
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "AiPlannerCard",
  data() {
    return {
      response: "",
      loading: true,
      lastUpdate: "-",
      intervalId: null
    };
  },
  computed: {
    hasPlan() {
      return this.response && !this.response.includes("No actions required");
    }
  },
  methods: {
    async fetchPlan() {
      this.loading = true;
      try {
        const res = await axios.get("http://localhost:8080/api/planning");
        this.response = res.data.response;
        this.lastUpdate = new Date().toLocaleTimeString();
      } catch (err) {
        console.error("Errore AI Planner", err);
        this.response = "Errore di connessione col Planner AI.";
      } finally {
        this.loading = false;
      }
    }
  },
  mounted() {
    this.fetchPlan();
    // Aggiorna ogni 10 secondi
    this.intervalId = setInterval(this.fetchPlan, 10000);
  },
  beforeUnmount() {
    clearInterval(this.intervalId);
  }
};
</script>

<style scoped>
.ai-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 5px solid #94a3b8; /* Default grigio */
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}

.ai-active {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #22c55e; /* Verde acceso se c'è un piano */
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  padding-bottom: 0.5rem;
}

.ai-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #334155;
}

.last-update {
  font-size: 0.8rem;
  color: #94a3b8;
}

.response-text {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  white-space: pre-wrap; /* Mantiene la formattazione a capo dell'AI */
  line-height: 1.6;
  color: #1e293b;
}

.spinner {
  font-size: 0.8rem;
  color: #3b82f6;
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }
</style>