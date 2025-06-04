<template>
  <div>
    <div class="status-info mb-4">
      <div class="data-status">
        <span v-if="dataCompleteness !== null">数据完整度: {{ dataCompleteness }}%</span>
        <span v-if="dataTimeSpan !== null">数据时间跨度: {{ dataTimeSpan }} 小时</span>
        <span>更新时间: {{ updateTime }}</span>
      </div>
      <div class="period-stats" v-if="periodStats">
        <span v-for="(stats, period) in periodStats" :key="period">
          {{ period }}: {{ stats.percentage }}%
        </span>
      </div>
    </div>

    <div class="data-note mb-4">
      <strong>实时数据显示:</strong> 系统会立即显示已收集的数据，无需等待所有时间段的数据都准备好。随着系统运行时间增加，更多历史数据将逐渐可用。
    </div>

    <el-input v-model="filterText" placeholder="搜索币种" class="mb-2" />

    <el-table :data="paginatedData" stripe style="width: 100%">
      <el-table-column prop="symbol" label="币种" sortable>
        <template #default="scope">
          <el-tooltip v-if="scope.row.data_points_count" :content="`${scope.row.data_points_count} 个数据点`">
            <span>{{ scope.row.symbol }}</span>
          </el-tooltip>
          <span v-else>{{ scope.row.symbol }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="当前价格" sortable>
        <template #default="scope">{{ scope.row.price.toFixed(4) }}</template>
      </el-table-column>

      <el-table-column label="1分钟涨跌" :sortable="true"
        :sort-method="(a, b) => getSortValue(a, b, '1m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.change['1m'])">
            {{ formatChange(scope.row.change['1m']) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="2分钟涨跌" :sortable="true"
        :sort-method="(a, b) => getSortValue(a, b, '2m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.change['2m'])">
            {{ formatChange(scope.row.change['2m']) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="5分钟涨跌" :sortable="true"
        :sort-method="(a, b) => getSortValue(a, b, '5m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.change['5m'])">
            {{ formatChange(scope.row.change['5m']) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="20分钟涨跌" :sortable="true"
        :sort-method="(a, b) => getSortValue(a, b, '20m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.change['20m'])">
            {{ formatChange(scope.row.change['20m']) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="40分钟涨跌" :sortable="true"
        :sort-method="(a, b) => getSortValue(a, b, '40m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.change['40m'])">
            {{ formatChange(scope.row.change['40m']) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="1小时涨跌" :sortable="true"
        :sort-method="(a, b) => getSortValue(a, b, '1h')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.change['1h'])">
            {{ formatChange(scope.row.change['1h']) }}
          </span>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-4 text-center">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="filteredData.length"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import API from '../api'
import { ElMessage } from 'element-plus'

const data = ref([])
const filterText = ref('')
const currentPage = ref(1)
const pageSize = 20
const dataCompleteness = ref(null)
const dataTimeSpan = ref(null)
const periodStats = ref(null)
const updateTime = ref('--:--:--')

const fetchData = async () => {
  try {
    const res = await API.get('/api/price_change')
    data.value = res.data.data
    
    // 更新元数据
    dataCompleteness.value = res.data.data_completeness || 0
    dataTimeSpan.value = res.data.data_time_span_hours || 0
    periodStats.value = res.data.period_stats || null
    updateTime.value = new Date().toLocaleTimeString()
    
    console.log('数据完整度:', dataCompleteness.value)
    console.log('数据时间跨度:', dataTimeSpan.value)
  } catch (e) {
    console.error('获取失败:', e)
    ElMessage.error('获取失败')
  }
}

const filteredData = computed(() =>
  data.value.filter(item =>
    item.symbol.toLowerCase().includes(filterText.value.toLowerCase())
  )
)

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredData.value.slice(start, start + pageSize)
})

const handlePageChange = (page) => {
  currentPage.value = page
}

// 获取排序值
const getSortValue = (a, b, period) => {
  const aChange = a.change[period]
  const bChange = b.change[period]
  
  // 如果两个值都有可用数据，直接比较
  if (aChange?.available && bChange?.available) {
    return aChange.value - bChange.value
  }
  
  // 如果只有一个有可用数据，有数据的排前面
  if (aChange?.available) return -1
  if (bChange?.available) return 1
  
  // 如果都有估计值，比较估计值
  if (aChange?.estimated && bChange?.estimated) {
    return aChange.value - bChange.value
  }
  
  // 如果只有一个有估计值，有估计值的排前面
  if (aChange?.estimated) return -1
  if (bChange?.estimated) return 1
  
  // 都没有数据，保持原顺序
  return 0
}

// 格式化变化值
const formatChange = (changeData) => {
  if (!changeData) return '-'
  
  if (changeData.available) {
    return (changeData.value >= 0 ? '+' : '') + changeData.value.toFixed(2) + '%'
  } else if (changeData.estimated) {
    return (changeData.value >= 0 ? '+' : '') + changeData.value.toFixed(2) + '%*'
  } else {
    return '-'
  }
}

// 获取CSS类
const getChangeClass = (changeData) => {
  if (!changeData) return 'not-available'
  
  let classes = []
  
  if (changeData.available || changeData.estimated) {
    if (changeData.value > 0) {
      classes.push('positive-change')
    } else if (changeData.value < 0) {
      classes.push('negative-change')
    }
    
    if (changeData.estimated) {
      classes.push('estimated')
    }
    
    if (changeData.method === 'closest') {
      classes.push('approximate')
    }
  } else {
    classes.push('not-available')
  }
  
  return classes.join(' ')
}

onMounted(() => {
  fetchData()
  setInterval(fetchData, 10000) // 每10秒刷新一次
})
</script>

<style scoped>
.status-info {
  background-color: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.data-status {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.period-stats {
  display: flex;
  gap: 15px;
  color: #666;
  font-size: 0.85em;
  margin-top: 5px;
  padding-top: 5px;
  border-top: 1px dashed #ddd;
}

.data-note {
  padding: 10px;
  background-color: #fff3cd;
  border-left: 4px solid #ffc107;
  color: #856404;
  font-size: 0.9em;
}

.positive-change {
  color: #4caf50;
  font-weight: bold;
}

.negative-change {
  color: #f44336;
  font-weight: bold;
}

.estimated {
  opacity: 0.7;
}

.approximate {
  text-decoration: underline dotted;
  text-underline-offset: 2px;
}

.not-available {
  color: #999;
}
</style>
