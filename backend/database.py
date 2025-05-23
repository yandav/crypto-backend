# database.py

from sqlalchemy.orm import scoped_session
from db import SessionLocal,PriceData
from sqlalchemy import desc
import datetime

# ✅ 保存实时数据（价格 + EMA）
def save_data(data):
    db = scoped_session(SessionLocal)
    try:
        for item in data:
            entry = PriceData(
                symbol=item['symbol'],
                price=item['price'],
                ema_7=item.get('ema_7'),
                ema_25=item.get('ema_25'),
                ema_99=item.get('ema_99'),
                timestamp=datetime.datetime.utcnow()
            )
            db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print("❌ save_data 保存失败:", e)
    finally:
        db.close()

# ✅ 查询最近一次价格数据（历史页面）
def get_latest_data(limit=100):
    db = scoped_session(SessionLocal)
    try:
        results = db.query(PriceData).order_by(desc(PriceData.timestamp)).limit(limit).all()
        return [
            {
                "symbol": row.symbol,
                "price": row.price,
                "ema_7": row.ema_7,
                "ema_25": row.ema_25,
                "ema_99": row.ema_99,
                "timestamp": row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in results
        ]
    except Exception as e:
        print("❌ 查询历史数据失败:", e)
        return []
    finally:
        db.close()

# ✅ 获取某个 symbol 指定分钟数前的价格（用于涨跌幅）
def get_price_change(symbol, minutes_ago):
    db = scoped_session(SessionLocal)
    try:
        target_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes_ago)
        result = db.query(PriceData).filter(
            PriceData.symbol == symbol,
            PriceData.timestamp <= target_time
        ).order_by(desc(PriceData.timestamp)).first()

        return result.price if result else None
    except Exception as e:
        print(f"❌ get_price_change 失败: {symbol} {minutes_ago}min:", e)
        return None
    finally:
        db.close()
