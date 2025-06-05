#app.py

from flask import Flask, jsonify, request
from flask_cors import CORS
from binance_api import BinanceAPI, get_open_interest_data
from indicators import append_ema
from alerts import check_ema_alerts, check_price_change_alerts, check_open_interest_alerts
from database import (
    save_prices,
    get_latest_data,
    get_price_history,
    get_closest_price_history,
    get_available_price_history,
    init_db,
    cleanup_old_data,
    get_db_session
)
from models import Price, OpenInterest, Trader, Trade
from middleware import rate_limit, log_request, error_handler
from config import config
from trade_notification import check_new_trades  # 导入交易通知模块
import asyncio
import os
import time
import logging
import threading
import concurrent.futures
import traceback
from datetime import datetime, timedelta
from functools import lru_cache
from sqlalchemy.sql import func, desc

from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置CORS
cors_origins = os.getenv('CORS_ORIGINS', 'https://crypto-backend-4973.vercel.app')
# 如果环境变量中有多个域名，用逗号分隔
origins = cors_origins.split(',')
CORS(app, resources={r"/api/*": {"origins": origins}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# 线程本地存储，为每个线程提供独立的事件循环
_thread_local = threading.local()

def get_event_loop():
    """获取当前线程的事件循环，如果不存在则创建一个新的"""
    if not hasattr(_thread_local, 'loop') or _thread_local.loop is None or _thread_local.loop.is_closed():
        _thread_local.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_thread_local.loop)
    return _thread_local.loop

def run_async(coro):
    """运行异步任务的辅助函数，为每个请求创建新的事件循环"""
    loop = None
    try:
        # 在Flask的多线程环境中，每次请求都需要一个新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        if loop:
            loop.close()

# 线程池执行器，用于后台任务
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def run_async_in_thread(coro):
    """在独立线程中运行异步任务"""
    def _run_async():
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            if loop:
                # 确保关闭所有未完成的任务
                pending = asyncio.all_tasks(loop) if hasattr(asyncio, 'all_tasks') else asyncio.Task.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # 运行一次事件循环，让取消的任务有机会完成
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                loop.close()
    
    # 在新线程中执行异步任务
    return executor.submit(_run_async).result()

# 缓存最近的价格数据（30秒过期）
price_change_cache = {}
price_change_cache_time = None
price_change_cache_lock = threading.Lock()

def get_cached_price_change(max_age_seconds=30):
    """获取缓存的价格变化数据，如果过期则返回None"""
    with price_change_cache_lock:
        global price_change_cache, price_change_cache_time
        if price_change_cache_time is None:
            return None
        
        age = (datetime.now() - price_change_cache_time).total_seconds()
        if age > max_age_seconds:
            return None
            
        return price_change_cache

def set_price_change_cache(data):
    """设置价格变化缓存"""
    with price_change_cache_lock:
        global price_change_cache, price_change_cache_time
        price_change_cache = data
        price_change_cache_time = datetime.now()

# ✅ 定时任务：更新价格数据
def update_price_data():
    try:
        logger.info("📈 正在抓取价格数据...")
        start = time.time()
        
        # 在独立线程中执行异步任务
        market_data = run_async_in_thread(BinanceAPI.fetch_market_data())
        
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
open_interest_lock = threading.Lock()

def update_open_interest_data():
    try:
        logger.info("📊 正在抓取持仓量数据...")
        start = time.time()
        
        # 在独立线程中执行异步任务
        run_async_in_thread(get_open_interest_data())
        
        logger.info(f"✅ 持仓量数据已抓取并保存，用时 {time.time() - start:.2f}s")
    except Exception as e:
        logger.error(f"❌ 持仓量数据保存失败: {str(e)}", exc_info=True)

# ✅ 定时任务：预计算价格变化数据
def precalculate_price_change():
    try:
        logger.info("🔄 正在预计算价格变化数据...")
        start = time.time()
        
        # 获取最新的市场数据
        market_data = run_async_in_thread(BinanceAPI.fetch_market_data())
        
        # 计算价格变化
        result = calculate_price_changes(market_data)
        
        # 更新缓存
        set_price_change_cache(result)
        
        logger.info(f"✅ 价格变化数据已预计算，用时 {time.time() - start:.2f}s")
    except Exception as e:
        logger.error(f"❌ 价格变化数据预计算失败: {str(e)}", exc_info=True)

# ✅ 定时任务：更新交易数据
def update_trade_data():
    try:
        logger.info("📊 正在更新交易数据...")
        start = time.time()
        
        # 导入交易爬虫模块
        from trade_scraper import AoyingCapitalScraper
        
        # 使用真实爬虫，允许在失败时回退到模拟数据
        scraper = AoyingCapitalScraper(fallback_to_mock=True)
        saved_count = run_async_in_thread(scraper.update_trades())
        
        logger.info(f"✅ 交易数据已更新，新增/更新 {saved_count} 条记录，用时 {time.time() - start:.2f}s")
    except Exception as e:
        logger.error(f"❌ 交易数据更新失败: {str(e)}", exc_info=True)

# ✅ 定时任务：更新热门交易员数据
def update_popular_traders_data():
    try:
        logger.info("📊 正在更新热门交易员数据...")
        start = time.time()
        
        # 导入热门交易员爬虫模块
        from popular_traders_scraper import PopularTradersScraper
        
        # 使用热门交易员爬虫
        scraper = PopularTradersScraper(fallback_to_mock=True)
        saved_count = run_async_in_thread(scraper.update_trades())
        
        logger.info(f"✅ 热门交易员数据已更新，新增/更新 {saved_count} 条记录，用时 {time.time() - start:.2f}s")
    except Exception as e:
        logger.error(f"❌ 热门交易员数据更新失败: {str(e)}", exc_info=True)

def calculate_price_changes(market_data):
    """计算价格变化，直接使用最新的市场数据，立即返回已有数据"""
    result = []
    
    # 标准时间段（分钟）
    standard_periods = {
        "1m": 1,
        "2m": 2,
        "5m": 5,
        "20m": 20,
        "40m": 40,
        "1h": 60
    }
    
    for item in market_data:
        try:
            symbol = item.symbol
            current_price = item.price
            
            # 创建价格变化对象，包含可用性标志
            change_data = {}
            
            # 获取该交易对的所有可用历史数据点
            available_history = get_available_price_history(symbol)
            
            # 处理每个标准时间段
            for period_name, minutes in standard_periods.items():
                # 初始化为不可用
                change_data[period_name] = {"value": 0, "available": False}
                
                # 方法1：尝试精确匹配
                exact_price = get_price_history(symbol, minutes)
                if exact_price:
                    change_value = round((current_price - exact_price) / exact_price * 100, 2)
                    change_data[period_name] = {
                        "value": change_value,
                        "available": True,
                        "method": "exact"
                    }
                    continue
                
                # 方法2：尝试找最接近的数据点（允许5分钟误差）
                tolerance = min(5, minutes // 2 + 1)  # 容差不超过5分钟，且不超过时间段的一半
                closest_data = get_closest_price_history(symbol, minutes, tolerance)
                if closest_data:
                    old_price = closest_data["price"]
                    change_value = round((current_price - old_price) / old_price * 100, 2)
                    change_data[period_name] = {
                        "value": change_value,
                        "available": True,
                        "method": "closest",
                        "actual_minutes": round(closest_data["actual_minutes_ago"], 1),
                        "time_diff": round(closest_data["time_diff"], 1)
                    }
                    continue
                
                # 方法3：如果是1小时且有24小时变化率，使用估计值
                if period_name == "1h" and item.change_24h is not None:
                    change_data[period_name] = {
                        "value": round(item.change_24h / 24, 2),
                        "available": False,
                        "estimated": True,
                        "method": "estimated"
                    }
            
            # 添加数据可用性摘要
            available_periods = [k for k, v in change_data.items() if v.get("available", False)]
            
            # 添加最早可用数据点信息
            earliest_data_point = None
            if available_history:
                earliest_minutes = max(available_history.keys())
                if earliest_minutes > 0:
                    earliest_data_point = {
                        "minutes_ago": earliest_minutes,
                        "price": available_history[earliest_minutes]
                    }
            
            result.append({
                "symbol": symbol,
                "price": current_price,
                "change": change_data,
                "available_periods": available_periods,
                "any_data_available": len(available_periods) > 0,
                "earliest_data_point": earliest_data_point,
                "data_points_count": len(available_history)
            })
        except Exception as e:
            logger.error(f"处理 {item.symbol} 的价格变化数据时出错: {str(e)}")
            logger.error(traceback.format_exc())
            # 继续处理下一个交易对
            continue
    
    return result

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
    minutes=5,
    id='update_price_data'
)
scheduler.add_job(
    update_open_interest_data,
    'interval',
    minutes=10,  # 增加到10分钟更新一次
    id='update_open_interest_data'
)
scheduler.add_job(
    precalculate_price_change,
    'interval',
    minutes=2,  # 每2分钟预计算一次价格变化
    id='precalculate_price_change'
)
scheduler.add_job(
    update_trade_data,
    'interval',
    minutes=5,  # 每5分钟更新一次交易数据
    id='update_trade_data'
)
scheduler.add_job(
    check_new_trades,
    'interval',
    minutes=5,  # 每5分钟检查一次新交易
    id='check_new_trades'
)
scheduler.add_job(
    update_popular_traders_data,
    'interval',
    minutes=10,  # 每10分钟更新一次热门交易员数据
    id='update_popular_traders_data'
)

# 添加一个恢复机制，每小时检查并重置API状态
def reset_api_state():
    try:
        logger.info("🔄 重置API状态...")
        # 正确方式：导入模块并访问其变量
        import binance_api
        if hasattr(binance_api, 'last_ip_ban_time'):
            binance_api.last_ip_ban_time = 0
            logger.info("✅ API状态已重置")
    except Exception as e:
        logger.error(f"❌ 重置API状态失败: {str(e)}")

scheduler.add_job(
    reset_api_state,
    'interval',
    hours=1,  # 每小时重置一次API状态
    id='reset_api_state'
)

# 确保程序退出时关闭调度器和线程池
def shutdown_app():
    scheduler.shutdown()
    executor.shutdown(wait=False)

atexit.register(shutdown_app)

scheduler.start()

# ✅ 实时数据接口
@app.route("/api/data", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_data():
    try:
        # 尝试从缓存获取数据
        cached_data = get_cached_price_change()
        
        try:
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
        except Exception as e:
            logger.error(f"获取实时数据失败，尝试使用缓存: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 如果有缓存数据，则使用缓存
            if cached_data:
                logger.info("使用缓存数据返回")
                return jsonify({
                    "message": "成功获取(缓存)", 
                    "data": cached_data, 
                    "from_cache": True,
                    "cache_time": str(price_change_cache_time) if price_change_cache_time else None
                })
            
            # 如果没有缓存，则返回错误
            return jsonify({"message": "获取数据失败", "error": str(e)}), 500
    except Exception as e:
        logger.error(f"获取数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "获取数据失败", "error": str(e)}), 500

# ✅ 实时持仓量接口
@app.route("/api/open_interest", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_open_interest():
    try:
        # 检查断路器状态
        try:
            import binance_api
            if hasattr(binance_api, 'check_circuit_breaker'):
                circuit_ok = run_async(binance_api.check_circuit_breaker())
                if not circuit_ok:
                    logger.warning("断路器已触发，API请求被暂停，尝试从数据库获取最近数据")
                    # 从数据库获取最近的持仓量数据
                    with get_db_session() as session:
                        # 获取最近1小时的数据
                        recent_time = datetime.utcnow() - timedelta(hours=1)
                        recent_data = session.query(OpenInterest).filter(
                            OpenInterest.timestamp >= recent_time
                        ).all()
                        
                        if recent_data:
                            result = []
                            for item in recent_data:
                                result.append({
                                    "symbol": item.symbol,
                                    "fundingRate": item.funding_rate or 0.0,
                                    "openInterest": item.open_interest,
                                    "openInterestChange": {
                                        "5m": 0,  # 无法计算变化
                                        "15m": 0,
                                        "1h": 0
                                    },
                                    "from_database": True
                                })
                            
                            return jsonify({
                                "message": "成功获取(数据库)", 
                                "data": result,
                                "from_database": True,
                                "timestamp": datetime.now().isoformat()
                            })
                        # 如果数据库中没有数据，继续尝试API请求
        except ImportError:
            logger.warning("无法导入 binance_api 模块，跳过断路器检查")
        except Exception as e:
            logger.warning(f"断路器检查失败: {str(e)}")
        
        result = run_async(get_open_interest_data())
        if not result:
            logger.warning("持仓量数据为空")
            return jsonify({"message": "持仓量数据为空", "data": []}), 200
        
        # 计算数据可用性统计
        total_items = len(result)
        periods = ["5m", "15m", "1h"]
        period_stats = {}
        
        for period in periods:
            available_count = sum(1 for item in result if item["openInterestChange"].get(period) is not None)
            period_stats[period] = {
                "available": available_count,
                "total": total_items,
                "percentage": round(available_count / total_items * 100, 2) if total_items > 0 else 0
            }
        
        # 计算总体数据完整度
        total_possible_data_points = total_items * len(periods)
        available_data_points = sum(stats["available"] for stats in period_stats.values())
        data_completeness = round(available_data_points / total_possible_data_points * 100, 2) if total_possible_data_points > 0 else 0
            
        return jsonify({
            "message": "成功获取", 
            "data": result,
            "data_completeness": data_completeness,
            "period_stats": period_stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"获取持仓量数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 尝试从数据库获取最近数据
        try:
            with get_db_session() as session:
                # 获取最近1小时的数据
                recent_time = datetime.utcnow() - timedelta(hours=1)
                recent_data = session.query(OpenInterest).filter(
                    OpenInterest.timestamp >= recent_time
                ).all()
                
                if recent_data:
                    result = []
                    for item in recent_data:
                        result.append({
                            "symbol": item.symbol,
                            "fundingRate": item.funding_rate or 0.0,
                            "openInterest": item.open_interest,
                            "openInterestChange": {
                                "5m": 0,  # 无法计算变化
                                "15m": 0,
                                "1h": 0
                            },
                            "from_database": True
                        })
                    
                    return jsonify({
                        "message": "成功获取(数据库)", 
                        "data": result,
                        "from_database": True,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        except Exception as db_error:
            logger.error(f"从数据库获取数据也失败: {str(db_error)}")
        
        return jsonify({"message": "获取持仓量数据失败", "error": str(e)}), 500

# ✅ 涨跌幅接口 - 优化版本，使用缓存，支持部分数据
@app.route("/api/price_change", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_price_change_api():
    try:
        # 尝试从缓存获取数据
        cached_data = get_cached_price_change()
        if cached_data:
            return jsonify({
                "message": "成功(缓存)", 
                "data": cached_data,
                "partial_data": True,  # 标记可能是部分数据
                "timestamp": datetime.now().isoformat()
            })
        
        # 如果缓存中没有数据，则计算新数据
        market_data = run_async(BinanceAPI.fetch_market_data())
        result = calculate_price_changes(market_data)
        
        # 更新缓存
        set_price_change_cache(result)
        
        # 计算数据完整度
        total_periods = 6  # 1m, 2m, 5m, 20m, 40m, 1h
        if result:
            available_count = sum(len(item.get("available_periods", [])) for item in result)
            total_possible = len(result) * total_periods
            completeness = round(available_count / total_possible * 100, 2) if total_possible > 0 else 0
            
            # 计算每个时间段的可用性
            period_stats = {}
            periods = ["1m", "2m", "5m", "20m", "40m", "1h"]
            for period in periods:
                available = sum(1 for item in result if period in item.get("available_periods", []))
                period_stats[period] = {
                    "available": available,
                    "total": len(result),
                    "percentage": round(available / len(result) * 100, 2) if len(result) > 0 else 0
                }
        else:
            completeness = 0
            period_stats = {}
        
        # 获取数据库中最早和最新的价格记录
        try:
            with get_db_session() as session:
                earliest = session.query(func.min(Price.timestamp)).scalar()
                latest = session.query(func.max(Price.timestamp)).scalar()
                
                if earliest and latest:
                    time_span = latest - earliest
                    time_span_hours = time_span.total_seconds() / 3600
                else:
                    time_span_hours = 0
        except Exception as e:
            logger.error(f"获取数据时间范围失败: {str(e)}")
            time_span_hours = 0
        
        return jsonify({
            "message": "成功", 
            "data": result,
            "partial_data": True,  # 标记可能是部分数据
            "data_completeness": completeness,  # 数据完整度百分比
            "period_stats": period_stats,  # 每个时间段的统计信息
            "data_time_span_hours": round(time_span_hours, 2),  # 数据时间跨度（小时）
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"获取价格变化数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "获取价格变化数据失败", "error": str(e)}), 500

@app.route("/api/traders", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_traders():
    """获取所有交易员信息"""
    try:
        with get_db_session() as session:
            traders = session.query(Trader).all()
            result = []
            
            for trader in traders:
                # 获取该交易员的交易统计
                open_trades = session.query(Trade).filter(
                    Trade.trader_id == trader.id,
                    Trade.status == "OPEN"
                ).count()
                
                closed_trades = session.query(Trade).filter(
                    Trade.trader_id == trader.id,
                    Trade.status == "CLOSED"
                ).count()
                
                # 计算盈利交易数量
                profit_trades = session.query(Trade).filter(
                    Trade.trader_id == trader.id,
                    Trade.status == "CLOSED",
                    Trade.pnl > 0
                ).count()
                
                # 计算亏损交易数量
                loss_trades = session.query(Trade).filter(
                    Trade.trader_id == trader.id,
                    Trade.status == "CLOSED",
                    Trade.pnl < 0
                ).count()
                
                # 计算总盈亏
                total_pnl = session.query(func.sum(Trade.pnl)).filter(
                    Trade.trader_id == trader.id,
                    Trade.status == "CLOSED"
                ).scalar() or 0
                
                # 计算胜率
                win_rate = (profit_trades / closed_trades * 100) if closed_trades > 0 else 0
                
                result.append({
                    "id": trader.id,
                    "name": trader.name,
                    "description": trader.description,
                    "source_url": trader.source_url,
                    "is_active": trader.is_active,
                    "created_at": trader.created_at.isoformat(),
                    "updated_at": trader.updated_at.isoformat(),
                    "stats": {
                        "open_trades": open_trades,
                        "closed_trades": closed_trades,
                        "profit_trades": profit_trades,
                        "loss_trades": loss_trades,
                        "total_pnl": round(total_pnl, 2),
                        "win_rate": round(win_rate, 2)
                    }
                })
            
            return jsonify({
                "message": "成功获取交易员信息",
                "data": result
            })
    except Exception as e:
        logger.error(f"获取交易员信息失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "获取交易员信息失败", "error": str(e)}), 500

@app.route("/api/trades", methods=["GET"])
@rate_limit
@log_request
@error_handler
def get_trades():
    """获取交易记录"""
    try:
        trader_id = request.args.get("trader_id")
        status = request.args.get("status")
        symbol = request.args.get("symbol")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
        
        with get_db_session() as session:
            query = session.query(Trade)
            
            # 应用过滤条件
            if trader_id:
                query = query.filter(Trade.trader_id == trader_id)
            if status:
                query = query.filter(Trade.status == status)
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            
            # 获取总记录数
            total = query.count()
            
            # 应用分页
            trades = query.order_by(desc(Trade.entry_time)).offset(offset).limit(limit).all()
            
            result = []
            for trade in trades:
                # 获取当前价格
                current_price = None
                try:
                    # 尝试获取最新价格
                    price_record = session.query(Price).filter(
                        Price.symbol == trade.symbol
                    ).order_by(desc(Price.timestamp)).first()
                    
                    if price_record:
                        current_price = price_record.price
                except Exception as e:
                    logger.warning(f"获取价格失败: {str(e)}")
                
                # 计算未实现盈亏
                unrealized_pnl = None
                unrealized_pnl_percentage = None
                
                if current_price and trade.status == "OPEN":
                    if trade.direction == "LONG":
                        unrealized_pnl = (current_price - trade.entry_price) * (trade.position_size or 1)
                        unrealized_pnl_percentage = (current_price - trade.entry_price) / trade.entry_price * 100
                    else:  # SHORT
                        unrealized_pnl = (trade.entry_price - current_price) * (trade.position_size or 1)
                        unrealized_pnl_percentage = (trade.entry_price - current_price) / trade.entry_price * 100
                
                # 获取交易员信息
                trader = session.query(Trader).get(trade.trader_id)
                
                result.append({
                    "id": trade.id,
                    "trader": {
                        "id": trader.id,
                        "name": trader.name
                    },
                    "symbol": trade.symbol,
                    "direction": trade.direction,
                    "entry_price": trade.entry_price,
                    "current_price": current_price,
                    "take_profit": trade.take_profit,
                    "stop_loss": trade.stop_loss,
                    "leverage": trade.leverage,
                    "position_size": trade.position_size,
                    "status": trade.status,
                    "pnl": trade.pnl,
                    "pnl_percentage": trade.pnl_percentage,
                    "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
                    "unrealized_pnl_percentage": round(unrealized_pnl_percentage, 2) if unrealized_pnl_percentage is not None else None,
                    "entry_time": trade.entry_time.isoformat(),
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                    "notes": trade.notes
                })
            
            return jsonify({
                "message": "成功获取交易记录",
                "data": result,
                "pagination": {
                    "total": total,
                    "offset": offset,
                    "limit": limit
                }
            })
    except Exception as e:
        logger.error(f"获取交易记录失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "获取交易记录失败", "error": str(e)}), 500

@app.route("/api/update_trades", methods=["POST"])
@rate_limit
@log_request
@error_handler
def update_trades_api():
    """手动触发交易数据更新"""
    try:
        # 导入交易爬虫模块
        from trade_scraper import MockTradeGenerator, AoyingCapitalScraper
        
        # 获取参数
        use_mock = request.json.get("use_mock", True)
        count = int(request.json.get("count", 5))
        
        if use_mock:
            # 使用模拟数据
            generator = MockTradeGenerator()
            saved_count = run_async(generator.update_trades(count))
        else:
            # 使用实际爬虫
            scraper = AoyingCapitalScraper()
            saved_count = run_async(scraper.update_trades())
        
        return jsonify({
            "message": "交易数据更新成功",
            "saved_count": saved_count
        })
    except Exception as e:
        logger.error(f"更新交易数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "更新交易数据失败", "error": str(e)}), 500

@app.route("/api/check_trades", methods=["POST"])
@rate_limit
@log_request
@error_handler
def check_trades_api():
    """手动触发交易检查和通知"""
    try:
        # 调用交易检查函数
        new_trades_count = check_new_trades()
        
        return jsonify({
            "message": "交易检查完成",
            "new_trades_count": new_trades_count,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"手动触发交易检查失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "交易检查失败", "error": str(e)}), 500

@app.route("/api/update_popular_traders", methods=["POST"])
@rate_limit
@log_request
@error_handler
def update_popular_traders_api():
    """手动触发热门交易员数据更新"""
    try:
        # 导入热门交易员爬虫模块
        from popular_traders_scraper import PopularTradersScraper
        
        # 获取参数
        use_mock = request.json.get("use_mock", False)
        
        # 使用热门交易员爬虫
        scraper = PopularTradersScraper(fallback_to_mock=use_mock)
        saved_count = run_async(scraper.update_trades())
        
        return jsonify({
            "message": "热门交易员数据更新成功",
            "saved_count": saved_count,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"更新热门交易员数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"message": "更新热门交易员数据失败", "error": str(e)}), 500

# 添加CORS预检请求处理器
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = app.make_default_options_response()
    return response

# ✅ 启动入口
if __name__ == '__main__':
    try:
        # 初始化数据库
        init_db()
        logger.info("数据库初始化完成")
        
        # 初始化数据
        logger.info("正在初始化数据...")
        try:
            update_price_data()
            logger.info("价格数据初始化完成")
        except Exception as e:
            logger.error(f"价格数据初始化失败: {str(e)}")
        
        try:
            update_open_interest_data()
            logger.info("持仓量数据初始化完成")
        except Exception as e:
            logger.error(f"持仓量数据初始化失败: {str(e)}")
        
        try:
            precalculate_price_change()  # 预计算价格变化数据
            logger.info("价格变化数据初始化完成")
        except Exception as e:
            logger.error(f"价格变化数据初始化失败: {str(e)}")
            
        try:
            update_popular_traders_data()  # 初始化热门交易员数据
            logger.info("热门交易员数据初始化完成")
        except Exception as e:
            logger.error(f"热门交易员数据初始化失败: {str(e)}")
        
        # 每天清理30天前的数据
        scheduler.add_job(
            lambda: cleanup_old_data(config.DATA_RETENTION_DAYS),
            'cron',
            hour=0,
            minute=0
        )
        
        # 获取端口，优先使用环境变量
        port = int(os.environ.get('PORT', 5000))
        debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        # 启动应用
        logger.info(f"应用启动在端口 {port}，调试模式：{debug_mode}")
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        logger.error(traceback.format_exc())
