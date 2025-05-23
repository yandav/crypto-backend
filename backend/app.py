from flask import Flask, jsonify
from flask_cors import CORS
from binance_api import fetch_all_data, get_open_interest_data
from indicators import append_ema
from alerts import check_ema_alerts, check_price_change_alerts, check_open_interest_alerts
from database import save_data, get_latest_data, get_price_change
from db import save_price_bulk, create_tables, SessionLocal, OpenInterest, PriceHistory
import asyncio
import threading
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)

# ✅ 持仓量锁
open_interest_lock = threading.Lock()

# ✅ 价格数据定时更新任务
def update_price_data():
    try:
        print("📈 正在抓取价格数据...")
        start = time.time()
        price_data = fetch_all_data()
        db_data = [{
            "symbol": item["symbol"],
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            "price": item["price"]
        } for item in price_data]
        save_price_bulk(db_data)
        print(f"✅ 价格数据已保存，用时 {time.time() - start:.2f}s")
    except Exception as e:
        print("❌ 价格数据保存失败:", e)

# ✅ 持仓量数据定时更新任务（防止重复运行）
def update_open_interest_data():
    if open_interest_lock.locked():
        print("⚠️ 上一个持仓量任务仍在运行，跳过")
        return

    with open_interest_lock:
        try:
            print(f"📊 正在抓取持仓量数据 @ {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_open_interest_data())
            loop.close()
            print("✅ 持仓量数据已成功更新")
        except Exception as e:
            print("❌ 持仓量数据抓取失败:", e)

# ✅ 定时任务
scheduler = BackgroundScheduler()
scheduler.add_job(update_price_data, 'interval', minutes=1, id='update_price_data', max_instances=1, coalesce=True)
scheduler.add_job(update_open_interest_data, 'interval', minutes=1, id='update_open_interest_data', max_instances=1, coalesce=True)
scheduler.start()

# ✅ 实时数据接口（价格 + EMA + EMA 警报）
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

# ✅ 历史价格数据
@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(get_latest_data())

# ✅ 实时持仓量 + 报警
@app.route("/api/open_interest", methods=["GET"])
def get_open_interest():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(get_open_interest_data())
        loop.close()
        alerts = check_open_interest_alerts(data)
        return jsonify({"message": "成功获取", "data": data, "alerts": alerts})
    except Exception as e:
        print("❌ open_interest 接口错误:", e)
        return jsonify({"message": "获取失败", "error": str(e), "data": []}), 500

# ✅ 涨跌幅监控
@app.route("/api/price_change", methods=["GET"])
def get_price_change_api():
    try:
        current_data = fetch_all_data()
        result = []

        for item in current_data:
            symbol = item['symbol']
            current_price = item['price']
            price_1m = get_price_change(symbol, 1)
            price_2m = get_price_change(symbol, 2)
            price_5m = get_price_change(symbol, 5)
            price_20m = get_price_change(symbol, 20)
            price_40m = get_price_change(symbol, 40)
            price_1h = get_price_change(symbol, 60)

            def change(old):
                if not old or old == 0: return 0
                return round((current_price - old) / old * 100, 2)

            result.append({
                "symbol": symbol,
                "price": current_price,
                "change": {
                    "1m": change(price_1m),
                    "2m": change(price_2m),
                    "5m": change(price_5m),
                    "20m": change(price_20m),
                    "40m": change(price_40m),
                    "1h": change(price_1h),
                }
            })

        return jsonify({"message": "成功", "data": result})
    except Exception as e:
        return jsonify({"message": "失败", "error": str(e)})

# ✅ Render 首页测试
@app.route('/')
def index():
    return "Hello from Render!"

# ✅ 调试：最近5条持仓量
@app.route("/debug/oi")
def debug_oi():
    session = SessionLocal()
    results = session.query(OpenInterest).order_by(OpenInterest.timestamp.desc()).limit(5).all()
    return jsonify([
        {
            "symbol": r.symbol,
            "oi": r.open_interest,
            "change": r.change_pct,
            "ts": r.timestamp.isoformat()
        } for r in results
    ])

# ✅ 调试：最近10条价格历史
@app.route("/debug/history")
def debug_history():
    session = SessionLocal()
    results = session.query(PriceHistory).order_by(PriceHistory.timestamp.desc()).limit(10).all()
    return jsonify([
        {
            "symbol": r.symbol,
            "price": r.price,
            "ts": r.timestamp.isoformat()
        } for r in results
    ])

# ✅ 启动入口
if __name__ == '__main__':
    create_tables()                      # 自动建表
    update_price_data()                 # 启动时跑一次
    update_open_interest_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
