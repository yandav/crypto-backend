/**
 * 集中配置文件 - 方便在不同环境之间切换
 * 
 * 使用方法:
 * 1. 复制此文件为 config.local.js 进行本地配置
 * 2. 修改下面的配置项以适应你的环境
 * 3. 本地开发和测试时使用此配置
 */
// #postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor
// #postgresql://yandavi_mc67_user:JsQWGa8gStDxawz2OIHsrmUnqgDLJAnS@dpg-d0ssul6mcj7s73fcco6g-a/yandavi_mc67
// DATABASE_URL = "postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor"
//http://127.0.0.1:5000
//https://crypto-backend-2.onrender.com
//https://crypto-backend-4973.vercel.app


// 当前环境
const ENV = {
  DEV: 'development',      // 本地开发环境
  TEST: 'test',            // 本地测试环境
  PROD: 'production'       // 生产环境
};

// 当前激活的环境
const CURRENT_ENV = ENV.DEV;

// 各环境配置
const config = {
  // 开发环境配置
  [ENV.DEV]: {
    // 后端API地址
    apiBaseUrl: 'http://localhost:5000',
    
    // 数据库配置
    database: {
      url: 'postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor',
      poolSize: 5,
      maxOverflow: 10,
      poolTimeout: 60,
      poolRecycle: 3600
    },
    
    // API配置
    api: {
      rateLimit: 100,
      timeout: 30
    },
    
    // 数据清理配置
    dataRetention: {
      days: 30
    },
    
    // 定时任务配置
    scheduler: {
      priceUpdateInterval: 1,
      openInterestUpdateInterval: 1
    },
    
    // CORS配置
    cors: {
      origin: 'http://localhost:5173'
    },
    
    // 服务配置
    server: {
      port: 5000,
      debug: true
    }
  },
  
  // 测试环境配置
  [ENV.TEST]: {
    apiBaseUrl: 'http://localhost:5000',
    
    database: {
      url: 'postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor_test',
      poolSize: 5,
      maxOverflow: 10,
      poolTimeout: 60,
      poolRecycle: 3600
    },
    
    api: {
      rateLimit: 100,
      timeout: 30
    },
    
    dataRetention: {
      days: 30
    },
    
    scheduler: {
      priceUpdateInterval: 1,
      openInterestUpdateInterval: 1
    },
    
    cors: {
      origin: 'http://localhost:5173'
    },
    
    server: {
      port: 5000,
      debug: true
    }
  },
  
  // 生产环境配置
  [ENV.PROD]: {
    apiBaseUrl: 'https://crypto-backend-2.onrender.com',
    
    database: {
      // 在生产环境中使用环境变量
      url: process.env.DATABASE_URL || 'postgresql://yandavi_fvr5_user:aeWKcZlTTY6YNvD3cOFVqZxPJZ7VSJSO@dpg-d10pbj6mcj7s73buf9n0-a/yandavi_fvr5',
      poolSize: 5,
      maxOverflow: 10,
      poolTimeout: 60,
      poolRecycle: 3600
    },
    
    api: {
      rateLimit: 100,
      timeout: 30
    },
    
    dataRetention: {
      days: 30
    },
    
    scheduler: {
      priceUpdateInterval: 5,  // 生产环境更新频率降低
      openInterestUpdateInterval: 10
    },
    
    cors: {
      origin: 'https://crypto-backend-4973.vercel.app'
    },
    
    server: {
      port: process.env.PORT || 5000,
      debug: false
    }
  }
};

// 导出当前环境的配置
module.exports = config[CURRENT_ENV];

// 导出所有配置和环境变量，方便切换
module.exports.allConfigs = config;
module.exports.environments = ENV;
module.exports.currentEnv = CURRENT_ENV;

// 切换环境的辅助函数
module.exports.switchEnv = function(env) {
  if (config[env]) {
    console.log(`切换到${env}环境配置`);
    return config[env];
  } else {
    console.error(`环境${env}不存在，使用${CURRENT_ENV}环境配置`);
    return config[CURRENT_ENV];
  }
}; 