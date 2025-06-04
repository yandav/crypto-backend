<template>
  <div>
    <div class="alert-header">
      <h2>📉 涨跌幅警报</h2>
      <div class="alert-info">
        <span>更新时间: {{ updateTime }}</span>
        <span>警报数量: {{ alerts.length }}</span>
      </div>
    </div>

    <div class="alert-controls">
      <input
        v-model="searchKeyword"
        placeholder="搜索币种"
        class="search-box"
      />
      
      <div class="filter-options">
        <el-select v-model="alertTypeFilter" placeholder="警报类型" clearable>
          <el-option label="全部" value=""></el-option>
          <el-option label="大幅上涨" value="surge"></el-option>
          <el-option label="大幅下跌" value="drop"></el-option>
        </el-select>
      </div>
    </div>

    <div class="data-note mb-4" v-if="alerts.length === 0">
      <strong>暂无警报:</strong> 当前没有符合条件的涨跌幅警报。系统会监控价格的剧烈变化，当出现大幅波动时会在此处显示。
    </div>

    <ul class="alert-list">
      <li v-for="alert in filteredAlerts" :key="alert" 
          :class="{'alert-item': true, 'positive-alert': isPositiveAlert(alert), 'negative-alert': isNegativeAlert(alert)}">
        {{ alert }}
      </li>
    </ul>

    <div class="alert-footer">
      <p class="alert-description">
        涨跌幅警报基于短时间内的价格剧烈变化，当价格在短时间内出现大幅上涨或下跌时，系统会生成警报信号。
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import API from '../api'
import { ElSelect, ElOption } from 'element-plus'

const alerts = ref([])
const updateTime = ref('--:--:--')
const searchKeyword = ref('')
const alertTypeFilter = ref('')

const load = async () => {
  try {
    const res = await API.get('/api/data')
    alerts.value = res.data.alerts.change_alerts
    updateTime.value = new Date().toLocaleTimeString()
    console.log(`涨跌幅警报已更新，共 ${alerts.value.length} 条`)
  } catch (error) {
    console.error('加载涨跌幅警报失败:', error)
  }
}

const isPositiveAlert = (alert) => {
  return alert.includes('上涨') || alert.includes('突破')
}

const isNegativeAlert = (alert) => {
  return alert.includes('下跌') || alert.includes('跌破')
}

const filteredAlerts = computed(() => {
  let result = alerts.value
  
  // 关键词搜索
  if (searchKeyword.value) {
    result = result.filter(alert => 
      alert.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
  
  // 警报类型筛选
  if (alertTypeFilter.value) {
    switch (alertTypeFilter.value) {
      case 'surge':
        result = result.filter(alert => isPositiveAlert(alert))
        break
      case 'drop':
        result = result.filter(alert => isNegativeAlert(alert))
        break
    }
  }
  
  return result
})

onMounted(() => {
  load()
  setInterval(load, 10000) // 每10秒刷新一次
})
</script>

<style scoped>
.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.alert-info {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: #666;
}

.alert-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.filter-options {
  min-width: 120px;
}

.search-box {
  width: 60%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.alert-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.alert-item {
  padding: 10px;
  background-color: #f9f9f9;
  margin-bottom: 8px;
  border-radius: 4px;
}

.positive-alert {
  border-left: 3px solid #4caf50;
}

.negative-alert {
  border-left: 3px solid #f44336;
}

.alert-footer {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px dashed #ddd;
}

.alert-description {
  font-size: 0.9em;
  color: #666;
  font-style: italic;
}

.data-note {
  padding: 10px;
  background-color: #fff3cd;
  border-left: 4px solid #ffc107;
  color: #856404;
  font-size: 0.9em;
  margin-bottom: 15px;
}

.mb-4 {
  margin-bottom: 1rem;
}
</style>
