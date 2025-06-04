<template>
  <div class="trade-monitor">
    <h2>交易员监控</h2>
    
    <!-- 交易员选择 -->
    <div class="trader-selector">
      <el-select v-model="selectedTraderId" placeholder="选择交易员" @change="loadTrades">
        <el-option
          v-for="trader in traders"
          :key="trader.id"
          :label="trader.name"
          :value="trader.id">
        </el-option>
      </el-select>
      
      <el-button type="primary" @click="refreshData" :loading="loading">
        <i class="el-icon-refresh"></i> 刷新
      </el-button>
      
      <el-button type="success" @click="updateTrades" :loading="updating">
        更新交易数据
      </el-button>
    </div>
    
    <!-- 交易员信息卡片 -->
    <div v-if="selectedTrader" class="trader-info">
      <el-card>
        <div slot="header">
          <span>{{ selectedTrader.name }}</span>
          <a v-if="selectedTrader.source_url" :href="selectedTrader.source_url" target="_blank">
            <i class="el-icon-link"></i>
          </a>
        </div>
        <div class="trader-stats">
          <div class="stat-item">
            <div class="stat-label">开仓交易</div>
            <div class="stat-value">{{ selectedTrader.stats.open_trades }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">已平交易</div>
            <div class="stat-value">{{ selectedTrader.stats.closed_trades }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">胜率</div>
            <div class="stat-value" :class="{'positive': selectedTrader.stats.win_rate > 50, 'negative': selectedTrader.stats.win_rate < 50}">
              {{ selectedTrader.stats.win_rate }}%
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-label">总盈亏</div>
            <div class="stat-value" :class="{'positive': selectedTrader.stats.total_pnl > 0, 'negative': selectedTrader.stats.total_pnl < 0}">
              {{ selectedTrader.stats.total_pnl > 0 ? '+' : '' }}{{ selectedTrader.stats.total_pnl }}
            </div>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 交易记录表格 -->
    <div class="trades-table">
      <h3>交易记录</h3>
      
      <el-tabs v-model="activeTab" @tab-click="handleTabClick">
        <el-tab-pane label="开仓交易" name="OPEN"></el-tab-pane>
        <el-tab-pane label="已平交易" name="CLOSED"></el-tab-pane>
        <el-tab-pane label="全部交易" name="ALL"></el-tab-pane>
      </el-tabs>
      
      <el-table
        :data="trades"
        style="width: 100%"
        v-loading="loading"
        border
        stripe>
        <el-table-column prop="symbol" label="交易对" width="120"></el-table-column>
        <el-table-column label="方向" width="100">
          <template slot-scope="scope">
            <el-tag :type="scope.row.direction === 'LONG' ? 'success' : 'danger'">
              {{ scope.row.direction === 'LONG' ? '做多' : '做空' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入场价" width="120">
          <template slot-scope="scope">
            {{ scope.row.entry_price }}
          </template>
        </el-table-column>
        <el-table-column label="当前价" width="120">
          <template slot-scope="scope">
            {{ scope.row.current_price || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="止盈/止损" width="160">
          <template slot-scope="scope">
            <div>TP: {{ scope.row.take_profit || '-' }}</div>
            <div>SL: {{ scope.row.stop_loss || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="杠杆" width="80">
          <template slot-scope="scope">
            {{ scope.row.leverage || '-' }}x
          </template>
        </el-table-column>
        <el-table-column label="仓位" width="100">
          <template slot-scope="scope">
            {{ scope.row.position_size || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="盈亏" width="120">
          <template slot-scope="scope">
            <template v-if="scope.row.status === 'OPEN'">
              <div v-if="scope.row.unrealized_pnl !== null" 
                   :class="{'positive': scope.row.unrealized_pnl > 0, 'negative': scope.row.unrealized_pnl < 0}">
                {{ scope.row.unrealized_pnl > 0 ? '+' : '' }}{{ scope.row.unrealized_pnl }}
                ({{ scope.row.unrealized_pnl_percentage > 0 ? '+' : '' }}{{ scope.row.unrealized_pnl_percentage }}%)
              </div>
              <div v-else>-</div>
            </template>
            <template v-else>
              <div v-if="scope.row.pnl !== null" 
                   :class="{'positive': scope.row.pnl > 0, 'negative': scope.row.pnl < 0}">
                {{ scope.row.pnl > 0 ? '+' : '' }}{{ scope.row.pnl }}
                ({{ scope.row.pnl_percentage > 0 ? '+' : '' }}{{ scope.row.pnl_percentage }}%)
              </div>
              <div v-else>-</div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="入场时间" width="180">
          <template slot-scope="scope">
            {{ formatDate(scope.row.entry_time) }}
          </template>
        </el-table-column>
        <el-table-column label="出场时间" width="180">
          <template slot-scope="scope">
            {{ scope.row.exit_time ? formatDate(scope.row.exit_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="备注">
          <template slot-scope="scope">
            {{ scope.row.notes || '-' }}
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[10, 20, 50, 100]"
          :page-size="pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total">
        </el-pagination>
      </div>
    </div>
  </div>
</template>

<script>
import API from '../api';
import { formatDate } from '../utils/dateFormatter';

export default {
  name: 'TradeMonitor',
  data() {
    return {
      traders: [],
      selectedTraderId: null,
      selectedTrader: null,
      trades: [],
      loading: false,
      updating: false,
      activeTab: 'ALL',  // 默认显示全部交易
      currentPage: 1,
      pageSize: 10,
      total: 0,
      timer: null
    };
  },
  created() {
    // 首次加载时先更新交易数据，然后加载交易员信息
    this.initialLoad();
    
    // 定时刷新数据
    this.timer = setInterval(() => {
      this.refreshData(false);
    }, 60000); // 每分钟刷新一次
  },
  beforeDestroy() {
    // 清除定时器
    if (this.timer) {
      clearInterval(this.timer);
    }
  },
  methods: {
    formatDate,
    async initialLoad() {
      this.loading = true;
      try {
        // 首先更新交易数据
        await this.updateTrades(false);
        
        // 然后加载交易员信息
        await this.loadTraders();
      } catch (error) {
        console.error('初始化数据失败:', error);
        this.$message.error('初始化数据失败');
      } finally {
        this.loading = false;
      }
    },
    async loadTraders() {
      this.loading = true;
      try {
        const response = await API.get('/api/traders');
        this.traders = response.data.data;
        
        if (this.traders.length > 0) {
          // 查找熬鹰资本交易员
          const aoyingTrader = this.traders.find(t => t.name === '熬鹰资本');
          
          // 如果找到熬鹰资本则选择它，否则选择第一个交易员
          if (aoyingTrader) {
            this.selectedTraderId = aoyingTrader.id;
            this.selectedTrader = aoyingTrader;
          } else if (!this.selectedTraderId) {
            this.selectedTraderId = this.traders[0].id;
            this.selectedTrader = this.traders[0];
          }
          
          this.loadTrades();
        }
      } catch (error) {
        console.error('加载交易员失败:', error);
        this.$message.error('加载交易员失败');
      } finally {
        this.loading = false;
      }
    },
    async loadTrades() {
      if (!this.selectedTraderId) return;
      
      this.loading = true;
      try {
        // 更新选中的交易员信息
        this.selectedTrader = this.traders.find(t => t.id === this.selectedTraderId);
        
        // 构建查询参数
        const params = {
          trader_id: this.selectedTraderId,
          limit: this.pageSize,
          offset: (this.currentPage - 1) * this.pageSize
        };
        
        // 如果不是"全部"标签，添加状态过滤
        if (this.activeTab !== 'ALL') {
          params.status = this.activeTab;
        }
        
        const response = await API.get('/api/trades', { params });
        this.trades = response.data.data;
        this.total = response.data.pagination.total;
      } catch (error) {
        console.error('加载交易记录失败:', error);
        this.$message.error('加载交易记录失败');
      } finally {
        this.loading = false;
      }
    },
    async updateTrades(showMessage = true) {
      this.updating = true;
      try {
        const response = await API.post('/api/update_trades', {
          use_mock: false,  // 使用真实爬虫（带有回退机制）
          count: 5  // 如果回退到模拟数据，生成5条记录
        });
        
        if (showMessage) {
          this.$message.success(`交易数据更新成功，新增/更新 ${response.data.saved_count} 条记录`);
        }
        
        // 重新加载数据
        await this.loadTraders();
        await this.loadTrades();
      } catch (error) {
        console.error('更新交易数据失败:', error);
        if (showMessage) {
          this.$message.error('更新交易数据失败');
        }
      } finally {
        this.updating = false;
      }
    },
    refreshData(showLoading = true) {
      if (showLoading) {
        this.loading = true;
      }
      
      Promise.all([
        this.loadTraders(),
        this.loadTrades()
      ]).finally(() => {
        if (showLoading) {
          this.loading = false;
        }
      });
    },
    handleTabClick() {
      this.currentPage = 1;  // 切换标签时重置页码
      this.loadTrades();
    },
    handleSizeChange(size) {
      this.pageSize = size;
      this.loadTrades();
    },
    handleCurrentChange(page) {
      this.currentPage = page;
      this.loadTrades();
    }
  }
};
</script>

<style scoped>
.trade-monitor {
  padding: 20px;
}

.trader-selector {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.trader-selector .el-select {
  width: 200px;
  margin-right: 10px;
}

.trader-info {
  margin-bottom: 20px;
}

.trader-stats {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
}

.positive {
  color: #67C23A;
}

.negative {
  color: #F56C6C;
}

.trades-table {
  margin-top: 20px;
}

.pagination {
  margin-top: 20px;
  text-align: right;
}
</style> 