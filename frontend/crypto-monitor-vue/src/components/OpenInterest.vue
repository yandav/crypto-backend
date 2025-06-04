<template>
  <div>
    <div class="status-info mb-4">
      <div class="data-status">
        <span>数据总数: {{ data.length }} 个交易对</span>
        <span>更新时间: {{ updateTime }}</span>
      </div>
    </div>

    <div class="data-note mb-4">
      <strong>实时数据显示:</strong> 系统会立即显示已收集的持仓量数据，部分时间段的变化数据可能暂时不可用。随着系统运行时间增加，更多历史数据将逐渐可用。
    </div>

    <el-input v-model="filterText" placeholder="搜索币种" class="mb-2" />

    <el-table
      :data="pagedData"
      style="width: 100%"
      stripe
    >
      <el-table-column prop="symbol" label="币种" sortable />
      <el-table-column prop="fundingRate" label="资金费率" sortable>
        <template #default="scope">
          <span :class="getFundingRateClass(scope.row.fundingRate)">
            {{ formatRate(scope.row.fundingRate) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="openInterest" label="当前持仓量" sortable>
        <template #default="scope">
          {{ formatNumber(scope.row.openInterest) }}
        </template>
      </el-table-column>
      <el-table-column label="5分钟涨跌" sortable :sort-method="(a, b) => getSortValue(a, b, '5m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.openInterestChange?.['5m'])">
            {{ formatChange(scope.row.openInterestChange?.['5m']) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="15分钟涨跌" sortable :sort-method="(a, b) => getSortValue(a, b, '15m')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.openInterestChange?.['15m'])">
            {{ formatChange(scope.row.openInterestChange?.['15m']) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="1小时涨跌" sortable :sort-method="(a, b) => getSortValue(a, b, '1h')">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.openInterestChange?.['1h'])">
            {{ formatChange(scope.row.openInterestChange?.['1h']) }}
          </span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页组件 -->
    <div class="mt-4 text-center">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredData.length"
        layout="total, sizes, prev, pager, next, jumper"
        background
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import API from '../api'
import { ElMessage } from 'element-plus'

const data = ref([])
const filterText = ref('')
const updateTime = ref('--:--:--')

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(20)

// 请求数据
const fetchData = async () => {
  try {
    const res = await API.get('/api/open_interest')
    data.value = res.data.data
    updateTime.value = new Date().toLocaleTimeString()
    console.log(`持仓量数据已更新，共 ${data.value.length} 条记录`)
  } catch (e) {
    console.error('获取失败:', e)
    ElMessage.error('获取失败')
  }
}

// 格式化资金费率
const formatRate = (rate) => {
  if (rate === null || rate === undefined) return '-'
  return (rate * 100).toFixed(4) + '%'
}

// 格式化数字，添加千位分隔符
const formatNumber = (num) => {
  if (num === null || num === undefined) return '-'
  return num.toLocaleString()
}

// 格式化变化值
const formatChange = (change) => {
  if (change === null || change === undefined) return '-'
  return (change >= 0 ? '+' : '') + change.toFixed(2) + '%'
}

// 获取资金费率的CSS类
const getFundingRateClass = (rate) => {
  if (rate === null || rate === undefined) return ''
  if (rate > 0.0001) return 'high-positive'
  if (rate > 0) return 'positive-rate'
  if (rate < -0.0001) return 'high-negative'
  if (rate < 0) return 'negative-rate'
  return ''
}

// 获取变化值的CSS类
const getChangeClass = (change) => {
  if (change === null || change === undefined) return 'not-available'
  if (change > 5) return 'high-positive-change'
  if (change > 0) return 'positive-change'
  if (change < -5) return 'high-negative-change'
  if (change < 0) return 'negative-change'
  return ''
}

// 获取排序值
const getSortValue = (a, b, period) => {
  const aChange = a.openInterestChange?.[period]
  const bChange = b.openInterestChange?.[period]
  
  // 如果两个都有值，直接比较
  if (aChange !== undefined && bChange !== undefined) {
    return aChange - bChange
  }
  
  // 如果只有一个有值，有值的排前面
  if (aChange !== undefined) return -1
  if (bChange !== undefined) return 1
  
  // 都没有值，保持原顺序
  return 0
}

// 搜索过滤后的数据
const filteredData = computed(() =>
  data.value.filter(item =>
    item.symbol.toLowerCase().includes(filterText.value.toLowerCase())
  )
)

// 当前页显示的数据
const pagedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredData.value.slice(start, end)
})

// 页面挂载和定时刷新
onMounted(() => {
  fetchData()
  setInterval(fetchData, 10000) // 每10秒刷新一次
})
</script>

<style scoped>
.mb-2 {
  margin-bottom: 12px;
}
.mt-4 {
  margin-top: 16px;
}

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

.high-positive-change {
  color: #2e7d32;
  font-weight: bold;
}

.negative-change {
  color: #f44336;
  font-weight: bold;
}

.high-negative-change {
  color: #c62828;
  font-weight: bold;
}

.positive-rate {
  color: #4caf50;
}

.high-positive {
  color: #2e7d32;
  font-weight: bold;
}

.negative-rate {
  color: #f44336;
}

.high-negative {
  color: #c62828;
  font-weight: bold;
}

.not-available {
  color: #999;
}
</style>
