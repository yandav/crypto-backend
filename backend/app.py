# app.py
from flask import Flask, jsonify
from flask_cors import CORS
from binance_api import fetch_all_data, get_open_interest_data
from indicators import append_ema
from alerts import check_ema_alerts, check_price_change_alerts, check_open_interest_alerts
from database import save_data, get_latest_data
from db import save_price_history, save_open_interest_data, get_price_change
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import os

app = Flask(__name__)
CORS(app)

# ✅ 异步执行数据更新
def update_data():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        try:
            print("⏰ 正在抓取并保存价格和持仓量数据...")
            price_data = fetch_all_data()
            save_price_history(price_data)

            oi_data = await get_open_interest_data()
            save_open_interest_data(oi_data)
            print("✅ 数据已保存")
        except Exception as e:
            print("❌ 定时任务失败:", e)

    loop.run_until_complete(run())
    loop.close()

# ✅ 创建调度器（防止多任务冲突，设置 max_instances）
scheduler = BackgroundScheduler()
scheduler.add_job(update_data, 'interval', minutes=1, max_instances=1)
scheduler.start()

@app.route("/api/data", methods=["GET"])
def get_data():
    try:
        raw_data = fetch_all_data()
        data = append_ema(raw_data)
        save_data(data)

        alerts = {
            "ema_alerts": check_ema_alerts(data),
            "change_alerts": check_price_change_alerts(data)
        }
        return jsonify({"message": "成功获取", "data": data, "alerts": alerts})
    except Exception as e:
        print("❌ 数据抓取失败:", str(e))
        return jsonify({"message": "抓取失败", "data": [], "alerts": {}})

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(get_latest_data())

@app.route("/api/open_interest", methods=["GET"])
def get_open_interest():
    try:
        data = asyncio.run(get_open_interest_data())
        alerts = check_open_interest_alerts(data)
        return jsonify({"message": "成功获取", "data": data, "alerts": alerts})
    except Exception as e:
        print("❌ open_interest 接口错误:", e)
        return jsonify({"message": "获取失败", "error": str(e), "data": []}), 500

@app.route("/api/price_change", methods=["GET"])
def get_price_change_api():
    try:
        current_data = fetch_all_data()
        result = []

        for item in current_data:
            symbol = item['symbol']
            current_price = item['price']
            def change(old):
                if not old or old == 0: return 0
                return round((current_price - old) / old * 100, 2)

            result.append({
                "symbol": symbol,
                "price": current_price,
                "change": {
                    "1m": change(get_price_change(symbol, 1)),
                    "2m": change(get_price_change(symbol, 2)),
                    "5m": change(get_price_change(symbol, 5)),
                    "20m": change(get_price_change(symbol, 20)),
                    "40m": change(get_price_change(symbol, 40)),
                    "1h": change(get_price_change(symbol, 60)),
                }
            })

        return jsonify({"message": "成功", "data": result})
    except Exception as e:
        return jsonify({"message": "失败", "error": str(e)})

@app.route('/')
def index():
    return "Hello from Render!"

if __name__ == '__main__':
    update_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
