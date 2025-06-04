# binance_api.py

import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from db import get_previous_oi, save_open_interest_bulk  # ✅ 正确导入
import time
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Binance API 配置
BASE_URL = "https://fapi.binance.com"
REQUEST_TIMEOUT = 30.0  # 请求超时时间（秒）
RATE_LIMIT_DELAY = 1.0  # API 请求间隔（秒），增加到1秒

# 请求头配置
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json"
}

# 全局变量记录上次IP被禁时间和断路器状态
last_ip_ban_time = 0
circuit_breaker_tripped = False
circuit_breaker_reset_time = 0
circuit_breaker_failures = 0
circuit_breaker_failure_threshold = 5

# 移除模块级别的锁，改为函数内部创建
# ip_ban_lock = asyncio.Lock()
# circuit_breaker_lock = asyncio.Lock()

async def check_circuit_breaker():
    """检查断路器状态，如果断路器被触发，则等待重置时间"""
    global circuit_breaker_tripped, circuit_breaker_reset_time, circuit_breaker_failures
    
    # 在函数内创建锁
    circuit_breaker_lock = asyncio.Lock()
    
    async with circuit_breaker_lock:
        # 如果断路器被触发
        if circuit_breaker_tripped:
            # 检查是否已经过了重置时间
            if time.time() > circuit_breaker_reset_time:
                logger.info("断路器重置，恢复API请求")
                circuit_breaker_tripped = False
                circuit_breaker_failures = 0
                return True
            else:
                # 计算剩余等待时间
                wait_time = circuit_breaker_reset_time - time.time()
                logger.warning(f"断路器已触发，API请求被暂停，剩余等待时间: {wait_time:.2f}s")
                return False
        return True

async def record_failure():
    """记录一次失败，如果失败次数超过阈值，则触发断路器"""
    global circuit_breaker_tripped, circuit_breaker_reset_time, circuit_breaker_failures
    
    # 在函数内创建锁
    circuit_breaker_lock = asyncio.Lock()
    
    async with circuit_breaker_lock:
        circuit_breaker_failures += 1
        if circuit_breaker_failures >= circuit_breaker_failure_threshold:
            circuit_breaker_tripped = True
            # 设置30分钟后重置断路器
            circuit_breaker_reset_time = time.time() + 1800
            logger.warning(f"失败次数达到阈值 {circuit_breaker_failures}，断路器已触发，暂停API请求30分钟")

async def record_success():
    """记录一次成功，重置失败计数"""
    global circuit_breaker_failures
    
    # 在函数内创建锁
    circuit_breaker_lock = asyncio.Lock()
    
    async with circuit_breaker_lock:
        circuit_breaker_failures = 0

# 请求限流控制
class RateLimiter:
    def __init__(self, requests_per_second=1):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
        # 移除构造函数中的锁，改为每次wait时创建
        # self.lock = asyncio.Lock()
    
    async def wait(self):
        # 在方法内创建锁
        lock = asyncio.Lock()
        
        async with lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            wait_time = max(0, 1.0/self.requests_per_second - elapsed)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                
            self.last_request_time = time.time()

# 创建限流器实例
rate_limiter = RateLimiter(requests_per_second=0.5)  # 每秒最多0.5个请求 (2秒一个请求)

@dataclass
class MarketData:
    """市场数据模型"""
    symbol: str
    price: float
    change_24h: float
    volume: float
    funding_rate: float
    open_interest: Optional[float] = None
    
