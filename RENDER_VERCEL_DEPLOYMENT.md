# Render + Vercel 部署指南

## 准备工作

1. 注册 [Render](https://render.com) 账号
2. 注册 [Vercel](https://vercel.com) 账号
3. 创建一个 PostgreSQL 数据库服务
   - 在 Render Dashboard 中选择 "New" > "PostgreSQL"
   - 填写名称，如 "crypto-monitor-db"
   - 选择合适的计划（免费计划有限制）
   - 创建后，记下内部连接字符串

## 后端部署 (Render)

1. 在 Render Dashboard 中选择 "New" > "Web Service"
2. 连接你的 GitHub 仓库
3. 配置服务：
   - 名称：crypto-api
   - 根目录：backend
   - 环境：Python
   - 构建命令：`pip install -r requirements.txt && chmod +x startup.sh`
   - 启动命令：`./startup.sh`
   - 高级设置中添加环境变量：
     - `DATABASE_URL`：使用之前创建的 PostgreSQL 数据库的内部连接字符串
     - `CORS_ORIGIN`：设置为你的 Vercel 前端 URL (例如 https://crypto-monitor.vercel.app)
     - 其他环境变量已在 render.yaml 中配置

## 前端部署 (Vercel)

1. 在 Vercel Dashboard 中点击 "New Project"
2. 导入你的 GitHub 仓库
3. 配置项目：
   - 框架预设：Vue.js
   - 根目录：frontend/crypto-monitor-vue
   - 构建命令：`npm run build`
   - 输出目录：dist
   - 环境变量：
     - `VITE_API_URL`：设置为你的 Render 后端 API URL (例如 https://crypto-api.onrender.com)

## 注意事项

1. **数据库连接**：
   - 确保后端的 `DATABASE_URL` 环境变量正确设置为 Render PostgreSQL 数据库的连接字符串
   - Render 的 PostgreSQL 连接字符串格式为 `postgres://user:password@host:port/database`，代码中已添加自动转换为 SQLAlchemy 支持的格式

2. **CORS 配置**：
   - 确保在后端设置了正确的 `CORS_ORIGIN` 环境变量，指向你的 Vercel 前端 URL
   - 这样可以防止跨域请求问题

3. **API URL 配置**：
   - 确保在 Vercel 前端设置了正确的 `VITE_API_URL` 环境变量，指向你的 Render 后端 URL

4. **服务限制**：
   - Render 免费计划的 Web 服务在 15 分钟无活动后会休眠，首次访问可能需要等待几秒钟启动
   - Render 免费计划的 PostgreSQL 数据库有 90 天的有效期，之后需要创建新的数据库
   - Vercel 的免费计划对于个人项目通常足够使用，但有一些构建时间和带宽限制

5. **监控与日志**：
   - 部署后，定期检查 Render 和 Vercel 的日志，确保服务正常运行
   - 设置监控提醒，以便在服务出现问题时及时通知

6. **数据库备份**：
   - 定期备份 Render PostgreSQL 数据库，以防数据丢失
   - 可以设置自动备份计划或手动导出数据 