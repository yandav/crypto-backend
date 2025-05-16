<template>
  <div>
    <h2>📉 涨跌幅警报</h2>
    <ul>
      <li v-for="alert in alerts" :key="alert">{{ alert }}</li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import API from '../api'

const alerts = ref([])

const load = async () => {
  const res = await API.get('/api/data')
  alerts.value = res.data.alerts.change_alerts
}

onMounted(load)
</script>
