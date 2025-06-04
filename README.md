# Crypto Monitor

加密货币监控系统，支持价格、持仓量和资金费率监控。

## 配置说明

本项目使用集中配置文件管理不同环境的配置，方便在本地开发、测试和生产环境之间切换。

### 配置文件

主要配置文件：

- `config.js` - 默认配置文件，包含开发、测试和生产环境的配置
- `config.local.js` - 本地配置文件（需自行创建，不提交到版本控制）
- `frontend/crypto-monitor-vue/src/config.js` - 前端配置文件
- `backend/config.env.example` - 后端环境变量示例文件

### 本地开发配置

1. 复制默认配置文件创建本地配置：

```bash
cp config.js config.local.js
```

2. 编辑 `config.local.js` 文件，根据需要修改配置项：

```javascript
// 修改当前环境
const CURRENT_ENV = ENV.DEV;  // 可选：ENV.DEV, ENV.TEST, ENV.PROD

// 修改数据库连接
config[ENV.DEV].database.url = 'postgresql+psycopg2://postgres:你的密码@localhost:5432/crypto_monitor';

// 修改API地址
config[ENV.DEV].apiBaseUrl = 'http://localhost:5000';
```

3. 前端开发环境配置在 `.env.development` 文件中

### 环境切换

项目支持三种环境：

1. **开发环境 (DEV)** - 用于本地开发
2. **测试环境 (TEST)** - 用于本地测试
3. **生产环境 (PROD)** - 用于生产部署

通过修改 `config.local.js` 中的 `CURRENT_ENV` 变量来切换环境。

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 前端启动

```bash
cd frontend/crypto-monitor-vue
npm install
npm run dev
```

## 部署

### 本地测试部署

1. 修改 `config.local.js` 中的 `CURRENT_ENV` 为 `ENV.PROD`
2. 启动后端：`cd backend && python app.py`
3. 构建前端：`cd frontend/crypto-monitor-vue && npm run build`
4. 使用任意静态文件服务器提供前端服务

### Render + Vercel 部署

详见 [RENDER_VERCEL_DEPLOYMENT.md](RENDER_VERCEL_DEPLOYMENT.md) 文件。 