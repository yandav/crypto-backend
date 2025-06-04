<template>
  <div class="app-container">
    <header class="app-header">
    <h1>虚拟货币监控系统</h1>
      <div class="app-version">v0.1.0</div>
    </header>

    <nav class="app-nav">
      <RouterLink to="/" class="nav-item">
        <i class="nav-icon">📊</i>
        <span>市场总览</span>
      </RouterLink>
      <RouterLink to="/ema-alerts" class="nav-item">
        <i class="nav-icon">📡</i>
        <span>EMA 警报</span>
      </RouterLink>
      <RouterLink to="/change-alerts" class="nav-item">
        <i class="nav-icon">⚠️</i>
        <span>涨跌幅警报</span>
      </RouterLink>
      <RouterLink to="/open-interest" class="nav-item">
        <i class="nav-icon">🧮</i>
        <span>持仓量监控</span>
      </RouterLink>
      <RouterLink to="/price-change" class="nav-item">
        <i class="nav-icon">🚨</i>
        <span>涨跌幅监控</span>
      </RouterLink>
      <RouterLink to="/trade-monitor" class="nav-item">
        <i class="nav-icon">👨‍💼</i>
        <span>跟单监控</span>
      </RouterLink>
    </nav>

    <main class="app-content">
    <router-view />
    </main>

    <footer class="app-footer">
      <p>© 2024 虚拟货币监控系统 - 数据仅供参考，不构成投资建议</p>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<style>
:root {
  --primary-color: #3498db;
  --secondary-color: #2c3e50;
  --accent-color: #e74c3c;
  --bg-color: #f8f9fa;
  --text-color: #333;
  --border-color: #ddd;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  background-color: var(--bg-color);
  color: var(--text-color);
  line-height: 1.6;
}

.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.app-version {
  font-size: 0.8rem;
  color: #666;
  background-color: #eee;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.app-nav {
  display: flex;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 2rem;
  padding: 0.5rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  text-decoration: none;
  color: var(--secondary-color);
  border-radius: 4px;
  transition: background-color 0.2s, color 0.2s;
}

.nav-item:hover {
  background-color: #eef2f7;
}

.nav-item.router-link-active {
  background-color: var(--primary-color);
  color: white;
}

.nav-icon {
  margin-right: 0.5rem;
  font-size: 1.2rem;
}

.app-content {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  min-height: 60vh;
}

.app-footer {
  margin-top: 2rem;
  padding-top: 1rem;
  text-align: center;
  font-size: 0.9rem;
  color: #666;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 768px) {
  .app-nav {
    flex-direction: column;
  }
  
  .app-content {
    padding: 1rem;
  }
}
</style>
