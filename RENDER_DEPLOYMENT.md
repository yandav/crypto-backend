# Render 部署指南

## 准备工作

1. 注册 [Render](https://render.com) 账号
2. 创建一个 PostgreSQL 数据库服务
   - 在 Render Dashboard 中选择 "New" > "PostgreSQL"
   - 填写名称，如 "crypto-monitor-db"
   - 选择合适的计划（免费计划有限制）
   - 创建后，记下内部连接字符串

## 后端部署

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
     - 其他环境变量已在 render.yaml 中配置

## 前端部署

1. 在 Render Dashboard 中选择 "New" > "Web Service"
2. 连接你的 GitHub 仓库
3. 配置服务：
   - 名称：crypto-monitor-frontend
   - 根目录：frontend
   - 环境：Node
   - 构建命令：`cd crypto-monitor-vue && npm install && npm run build`
   - 发布目录：crypto-monitor-vue/dist
   - 高级设置中添加环境变量：
     - `VITE_API_URL`：后端服务的完整 URL（例如 https://crypto-api.onrender.com）

## 注意事项

1. 确保后端的 `DATABASE_URL` 环境变量正确设置为 Render PostgreSQL 数据库的连接字符串
2. 确保前端的 `VITE_API_URL` 环境变量正确设置为后端服务的 URL
3. 免费计划的 Web 服务在 15 分钟无活动后会休眠，首次访问可能需要等待几秒钟启动
4. 免费计划的 PostgreSQL 数据库有 90 天的有效期，之后需要创建新的数据库 