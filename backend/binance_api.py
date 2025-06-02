# binance_api.py

import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from db import get_previous_oi, save_open_interest_bulk  # ✅ 正确导入
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Binance API 配置
BASE_URL = "https://fapi.binance.com"
REQUEST_TIMEOUT = 30.0  # 请求超时时间（秒）
RATE_LIMIT_DELAY = 0.1  # API 请求间隔（秒）

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
    async def get_valid_symbols() -> List[str]:
        """获取所有有效的永续合约交易对"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BASE_URL}/fapi/v1/exchangeInfo")
                resp.raise_for_status()
                data = resp.json()
                
                return [
                    s["symbol"] for s in data["symbols"]
                    if (s["contractType"] == "PERPETUAL" and
                        s["quoteAsset"] == "USDT" and
                        s["status"] == "TRADING" and
                        s.get("underlyingType", "") == "COIN")
                ]
        except Exception as e:
            logger.error(f"Error getting valid symbols: {str(e)}")
            return []

    @staticmethod
    async def fetch_market_data() -> List[MarketData]:
        """获取所有交易对的市场数据"""
        try:
            async with httpx.AsyncClient() as client:
                # 获取资金费率
                premium_resp = await client.get(f"{BASE_URL}/fapi/v1/premiumIndex")
                premium_resp.raise_for_status()
                funding_dict = {
                    item["symbol"]: float(item.get("lastFundingRate") or 0.0)
                    for item in premium_resp.json()
                }

                # 获取24小时行情
                ticker_resp = await client.get(f"{BASE_URL}/fapi/v1/ticker/24hr")
                ticker_resp.raise_for_status()
                
                result = []
                for item in ticker_resp.json():
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
    async def fetch_open_interest(client: httpx.AsyncClient, symbol: str) -> Optional[Dict[str, Any]]:
        """获取单个交易对的持仓量数据"""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                await asyncio.sleep(RATE_LIMIT_DELAY)
                response = await client.get(
                    f"{BASE_URL}/fapi/v1/openInterest",
                    params={"symbol": symbol},
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 400:
                    logger.warning(f"{symbol} may be delisted or not supported")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                if "openInterest" not in data:
                    logger.warning(f"Invalid response format for {symbol}")
                    return None

                return {
                    "symbol": symbol,
                    "open_interest": float(data["openInterest"])
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                logger.error(f"Error fetching open interest for {symbol}: {str(e)}")
                return None

        return None

    @staticmethod
    async def fetch_all_open_interest() -> List[Dict[str, Any]]:
        """获取所有交易对的持仓量数据"""
        try:
            symbols = await BinanceAPI.get_valid_symbols()
            
            async with httpx.AsyncClient() as client:
                tasks = [BinanceAPI.fetch_open_interest(client, symbol) for symbol in symbols]
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

    symbols = await BinanceAPI.get_valid_symbols()
    premium_data = httpx.get(f"{BASE_URL}/fapi/v1/premiumIndex").json()
    funding_dict = {d["symbol"]: float(d.get("lastFundingRate") or 0.0) for d in premium_data}

    client = httpx.AsyncClient()
    try:
        tasks = [BinanceAPI.fetch_open_interest(client, symbol) for symbol in symbols]
        raw_results = await asyncio.gather(*tasks)
    finally:
        await client.aclose()

    result = []
    db_items = []
    now = datetime.utcnow()

    for item in raw_results:
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
