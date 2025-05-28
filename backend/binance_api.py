# binance_api.py

import httpx
import asyncio
from datetime import datetime
from db import get_previous_oi, save_open_interest_bulk  # ✅ 正确导入
import time

BASE_URL = "https://fapi.binance.com"

def fetch_all_data():
    premium_data = httpx.get(f"{BASE_URL}/fapi/v1/premiumIndex").json()
    funding_dict = {
        item["symbol"]: float(item.get("lastFundingRate") or 0.0)
        for item in premium_data
    }

    ticker_data = httpx.get(f"{BASE_URL}/fapi/v1/ticker/24hr").json()

    result = []
    for item in ticker_data:
        symbol = item["symbol"]
        if not symbol.endswith("USDT"):
            continue
        result.append({
            "symbol": symbol,
            "price": float(item["lastPrice"]),
            "change": float(item["priceChangePercent"]),
            "volume": float(item["quoteVolume"]),
            "fundingRate": funding_dict.get(symbol, None)
        })

    return result

def get_valid_symbols():
    resp = httpx.get(f"{BASE_URL}/fapi/v1/exchangeInfo").json()
    return [s["symbol"] for s in resp["symbols"]
            if s["contractType"] == "PERPETUAL" and s["quoteAsset"] == "USDT"]

async def fetch_open_interest(session, symbol):
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(0.1)  # Rate limiting
            url = f"{BASE_URL}/fapi/v1/openInterest"
            async with session.get(url, params={"symbol": symbol}, timeout=30.0) as resp:
                if resp.status != 200:
                    print(f"❌ {symbol} API 返回状态码: {resp.status}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None
                    
                data = await resp.json()
                if "openInterest" not in data:
                    return None
                    
                return {
                    "symbol": symbol,
                    "current_oi": float(data["openInterest"])
                }
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            print(f"❌ 获取 {symbol} 持仓量失败: {e}")
            return None
    
    return None

def calc_change(old, current):
    if old is None or old == 0:
        return 0.0
    return round(((current - old) / old) * 100, 2)

async def get_open_interest_data():
    print("📊 开始抓取持仓量数据...")
    start = time.time()

    symbols = get_valid_symbols()
    premium_data = httpx.get(f"{BASE_URL}/fapi/v1/premiumIndex").json()
    funding_dict = {d["symbol"]: float(d.get("lastFundingRate") or 0.0) for d in premium_data}

    async with httpx.AsyncClient() as client:
        tasks = [fetch_open_interest(client, symbol) for symbol in symbols]
        raw_results = await asyncio.gather(*tasks)

    result = []
    db_items = []
    now = datetime.utcnow()

    for item in raw_results:
        if not item or not item.get("symbol") or not item.get("current_oi"):  # Add null check
            continue
        
        symbol = item["symbol"]
        current_oi = item["current_oi"]
        
        if not isinstance(current_oi, (int, float)) or current_oi <= 0:  # Validate OI value
            continue
            
        result.append({
            "symbol": symbol,
            "fundingRate": funding_dict.get(symbol, 0.0),
            "openInterest": current_oi,
            "openInterestChange": {
                "5m": calc_change(get_previous_oi(symbol, 5), current_oi),
                "15m": calc_change(get_previous_oi(symbol, 15), current_oi),
                "1h": calc_change(get_previous_oi(symbol, 60), current_oi),
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
