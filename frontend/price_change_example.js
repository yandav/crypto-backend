// 价格变化数据处理示例

/**
 * 从后端获取价格变化数据
 * @returns {Promise<Array>} 价格变化数据
 */
async function fetchPriceChangeData() {
  try {
    const response = await fetch('http://localhost:5000/api/price_change');
    const data = await response.json();
    
    if (data.message.includes("成功")) {
      // 显示数据完整度和时间跨度信息
      console.log(`数据完整度: ${data.data_completeness || 0}%`);
      console.log(`数据时间戳: ${data.timestamp || "未知"}`);
      console.log(`数据时间跨度: ${data.data_time_span_hours || 0} 小时`);
      
      // 显示每个时间段的可用性
      if (data.period_stats) {
        console.log("时间段可用性:");
        Object.entries(data.period_stats).forEach(([period, stats]) => {
          console.log(`  ${period}: ${stats.available}/${stats.total} (${stats.percentage}%)`);
        });
      }
      
      return data.data;
    } else {
      console.error('获取价格变化数据失败:', data.message);
      return [];
    }
  } catch (error) {
    console.error('获取价格变化数据出错:', error);
    return [];
  }
}

/**
 * 渲染价格变化表格
 * @param {Array} data 价格变化数据
 */
function renderPriceChangeTable(data) {
  // 获取表格元素
  const tableBody = document.getElementById('price-change-table-body');
  if (!tableBody) return;
  
  // 清空表格
  tableBody.innerHTML = '';
  
  if (!data || data.length === 0) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 8;
    cell.textContent = '暂无数据';
    cell.style.textAlign = 'center';
    row.appendChild(cell);
    tableBody.appendChild(row);
    return;
  }
  
  // 计算每个时间段的可用数据数量
  const availableStats = {};
  const periods = ['1m', '2m', '5m', '20m', '40m', '1h'];
  
  periods.forEach(period => {
    availableStats[period] = data.filter(item => 
      item.change[period] && item.change[period].available
    ).length;
  });
  
  // 确定按哪个时间段排序（选择数据最多的时间段）
  let sortPeriod = '1m'; // 默认按1分钟排序
  let maxAvailable = 0;
  
  periods.forEach(period => {
    if (availableStats[period] > maxAvailable) {
      maxAvailable = availableStats[period];
      sortPeriod = period;
    }
  });
  
  // 对数据进行排序
  const sortedData = [...data].sort((a, b) => {
    // 如果选定的时间段没有数据，尝试使用其他时间段
    let aValue = 0;
    let bValue = 0;
    
    if (a.change[sortPeriod] && (a.change[sortPeriod].available || a.change[sortPeriod].estimated)) {
      aValue = a.change[sortPeriod].value;
    } else {
      // 尝试找到有数据的最近时间段
      for (const p of periods) {
        if (a.change[p] && (a.change[p].available || a.change[p].estimated)) {
          aValue = a.change[p].value;
          break;
        }
      }
    }
    
    if (b.change[sortPeriod] && (b.change[sortPeriod].available || b.change[sortPeriod].estimated)) {
      bValue = b.change[sortPeriod].value;
    } else {
      // 尝试找到有数据的最近时间段
      for (const p of periods) {
        if (b.change[p] && (b.change[p].available || b.change[p].estimated)) {
          bValue = b.change[p].value;
          break;
        }
      }
    }
    
    return bValue - aValue; // 降序排列
  });
  
  // 渲染表格行
  sortedData.forEach(item => {
    const row = document.createElement('tr');
    
    // 币种
    const symbolCell = document.createElement('td');
    symbolCell.textContent = item.symbol;
    // 添加数据点数量作为提示
    if (item.data_points_count) {
      symbolCell.title = `${item.data_points_count} 个数据点`;
    }
    row.appendChild(symbolCell);
    
    // 当前价格
    const priceCell = document.createElement('td');
    priceCell.textContent = item.price.toFixed(4);
    row.appendChild(priceCell);
    
    // 各时间段涨跌幅
    periods.forEach(period => {
      const cell = document.createElement('td');
      const changeData = item.change[period];
      
      // 检查数据是否可用
      if (changeData && changeData.available) {
        // 数据可用，正常显示
        const value = changeData.value;
        cell.textContent = value.toFixed(2) + '%';
        cell.className = value > 0 ? 'positive-change' : (value < 0 ? 'negative-change' : '');
        
        // 添加提示信息
        if (changeData.method === 'closest') {
          cell.title = `实际数据点: ${changeData.actual_minutes}分钟前 (误差: ${changeData.time_diff}分钟)`;
          cell.classList.add('approximate');
        }
      } else if (changeData && changeData.estimated) {
        // 估计值，显示为斜体并添加星号
        const value = changeData.value;
        cell.innerHTML = `<i>${value.toFixed(2)}%*</i>`;
        cell.className = value > 0 ? 'positive-change estimated' : (value < 0 ? 'negative-change estimated' : 'estimated');
        cell.title = '基于24小时变化率估算';
      } else {
        // 数据不可用，显示短横线
        cell.innerHTML = '<span class="not-available">-</span>';
        
        // 如果有最早数据点信息，添加提示
        if (item.earliest_data_point) {
          const minutesAgo = item.earliest_data_point.minutes_ago;
          if (minutesAgo < parseInt(period)) {
            cell.title = `数据收集中，最早的数据点在 ${minutesAgo} 分钟前`;
          } else {
            cell.title = '数据不可用';
          }
        }
      }
      
      row.appendChild(cell);
    });
    
    tableBody.appendChild(row);
  });
  
  // 显示数据加载状态和排序信息
  const statusElement = document.getElementById('data-status');
  if (statusElement) {
    const availableCount = data.filter(item => item.any_data_available).length;
    const sortInfo = availableStats[sortPeriod] > 0 ? `(按${sortPeriod}排序)` : '';
    statusElement.textContent = `已加载 ${availableCount}/${data.length} 个交易对的数据 ${sortInfo}`;
    
    // 添加时间段可用性信息
    const availabilityInfo = periods.map(p => 
      `${p}: ${availableStats[p]}/${data.length} (${Math.round(availableStats[p]/data.length*100)}%)`
    ).join(' | ');
    
    const dataAvailabilityElement = document.getElementById('data-availability');
    if (dataAvailabilityElement) {
      dataAvailabilityElement.textContent = availabilityInfo;
    }
    
    // 更新数据时间信息
    const dataTimeElement = document.getElementById('data-time');
    if (dataTimeElement) {
      const now = new Date();
      dataTimeElement.textContent = `更新时间: ${now.toLocaleTimeString()}`;
    }
  }
}

/**
 * 初始化价格变化监控
 */
async function initPriceChangeMonitor() {
  // 首次加载数据
  let data = await fetchPriceChangeData();
  renderPriceChangeTable(data);
  
  // 设置定时刷新
  setInterval(async () => {
    data = await fetchPriceChangeData();
    renderPriceChangeTable(data);
  }, 5000); // 每5秒刷新一次
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initPriceChangeMonitor);

// CSS 样式示例
/*
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

.loading {
  color: #999;
  font-style: italic;
}
*/ 