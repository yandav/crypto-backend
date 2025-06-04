import asyncio
import sys
import os

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# 导入trade_scraper模块
from trade_scraper import AoyingCapitalScraper, MockTradeGenerator

async def main():
    print("开始抓取熬鹰资本的交易数据...")
    
    # 尝试使用真实爬虫，允许在失败时回退到模拟数据
    scraper = AoyingCapitalScraper(fallback_to_mock=True)
    count = await scraper.update_trades()
    
    if count > 0:
        print(f"成功获取并保存 {count} 条交易记录")
    else:
        print("未能获取任何交易记录")
        
    # 可选：如果想要强制使用模拟数据，可以取消下面的注释
    # print("生成额外的模拟交易数据...")
    # mock_generator = MockTradeGenerator(trader_name="熬鹰资本")
    # mock_count = await mock_generator.update_trades(count=5)
    # print(f"成功生成 {mock_count} 条额外的模拟交易记录")

if __name__ == "__main__":
    asyncio.run(main()) 