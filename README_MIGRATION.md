# 数据库迁移说明

## 问题描述
在 Render 上部署时，可能会出现以下错误：
```
WARNING:database:从 price 表查询失败: (psycopg2.errors.UndefinedTable) relation "price" does not exist
```

这是因为数据库表名不一致导致的问题。在代码中，有些地方使用 `price` 表名，有些地方使用 `prices` 表名。

## 解决方案
我们已经更新了代码，使所有地方都使用 `prices` 表名，并且添加了一个迁移脚本，可以自动将现有的 `price` 表重命名为 `prices`。

## 在 Render 上运行迁移
1. 登录到 Render 控制台
2. 进入你的 Web 服务
3. 点击 "Shell" 选项卡
4. 在 Shell 中运行以下命令：
```bash
python run_migration.py
```

这将自动检查数据库中的表，并进行必要的迁移。

## 本地测试
如果你想在本地测试迁移，可以运行：
```bash
python -m backend.migrate_db
```

## 迁移内容
1. 检查 `open_interest` 表是否有 `funding_rate` 列，如果没有则添加
2. 检查是否存在 `price` 表，如果存在则将其重命名为 `prices`

## 代码更改
1. 所有代码中的 `price` 表名已更改为 `prices`
2. 所有查询也已更新为使用 `prices` 表名 