class BinanceAPI:
    """Binance API 封装类"""
    
    @staticmethod
    async def make_request(url, params=None, max_retries=3, initial_backoff=5):
        """发送API请求，带指数退避重试机制"""
        global last_ip_ban_time
        
        # 检查断路器状态
        if not await check_circuit_breaker():
            raise Exception("API请求被断路器暂停")
        
        # 检查是否在IP禁止期间
        # 在函数内创建锁
        ip_ban_lock = asyncio.Lock()
        
        async with ip_ban_lock:
            if last_ip_ban_time > 0:
                time_since_ban = time.time() - last_ip_ban_time
                if time_since_ban < 300:  # 如果距离上次IP禁止不到5分钟
                    wait_time = 300 - time_since_ban + random.uniform(1, 5)
                    logger.warning(f"IP recently banned, waiting {wait_time:.2f}s before next request")
                    await asyncio.sleep(wait_time)
                    last_ip_ban_time = 0  # 重置禁止时间
        
        # 创建一个新的限流器实例，避免跨事件循环问题
        local_rate_limiter = RateLimiter(requests_per_second=0.5)
        await local_rate_limiter.wait()  # 请求前等待限流器
        
        for attempt in range(max_retries):
            try:
                # 添加随机抖动，避免多个请求同时发出
                jitter = random.uniform(1, 3)
                if attempt > 0:
                    backoff_time = initial_backoff * (2 ** (attempt - 1)) + jitter
                    logger.info(f"Retrying request after {backoff_time:.2f}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(backoff_time)
                
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.get(url, params=params, headers=DEFAULT_HEADERS)
                    
                    # 处理429和418状态码
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get('Retry-After', initial_backoff * 2))
                        logger.warning(f"Rate limited (status 429), waiting for {retry_after}s")
                        await record_failure()  # 记录失败
                        await asyncio.sleep(retry_after + jitter)
                        continue
                    elif resp.status_code == 418:
                        # 418表示IP被临时禁止，需要等待更长时间
                        retry_after = int(resp.headers.get('Retry-After', 300))
                        logger.warning(f"IP banned (status 418), waiting for {retry_after}s")
                        
                        # 更新全局IP禁止时间
                        async with ip_ban_lock:
                            last_ip_ban_time = time.time()
                        
                        await record_failure()  # 记录失败
                        
                        # 等待更长时间后重试
                        await asyncio.sleep(retry_after + random.uniform(10, 30))
                        continue
                    
                    resp.raise_for_status()
                    await record_success()  # 记录成功
                    return resp.json()
            except httpx.HTTPStatusError as e:
                await record_failure()  # 记录失败
                if attempt == max_retries - 1:
                    logger.error(f"HTTP error after {max_retries} attempts: {str(e)}")
                    raise
            except Exception as e:
                await record_failure()  # 记录失败
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {str(e)}")
                    raise
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    @staticmethod
    async def get_valid_symbols() -> List[str]:
        """获取所有有效的永续合约交易对"""
        try:
            data = await BinanceAPI.make_request(f"{BASE_URL}/fapi/v1/exchangeInfo")
            
            # 只返回部分交易对，减少API请求量
            symbols = [
                s["symbol"] for s in data["symbols"]
                if (s["contractType"] == "PERPETUAL" and
                    s["quoteAsset"] == "USDT" and
                    s["status"] == "TRADING" and
                    s.get("underlyingType", "") == "COIN")
            ]
            
            # 只返回前30个交易对，避免过多请求
            return symbols[:30]
        except Exception as e:
            logger.error(f"Error getting valid symbols: {str(e)}")
            return []

    @staticmethod
    async def fetch_market_data() -> List[MarketData]:
        """获取所有交易对的市场数据"""
        try:
            # 获取资金费率
            premium_data = await BinanceAPI.make_request(f"{BASE_URL}/fapi/v1/premiumIndex")
            funding_dict = {
                item["symbol"]: float(item.get("lastFundingRate") or 0.0)
                for item in premium_data
            }

            # 获取24小时行情
            ticker_data = await BinanceAPI.make_request(f"{BASE_URL}/fapi/v1/ticker/24hr")
            
            result = []
            for item in ticker_data:
                symbol = item["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                    
                result.append(MarketData(
                    symbol=symbol,
                    price=float(item["lastPrice"]),
                    change_24h=float(item["priceChangePercent"]),
                    volume=float(item["quoteVolume"]),
                    funding_rate=funding_dict.get(symbol, 0.0)
                ))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return []

    @staticmethod
    async def fetch_open_interest(symbol: str) -> Optional[Dict[str, Any]]:
        """获取单个交易对的持仓量数据"""
        try:
            data = await BinanceAPI.make_request(
                f"{BASE_URL}/fapi/v1/openInterest",
                params={"symbol": symbol}
            )
            
            if "openInterest" not in data:
                logger.warning(f"Invalid response format for {symbol}")
                return None

            return {
                "symbol": symbol,
                "open_interest": float(data["openInterest"])
            }
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {str(e)}")
            return None

    @staticmethod
    async def fetch_all_open_interest() -> List[Dict[str, Any]]:
        """获取所有交易对的持仓量数据"""
        try:
            symbols = await BinanceAPI.get_valid_symbols()
            
            # 使用信号量限制并发请求数量
            semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
            
            async def fetch_with_semaphore(symbol):
                async with semaphore:
                    return await BinanceAPI.fetch_open_interest(symbol)
            
            tasks = [fetch_with_semaphore(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks)
            
            # 过滤掉 None 结果
            return [r for r in results if r is not None]
                
        except Exception as e:
            logger.error(f"Error fetching all open interest: {str(e)}")
            return []

    @staticmethod
    def calc_change(old_value: Optional[float], new_value: float) -> float:
        """计算变化百分比"""
        if not old_value or old_value == 0:
            return 0.0
        return round((new_value - old_value) / old_value * 100, 2)

async def get_open_interest_data():
    print("📊 开始抓取持仓量数据...")
    start = time.time()

    try:
        symbols = await BinanceAPI.get_valid_symbols()
        if not symbols:
            logger.error("无法获取有效交易对列表")
            return []
            
        premium_data = await BinanceAPI.make_request(f"{BASE_URL}/fapi/v1/premiumIndex")
        funding_dict = {d["symbol"]: float(d.get("lastFundingRate") or 0.0) for d in premium_data}

        # 使用信号量限制并发请求数量
        semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
        
        async def fetch_with_semaphore(symbol):
            async with semaphore:
                # 创建一个新的限流器实例，避免跨事件循环问题
                local_rate_limiter = RateLimiter(requests_per_second=0.5)
                await local_rate_limiter.wait()  # 请求前等待限流器
                return await BinanceAPI.fetch_open_interest(symbol)
        
        tasks = [fetch_with_semaphore(symbol) for symbol in symbols]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤出成功的结果
        filtered_results = []
        for result in raw_results:
            if isinstance(result, Exception):
                logger.error(f"获取持仓量失败: {str(result)}")
            elif result:
                filtered_results.append(result)
                
        result = []
        db_items = []
        now = datetime.utcnow()

        for item in filtered_results:
            if not item or not item.get("symbol") or not item.get("open_interest"):  # Add null check
                continue
            
            symbol = item["symbol"]
            current_oi = item["open_interest"]
            
            if not isinstance(current_oi, (int, float)) or current_oi <= 0:  # Validate OI value
                continue
                
            result.append({
                "symbol": symbol,
                "fundingRate": funding_dict.get(symbol, 0.0),
                "openInterest": current_oi,
                "openInterestChange": {
                    "5m": BinanceAPI.calc_change(get_previous_oi(symbol, 5), current_oi),
                    "15m": BinanceAPI.calc_change(get_previous_oi(symbol, 15), current_oi),
                    "1h": BinanceAPI.calc_change(get_previous_oi(symbol, 60), current_oi),
                }
            })
            
            # Only add valid data to database items
            db_items.append({
                "symbol": symbol,
                "timestamp": now,
                "open_interest": current_oi,
                "change_pct": 0.0  # Default value for change percentage
            })

        if db_items:  # Only save if we have valid items
            save_open_interest_bulk(db_items)
            print(f"✅ 持仓量数据抓取完成，用时 {time.time() - start:.2f}s，共 {len(result)} 个币种")
        else:
            print("⚠️ 没有有效的持仓量数据可保存")
        
        return result
    except Exception as e:
        logger.error(f"获取持仓量数据失败: {str(e)}", exc_info=True)
        return []
