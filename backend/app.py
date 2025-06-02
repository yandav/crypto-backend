#app.py

from flask import Flask, jsonify
from flask_cors import CORS
from binance_api import BinanceAPI, get_open_interest_data
from indicators import append_ema
from alerts import check_ema_alerts, check_price_change_alerts, check_open_interest_alerts
from database import (
    save_prices,
    get_latest_data,
    get_price_history,
    init_db,
    cleanup_old_data
)
from middleware import rate_limit, log_request, error_handler
from config import config
import asyncio
import os
import time
import logging

from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def run_async(coro):
    """运行异步任务的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ✅ 定时任务：更新价格数据
def update_price_data():
    try:
        logger.info("📈 正在抓取价格数据...")
        start = time.time()
        
        market_data = run_async(BinanceAPI.fetch_market_data())
        db_data = [{
            "symbol": item.symbol,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            "price": item.price
        } for item in market_data]
        
        save_prices(db_data)
        logger.info(f"✅ 价格数据已保存，用时 {time.time() - start:.2f}s")
    except Exception as e:
        logger.error(f"❌ 价格数据保存失败: {str(e)}", exc_info=True)

# ✅ 定时任务：更新持仓量数据（自动保存）
open_interest_lock = asyncio.Lock()

def update_open_interest_data():
    try:
        logger.info("📊 正在抓取持仓量数据...")
        start = time.time()
        
        run_async(get_open_interest_data())
        logger.info(f"✅ 持仓量数据已抓取并保存，用时 {time.time() - start:.2f}s")
    except Exception as e:
        logger.error(f"❌ 持仓量数据保存失败: {str(e)}", exc_info=True)

# ✅ 定时器启动
scheduler = BackgroundScheduler(
    job_defaults={
        'max_instances': 1,
        'coalesce': True,
        'misfire_grace_time': 60
    }
)
scheduler.add_job(
    update_price_data,
    'interval',
    minutes=config.PRICE_UPDATE_INTERVAL,
    id='update_price_data'
)
scheduler.add_job(
    update_open_interest_data,
    'interval',
    minutes=config.OPEN_INTEREST_UPDATE_INTERVAL,
    id='update_open_interest_data'
)

# 确保程序退出时关闭调度器
atexit.register(lambda: scheduler.shutdown())

scheduler.start()

# ✅ 实时数据接口
@app.route("/api/data", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_data():
    market_data = run_async(BinanceAPI.fetch_market_data())
    data = append_ema([{
        "symbol": item.symbol,
        "price": item.price,
        "change": item.change_24h,
        "volume": item.volume,
        "fundingRate": item.funding_rate
    } for item in market_data])
    
    # 保存数据
    db_data = [{
        "symbol": item["symbol"],
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
        "price": item["price"]
    } for item in data]
    save_prices(db_data)
    
    alerts = {
        "ema_alerts": check_ema_alerts(data),
        "change_alerts": check_price_change_alerts(data)
    }
    return jsonify({"message": "成功获取", "data": data, "alerts": alerts})

# ✅ 实时持仓量接口
@app.route("/api/open_interest", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_open_interest():
    result = run_async(get_open_interest_data())
    return jsonify({"message": "成功获取", "data": result})

# ✅ 涨跌幅接口
@app.route("/api/price_change", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_price_change_api():
    market_data = run_async(BinanceAPI.fetch_market_data())
    result = []

    for item in market_data:
        symbol = item.symbol
        current_price = item.price
        price_1m = get_price_history(symbol, 1)
        price_2m = get_price_history(symbol, 2)
        price_5m = get_price_history(symbol, 5)
        price_20m = get_price_history(symbol, 20)
        price_40m = get_price_history(symbol, 40)
        price_1h = get_price_history(symbol, 60)

        def change(old):
            if not old or old == 0:
                return 0
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

# ✅ 启动入口
if __name__ == '__main__':
    init_db()
    update_price_data()
    update_open_interest_data()
    # 每天清理30天前的数据
    scheduler.add_job(
        lambda: cleanup_old_data(config.DATA_RETENTION_DAYS),
        'cron',
        hour=0,
        minute=0
    )
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
