from flask import Flask, jsonify
from flask_cors import CORS
from binance_api import fetch_all_data
from indicators import append_ema
from alerts import check_ema_alerts, check_price_change_alerts, check_open_interest_alerts
from database import save_data, get_latest_data
from open_interest import get_open_interest_data
import asyncio
from db import get_price_change
import os


app = Flask(__name__)
CORS(app)

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
        data = asyncio.run(get_open_interest_data())  # ✅ 正确调用异步函数
        alerts = check_open_interest_alerts(data)
        return jsonify({"message": "成功获取", "data": data, "alerts": alerts})
    except Exception as e:
        print("❌ open_interest 接口错误:", e)  # 建议加上打印
        return jsonify({"message": "获取失败", "error": str(e), "data": []}), 500

@app.route("/api/price_change", methods=["GET"])
def get_price_change_api():
    try:
        current_data = fetch_all_data()  # 最新价格
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

@app.route('/')
def index():
    return "Hello from Render!"


#if __name__ == "__main__":
#    app.run(debug=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # 读取 PORT 环境变量，Render 会提供
    app.run(host='0.0.0.0', port=port, debug=True)