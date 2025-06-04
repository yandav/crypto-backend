# trade_scraper.py

import asyncio
import logging
import json
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, Optional
from database import get_db_session, save_trades
from models import Trader, Trade

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AoyingCapitalScraper:
    """熬鹰资本交易数据爬虫"""
    
    def __init__(self, fallback_to_mock=True):
        self.base_url = "https://www.binance.com/zh-CN/futures-activity/leaderboard/user/um?encryptedUid=9FAD2A7F8D2B3F35A7F58D8B6F5CC6F7"  # 熬鹰资本的币安页面
        self.trader_name = "熬鹰资本"
        self.trader_id = None
        self.fallback_to_mock = fallback_to_mock  # 是否在真实爬虫失败时回退到模拟数据
    
    async def ensure_trader_exists(self) -> int:
        """确保交易员存在于数据库中"""
        with get_db_session() as session:
            trader = session.query(Trader).filter(Trader.name == self.trader_name).first()
            
            if not trader:
                # 创建新交易员
                trader = Trader(
                    name=self.trader_name,
                    description="熬鹰资本 - 币安交易员",
                    source_url=self.base_url,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(trader)
                session.commit()
                logger.info(f"创建新交易员: {self.trader_name}")
            
            self.trader_id = trader.id
            return trader.id
    
    async def fetch_page(self, url: str) -> str:
        """获取页面内容"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.binance.com/"
            }
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"获取页面失败: {url}, 错误: {str(e)}")
            return ""
    
    async def fetch_api_data(self) -> List[Dict[str, Any]]:
        """从币安API获取交易数据"""
        try:
            # 币安API地址，可能需要根据实际情况调整
            api_url = "https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/json",
                "Origin": "https://www.binance.com",
                "Referer": self.base_url
            }
            
            # 请求参数，encryptedUid是熬鹰资本的用户ID
            payload = {
                "encryptedUid": "9FAD2A7F8D2B3F35A7F58D8B6F5CC6F7",
                "tradeType": "PERPETUAL"
            }
            
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                response = await client.post(api_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if data.get("success") and "data" in data:
                    return data["data"]["otherPositionRetList"]
                else:
                    logger.error(f"API返回错误: {data}")
                    return []
        except Exception as e:
            logger.error(f"获取API数据失败: {str(e)}")
            return []
    
    async def parse_trades(self, html_content: str) -> List[Dict[str, Any]]:
        """解析HTML内容提取交易数据（备用方法）"""
        trades = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 这里需要根据实际网页结构调整选择器
            trade_elements = soup.select('.trade-item, .position-item')
            
            for element in trade_elements:
                try:
                    # 解析交易数据，以下是示例，需要根据实际HTML结构调整
                    symbol = element.select_one('.symbol, .pair').text.strip()
                    direction_elem = element.select_one('.direction, .side')
                    direction = "LONG" if "买入" in direction_elem.text or "多" in direction_elem.text else "SHORT"
                    
                    # 提取价格
                    entry_price_elem = element.select_one('.entry-price, .entry-price-value')
                    entry_price = float(entry_price_elem.text.strip().replace(',', ''))
                    
                    # 提取更多信息
                    take_profit_elem = element.select_one('.take-profit, .tp-price')
                    take_profit = float(take_profit_elem.text.strip().replace(',', '')) if take_profit_elem else None
                    
                    stop_loss_elem = element.select_one('.stop-loss, .sl-price')
                    stop_loss = float(stop_loss_elem.text.strip().replace(',', '')) if stop_loss_elem else None
                    
                    # 解析杠杆
                    leverage_elem = element.select_one('.leverage')
                    leverage = int(leverage_elem.text.strip().replace('x', '')) if leverage_elem else None
                    
                    # 解析日期
                    date_elem = element.select_one('.trade-date, .create-time')
                    if date_elem:
                        date_text = date_elem.text.strip()
                        try:
                            entry_time = datetime.strptime(date_text, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            # 尝试其他日期格式
                            try:
                                entry_time = datetime.strptime(date_text, '%Y/%m/%d %H:%M:%S')
                            except ValueError:
                                entry_time = datetime.utcnow()
                    else:
                        entry_time = datetime.utcnow()
                    
                    # 创建交易记录
                    trade = {
                        "symbol": symbol,
                        "direction": direction,
                        "entry_price": entry_price,
                        "take_profit": take_profit,
                        "stop_loss": stop_loss,
                        "leverage": leverage,
                        "entry_time": entry_time,
                        "status": "OPEN",
                        "source_data": str(element)
                    }
                    
                    trades.append(trade)
                except Exception as e:
                    logger.error(f"解析交易元素失败: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"解析HTML内容失败: {str(e)}")
        
        return trades
    
    async def parse_api_data(self, api_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析API数据为交易记录格式"""
        trades = []
        
        for position in api_data:
            try:
                symbol = position.get("symbol", "").replace("USDT", "/USDT")  # 添加斜杠使格式一致
                direction = "LONG" if position.get("amount", 0) > 0 else "SHORT"
                entry_price = float(position.get("entryPrice", 0))
                leverage = int(position.get("leverage", 1))
                position_size = abs(float(position.get("amount", 0)))
                
                # 从updateTime转换为datetime
                entry_time_ms = position.get("updateTime", 0)
                if entry_time_ms > 0:
                    entry_time = datetime.fromtimestamp(entry_time_ms / 1000)
                else:
                    entry_time = datetime.utcnow()
                
                # 创建交易记录
                trade = {
                    "trader_id": self.trader_id,
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry_price,
                    "leverage": leverage,
                    "position_size": position_size,
                    "status": "OPEN",
                    "entry_time": entry_time,
                    "notes": f"从币安API获取 - {position.get('updateTimeString', '')}",
                    "source_data": json.dumps(position)
                }
                
                trades.append(trade)
            except Exception as e:
                logger.error(f"解析API数据失败: {str(e)}")
                continue
        
        return trades
    
    async def fetch_trades(self) -> List[Dict[str, Any]]:
        """获取交易数据"""
        # 确保交易员存在
        await self.ensure_trader_exists()
        
        # 首先尝试从API获取数据
        api_data = await self.fetch_api_data()
        if api_data:
            trades = await self.parse_api_data(api_data)
            logger.info(f"从API获取到 {len(trades)} 条交易记录")
            return trades
        
        # 如果API获取失败，尝试从页面获取
        logger.info("API获取失败，尝试从页面获取数据")
        html_content = await self.fetch_page(self.base_url)
        if not html_content:
            logger.error("页面内容为空")
            return []
        
        # 解析交易数据
        trades = await self.parse_trades(html_content)
        
        # 添加交易员ID
        for trade in trades:
            trade["trader_id"] = self.trader_id
        
        return trades
    
    async def update_trades(self) -> int:
        """更新交易数据"""
        try:
            trades = await self.fetch_trades()
            
            if not trades:
                logger.info("没有找到新的交易")
                
                # 如果允许回退到模拟数据，且没有获取到真实数据
                if self.fallback_to_mock:
                    logger.info("尝试使用模拟数据作为备选")
                    mock_generator = MockTradeGenerator(trader_name=self.trader_name)
                    return await mock_generator.update_trades(count=5)
                
                return 0
            
            # 保存交易数据
            saved_count = save_trades(trades)
            logger.info(f"保存了 {saved_count} 条交易记录")
            
            return saved_count
        except Exception as e:
            logger.error(f"更新交易数据失败: {str(e)}")
            
            # 如果允许回退到模拟数据，且爬虫出错
            if self.fallback_to_mock:
                logger.info("爬虫出错，尝试使用模拟数据作为备选")
                try:
                    mock_generator = MockTradeGenerator(trader_name=self.trader_name)
                    return await mock_generator.update_trades(count=5)
                except Exception as mock_error:
                    logger.error(f"使用模拟数据也失败: {str(mock_error)}")
            
            return 0

# 模拟数据生成器（用于测试）
class MockTradeGenerator:
    """模拟交易数据生成器，用于测试"""
    
    def __init__(self, trader_name="熬鹰资本"):
        self.trader_name = trader_name
        self.trader_id = None
        self.symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
    
    async def ensure_trader_exists(self) -> int:
        """确保交易员存在于数据库中"""
        with get_db_session() as session:
            trader = session.query(Trader).filter(Trader.name == self.trader_name).first()
            
            if not trader:
                # 创建新交易员
                trader = Trader(
                    name=self.trader_name,
                    description=f"{self.trader_name}交易员",
                    source_url="https://example.com",
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(trader)
                session.commit()
                logger.info(f"创建新交易员: {self.trader_name}")
            
            self.trader_id = trader.id
            return trader.id
    
    async def generate_mock_trades(self, count=5) -> List[Dict[str, Any]]:
        """生成模拟交易数据"""
        import random
        
        # 确保交易员存在
        await self.ensure_trader_exists()
        
        trades = []
        now = datetime.utcnow()
        
        for i in range(count):
            # 随机选择交易对
            symbol = random.choice(self.symbols)
            
            # 随机方向
            direction = random.choice(["LONG", "SHORT"])
            
            # 生成随机价格
            base_price = {
                "BTC/USDT": 50000,
                "ETH/USDT": 3000,
                "SOL/USDT": 100,
                "BNB/USDT": 400,
                "XRP/USDT": 0.5
            }.get(symbol, 100)
            
            # 添加一些随机波动
            price_variation = random.uniform(-0.05, 0.05)
            entry_price = base_price * (1 + price_variation)
            
            # 设置止盈止损
            if direction == "LONG":
                take_profit = entry_price * (1 + random.uniform(0.05, 0.2))
                stop_loss = entry_price * (1 - random.uniform(0.02, 0.1))
            else:
                take_profit = entry_price * (1 - random.uniform(0.05, 0.2))
                stop_loss = entry_price * (1 + random.uniform(0.02, 0.1))
            
            # 随机入场时间（最近7天内）
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            entry_time = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # 创建交易记录
            trade = {
                "trader_id": self.trader_id,
                "symbol": symbol,
                "direction": direction,
                "entry_price": round(entry_price, 2),
                "take_profit": round(take_profit, 2),
                "stop_loss": round(stop_loss, 2),
                "leverage": random.randint(1, 20),
                "position_size": round(random.uniform(0.1, 10), 2),
                "status": "OPEN",
                "entry_time": entry_time,
                "notes": f"模拟交易 #{i+1}",
                "source_data": json.dumps({"mock": True, "id": i+1})
            }
            
            trades.append(trade)
        
        return trades
    
    async def update_trades(self, count=5) -> int:
        """更新模拟交易数据"""
        try:
            trades = await self.generate_mock_trades(count)
            
            # 保存交易数据
            saved_count = save_trades(trades)
            logger.info(f"保存了 {saved_count} 条模拟交易记录")
            
            return saved_count
        except Exception as e:
            logger.error(f"更新模拟交易数据失败: {str(e)}")
            return 0

# 主函数
async def main():
    """主函数"""
    # 使用模拟数据生成器
    generator = MockTradeGenerator()
    await generator.update_trades(10)
    
    # 实际爬虫（取消注释以使用）
    # scraper = AoyingCapitalScraper()
    # await scraper.update_trades()

if __name__ == "__main__":
    asyncio.run(main()) 