#open_interest.py

import aiohttp
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session
from db import SessionLocal
from db import OpenInterest
from db import get_previous_oi, save_open_interest_bulk

# ✅ 从 Binance 获取所有 symbol
async def get_futures_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

# ✅ 获取某个 symbol 当前持仓量
async def fetch_open_interest(session, symbol):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    async with session.get(url) as resp:
        data = await resp.json()
        return {
            "symbol": symbol,
            "open_interest": float(data["openInterest"])
        }

# ✅ 获取全部 symbol 的持仓量
async def get_open_interest_data():
    symbols = await get_futures_symbols()
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_open_interest(session, symbol) for symbol in symbols]
        all_data = await asyncio.gather(*tasks)

        timestamp = datetime.utcnow()

        # ✅ 查询过去 N 分钟前的数据，用于计算涨跌幅
        previous_data = get_previous_oi(minutes_ago=1)
        previous_dict = {item.symbol: item.open_interest for item in previous_data}

        for item in all_data:
            symbol = item["symbol"]
            current = item["open_interest"]
            previous = previous_dict.get(symbol)

            change_pct = 0.0
            if previous and previous != 0:
                change_pct = round((current - previous) / previous * 100, 2)

            results.append({
                "symbol": symbol,
                "open_interest": current,
                "change_pct": change_pct,
                "timestamp": timestamp
            })

        return results

# ✅ 批量保存到数据库
def save_open_interest_data(data):
    session = scoped_session(SessionLocal)
    try:
        records = [
            OpenInterest(
                symbol=item["symbol"],
                open_interest=item["open_interest"],
                change_pct=item["change_pct"],
                timestamp=item["timestamp"]
            )
            for item in data
        ]
        save_open_interest_bulk(records, session)
        print(f"✅ 已保存 {len(records)} 条持仓量数据")
    except Exception as e:
        session.rollback()
        print("❌ save_open_interest_data 失败:", e)
    finally:
        session.close()
