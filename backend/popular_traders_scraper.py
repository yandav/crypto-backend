# popular_traders_scraper.py

import asyncio
import logging
import json
from datetime import datetime, timedelta
import httpx
from typing import List, Dict, Any, Optional
from database import get_db_session, save_trades
from models import Trader, Trade

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PopularTradersScraper:
    """币安热门交易员数据爬虫"""
    
    def __init__(self, fallback_to_mock=True):
        # 热门交易员列表，包含名称和加密ID
        self.traders = [
            {
                "name": "熬鹰资本",
                "encrypted_uid": "9FAD2A7F8D2B3F35A7F58D8B6F5CC6F7",
                "description": "熬鹰资本 - 币安知名交易员"
            },
            {
                "name": "Swing",
                "encrypted_uid": "D8AE0E4A0605CE9FAC0E8C5E7B5FE214",
                "description": "Swing - 币安热门交易员"
            },
            {
                "name": "牛市猎手",
                "encrypted_uid": "3C496F14B8AD5D0C8D671BBD0DBAC252",
                "description": "牛市猎手 - 币安热门交易员"
            },
            {
                "name": "币圈顶级玩家",
                "encrypted_uid": "D20FD31BB9EB9C3AC4C9D7C35CC9C7CC",
                "description": "币圈顶级玩家 - 币安热门交易员"
            },
            {
                "name": "Crypto Whale",
                "encrypted_uid": "B8E2C7F9B37C71D3F5346B481B9F4E28",
                "description": "Crypto Whale - 币安国际交易员"
            }
        ]
        self.fallback_to_mock = fallback_to_mock
        self.base_url = "https://www.binance.com/zh-CN/futures-activity/leaderboard"
    
    async def ensure_traders_exist(self) -> Dict[str, int]:
        """确保所有交易员存在于数据库中，返回交易员ID映射"""
        trader_ids = {}
        
        with get_db_session() as session:
            for trader_info in self.traders:
                trader_name = trader_info["name"]
                trader = session.query(Trader).filter(Trader.name == trader_name).first()
                
                if not trader:
                    # 创建新交易员
                    trader = Trader(
                        name=trader_name,
                        description=trader_info["description"],
                        source_url=f"{self.base_url}/user/um?encryptedUid={trader_info['encrypted_uid']}",
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(trader)
                    session.commit()
                    logger.info(f"创建新交易员: {trader_name}")
                
                trader_ids[trader_name] = trader.id
        
        return trader_ids
    
    async def fetch_current_positions(self, encrypted_uid: str) -> List[Dict[str, Any]]:
        """获取当前持仓数据"""
        try:
            api_url = "https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/json",
                "Origin": "https://www.binance.com",
                "Referer": f"{self.base_url}/user/um?encryptedUid={encrypted_uid}"
            }
            
            payload = {
                "encryptedUid": encrypted_uid,
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
            logger.error(f"获取当前持仓数据失败: {str(e)}")
            return []
    
    async def fetch_position_history(self, encrypted_uid: str) -> List[Dict[str, Any]]:
        """获取历史交易数据"""
        try:
            # 尝试第一个API端点
            api_url = "https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getPositionHistory"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/json",
                "Origin": "https://www.binance.com",
                "Referer": f"{self.base_url}/user/um?encryptedUid={encrypted_uid}"
            }
            
            # 计算过去24小时的时间戳
            current_time = int(datetime.utcnow().timestamp() * 1000)
            past_time = int((datetime.utcnow() - timedelta(days=1)).timestamp() * 1000)
            
            payload = {
                "encryptedUid": encrypted_uid,
                "tradeType": "PERPETUAL",
                "startTime": past_time,
                "endTime": current_time,
                "limit": 20
            }
            
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                try:
                    response = await client.post(api_url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success") and "data" in data:
                        return data["data"]["positionHistoryList"]
                    else:
                        logger.error(f"历史交易API返回错误: {data}")
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        logger.warning(f"历史交易API端点不可用 (404)，尝试替代API...")
                    else:
                        logger.error(f"历史交易API请求失败: {str(e)}")
                
                # 尝试替代API端点
                alt_api_url = "https://www.binance.com/bapi/futures/v2/public/future/leaderboard/getPositionHistory"
                try:
                    response = await client.post(alt_api_url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success") and "data" in data:
                        return data["data"]["positionHistoryList"]
                    else:
                        logger.error(f"替代历史交易API返回错误: {data}")
                except Exception as e:
                    logger.error(f"替代历史交易API请求失败: {str(e)}")
                
                # 如果两个API都失败，尝试第三种方式
                alt_api_url2 = "https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getTradeStatistics"
                try:
                    alt_payload = {
                        "encryptedUid": encrypted_uid,
                        "tradeType": "PERPETUAL"
                    }
                    response = await client.post(alt_api_url2, json=alt_payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success") and "data" in data:
                        logger.info(f"成功获取交易统计数据，但无法获取详细历史交易")
                    else:
                        logger.error(f"交易统计API返回错误: {data}")
                except Exception as e:
                    logger.error(f"交易统计API请求失败: {str(e)}")
                
                # 所有API都失败，返回空列表
                return []
        except Exception as e:
            logger.error(f"获取历史交易数据失败: {str(e)}")
            return []
    
    async def parse_current_positions(self, positions: List[Dict[str, Any]], trader_id: int) -> List[Dict[str, Any]]:
        """解析当前持仓数据为交易记录格式"""
        trades = []
        
        for position in positions:
            try:
                symbol = position.get("symbol", "").replace("USDT", "/USDT")
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
                    "trader_id": trader_id,
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry_price,
                    "leverage": leverage,
                    "position_size": position_size,
                    "status": "OPEN",
                    "entry_time": entry_time,
                    "notes": f"当前持仓 - {position.get('updateTimeString', '')}",
                    "source_data": json.dumps(position)
                }
                
                trades.append(trade)
            except Exception as e:
                logger.error(f"解析当前持仓数据失败: {str(e)}")
                continue
        
        return trades
    
    async def parse_position_history(self, positions: List[Dict[str, Any]], trader_id: int) -> List[Dict[str, Any]]:
        """解析历史交易数据为交易记录格式"""
        trades = []
        
        for position in positions:
            try:
                symbol = position.get("symbol", "").replace("USDT", "/USDT")
                direction = "LONG" if position.get("amount", 0) > 0 else "SHORT"
                entry_price = float(position.get("entryPrice", 0))
                exit_price = float(position.get("closePrice", 0))
                leverage = int(position.get("leverage", 1))
                position_size = abs(float(position.get("amount", 0)))
                pnl = float(position.get("pnl", 0))
                roe = float(position.get("roe", 0))
                
                # 从createTime转换为datetime
                entry_time_ms = position.get("createTime", 0)
                if entry_time_ms > 0:
                    entry_time = datetime.fromtimestamp(entry_time_ms / 1000)
                else:
                    entry_time = datetime.utcnow()
                
                # 从updateTime转换为datetime
                exit_time_ms = position.get("updateTime", 0)
                if exit_time_ms > 0:
                    exit_time = datetime.fromtimestamp(exit_time_ms / 1000)
                else:
                    exit_time = None
                
                # 创建交易记录
                trade = {
                    "trader_id": trader_id,
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "leverage": leverage,
                    "position_size": position_size,
                    "status": "CLOSED",
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "pnl": pnl,
                    "roe": roe,
                    "notes": f"历史交易 - ROE: {roe}%",
                    "source_data": json.dumps(position)
                }
                
                trades.append(trade)
            except Exception as e:
                logger.error(f"解析历史交易数据失败: {str(e)}")
                continue
        
        return trades
    
    async def fetch_trader_data(self, trader_info: Dict[str, Any], trader_id: int) -> List[Dict[str, Any]]:
        """获取单个交易员的数据"""
        all_trades = []
        encrypted_uid = trader_info["encrypted_uid"]
        trader_name = trader_info["name"]
        
        # 获取当前持仓
        current_positions = await self.fetch_current_positions(encrypted_uid)
        if current_positions:
            current_trades = await self.parse_current_positions(current_positions, trader_id)
            logger.info(f"从API获取到 {trader_name} 的 {len(current_trades)} 条当前持仓记录")
            all_trades.extend(current_trades)
        
        # 获取历史交易
        history_positions = await self.fetch_position_history(encrypted_uid)
        if history_positions:
            history_trades = await self.parse_position_history(history_positions, trader_id)
            logger.info(f"从API获取到 {trader_name} 的 {len(history_trades)} 条历史交易记录")
            all_trades.extend(history_trades)
        
        return all_trades
    
    async def update_trades(self) -> int:
        """更新所有交易员的交易数据"""
        try:
            # 确保所有交易员存在
            trader_ids = await self.ensure_traders_exist()
            
            all_trades = []
            
            # 获取每个交易员的数据
            for trader_info in self.traders:
                trader_name = trader_info["name"]
                trader_id = trader_ids.get(trader_name)
                
                if not trader_id:
                    logger.error(f"无法获取交易员ID: {trader_name}")
                    continue
                
                trades = await self.fetch_trader_data(trader_info, trader_id)
                all_trades.extend(trades)
            
            if not all_trades:
                logger.info("没有找到新的交易")
                
                # 如果允许回退到模拟数据，且没有获取到真实数据
                if self.fallback_to_mock:
                    logger.info("尝试使用模拟数据作为备选")
                    from trade_scraper import MockTradeGenerator
                    for trader_name, trader_id in trader_ids.items():
                        mock_generator = MockTradeGenerator(trader_name=trader_name)
                        mock_trades = await mock_generator.generate_mock_trades(count=3)
                        all_trades.extend(mock_trades)
                
                if not all_trades:
                    return 0
            
            # 保存交易数据到数据库
            saved_count = save_trades(all_trades)
            logger.info(f"成功保存 {saved_count} 条交易记录")
            return saved_count
        
        except Exception as e:
            logger.error(f"更新交易数据失败: {str(e)}")
            return 0

# 主函数
async def main():
    """主函数"""
    scraper = PopularTradersScraper()
    saved_count = await scraper.update_trades()
    print(f"成功保存 {saved_count} 条交易记录")

if __name__ == "__main__":
    asyncio.run(main()) 