# binance_api.py
import httpx
import asyncio
from datetime import datetime
from db import get_previous_oi

BASE_URL = "https://fapi.binance.com"

def fetch_all_data():
    # 获取所有资金费率（premiumIndex 有所有 PERPETUAL 的 fundingRate）
    premium_data = httpx.get(f"{BASE_URL}/fapi/v1/premiumIndex").json()
    funding_dict = {
        item["symbol"]: float(item.get("lastFundingRate") or 0.0)
        for item in premium_data
    }

    # 获取所有 24h ticker 数据
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
    """只获取 USDT 永续合约"""
    resp = httpx.get(f"{BASE_URL}/fapi/v1/exchangeInfo").json()
    return [s["symbol"] for s in resp["symbols"]
            if s["contractType"] == "PERPETUAL" and s["quoteAsset"] == "USDT"]

async def fetch_open_interest(session, symbol):
    try:
        url = f"{BASE_URL}/fapi/v1/openInterest"
        resp = await session.get(url, params={"symbol": symbol}, timeout=10.0)
        data = resp.json()
        if "openInterest" not in data:
            return None
        return {
            "symbol": symbol,
            "current_oi": float(data["openInterest"])
        }
    except Exception as e:
        print(f"❌ 获取 {symbol} 持仓量失败: {e}")
        return None

def calc_change(old, current):
    if old is None or old == 0:
        return 0.0
    return round(((current - old) / old) * 100, 2)

async def get_open_interest_data():
    symbols = get_valid_symbols()
    premium_data = httpx.get(f"{BASE_URL}/fapi/v1/premiumIndex").json()
    funding_dict = {d["symbol"]: float(d.get("lastFundingRate") or 0.0) for d in premium_data}

    async with httpx.AsyncClient() as client:
        tasks = [fetch_open_interest(client, symbol) for symbol in symbols]
        raw_results = await asyncio.gather(*tasks)

    result = []
    now = datetime.utcnow()
    for item in raw_results:
        if not item:
            continue
        symbol = item["symbol"]
        current_oi = item["current_oi"]
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

    return result
