<template>
  <div>
    <el-input v-model="filterText" placeholder="搜索币种" class="mb-2" />

    <el-table
      :data="pagedData"
      style="width: 100%"
      stripe
    >
      <el-table-column prop="symbol" label="币种" sortable />
      <el-table-column prop="fundingRate" label="资金费率" sortable>
        <template #default="scope">
          {{ formatRate(scope.row.fundingRate) }}
        </template>
      </el-table-column>
      <el-table-column prop="openInterest" label="当前持仓量" sortable />
      <el-table-column prop="openInterestChange['5m']" label="5分钟涨跌" sortable />
      <el-table-column prop="openInterestChange['15m']" label="15分钟涨跌" sortable />
      <el-table-column prop="openInterestChange['1h']" label="1小时涨跌" sortable />
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
import axios from 'axios'
import { ElMessage } from 'element-plus'

const data = ref([])
const filterText = ref('')

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(20)

// 请求数据
const fetchData = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:5000/api/open_interest')
    data.value = res.data.data
  } catch (e) {
    ElMessage.error('获取失败')
  }
}

// 格式化资金费率
const formatRate = (rate) => (rate * 100).toFixed(4) + '%'

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
  setInterval(fetchData, 30000)
})
</script>

<style scoped>
.mb-2 {
  margin-bottom: 12px;
}
.mt-4 {
  margin-top: 16px;
}
</style>
