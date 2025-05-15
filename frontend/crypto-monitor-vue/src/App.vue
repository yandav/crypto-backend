<template>
  <div class="container">
    <h1>虚拟货币监控系统</h1>

    <nav>
      <RouterLink to="/">📊 市场总览</RouterLink> |
      <RouterLink to="/ema-alerts">📡 EMA 警报</RouterLink> |
      <RouterLink to="/change-alerts">⚠️ 涨跌幅警报</RouterLink> |
      <RouterLink to="/open-interest">🧮 持仓量监控</RouterLink> |
      <RouterLink to="/price-change">🚨 涨跌幅监控</RouterLink> |
    </nav>

    <router-view />
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<style>
.container {
  max-width: 1000px;
  margin: auto;
  padding: 2rem;
  font-family: Arial, sans-serif;
}
nav {
  margin-bottom: 1rem;
}
nav a {
  margin-right: 1rem;
  text-decoration: none;
  color: blue;
}
</style>
