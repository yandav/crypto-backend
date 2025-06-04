/**
 * 前端配置文件 - 集中管理各环境的配置
 */

// 环境类型
export const ENV = {
  DEV: 'development',      // 本地开发环境
  TEST: 'test',            // 本地测试环境
  PROD: 'production'       // 生产环境
};

// 获取当前环境
const getEnv = () => {
  if (import.meta.env.MODE === 'development') {
    return ENV.DEV;
  } else if (import.meta.env.VITE_ENV === 'test') {
    return ENV.TEST;
  } else {
    return ENV.PROD;
  }
};

const CURRENT_ENV = getEnv();

// 各环境配置
const config = {
  // 开发环境配置
  [ENV.DEV]: {
    // API基础URL
    apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:5000',
    
    // 请求超时时间（毫秒）
    apiTimeout: 10000,
    
    // 是否启用调试工具
    debug: true,
    
    // 是否启用源码映射
    sourcemap: true,
    
    // 数据刷新间隔（毫秒）
    refreshInterval: 30000
  },
  
  // 测试环境配置
  [ENV.TEST]: {
    apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:5000',
    apiTimeout: 10000,
    debug: true,
    sourcemap: true,
    refreshInterval: 30000
  },
  
  // 生产环境配置
  [ENV.PROD]: {
    apiBaseUrl: import.meta.env.VITE_API_URL || 'https://crypto-api.onrender.com',
    apiTimeout: 15000,
    debug: false,
    sourcemap: import.meta.env.VITE_ENABLE_SOURCEMAP === 'true',
    refreshInterval: 60000
  }
};

// 当前环境的配置
const currentConfig = config[CURRENT_ENV];

// 导出配置
export default {
  ...currentConfig,
  env: CURRENT_ENV,
  isProduction: CURRENT_ENV === ENV.PROD,
  isDevelopment: CURRENT_ENV === ENV.DEV,
  isTest: CURRENT_ENV === ENV.TEST
}; 