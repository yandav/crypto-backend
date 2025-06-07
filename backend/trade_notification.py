# trade_notification.py

import logging
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from database import get_db_session
from models import Trade, Trader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradeNotifier:
    """交易通知系统，用于在检测到新交易时通知用户"""
    
    def __init__(self):
        # 从环境变量获取邮件配置
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.example.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', 'crypto-monitor@example.com')
        self.to_emails = os.getenv('TO_EMAILS', '').split(',')
        
        # 是否启用通知
        self.email_enabled = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
        
        # 上次检查时间
        self.last_check_time = datetime.utcnow() - timedelta(minutes=30)
    
    def get_new_trades(self, trader_name: str = "熬鹰资本") -> List[Dict[str, Any]]:
        """获取指定交易员的新交易"""
        new_trades = []
        
        try:
            with get_db_session() as session:
                # 获取交易员ID
                trader = session.query(Trader).filter(Trader.name == trader_name).first()
                if not trader:
                    logger.error(f"交易员不存在: {trader_name}")
                    return []
                
                # 查询上次检查后的新交易，使用entry_time而不是created_at
                trades = session.query(Trade).filter(
                    Trade.trader_id == trader.id,
                    Trade.entry_time >= self.last_check_time
                ).order_by(Trade.entry_time.desc()).all()
                
                # 格式化交易数据
                for trade in trades:
                    trade_data = {
                        "id": trade.id,
                        "symbol": trade.symbol,
                        "direction": trade.direction,
                        "entry_price": trade.entry_price,
                        "leverage": trade.leverage,
                        "position_size": trade.position_size,
                        "status": trade.status,
                        "entry_time": trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if trade.entry_time else None,
                        "exit_time": trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else None,
                        "exit_price": trade.exit_price,
                        "pnl": trade.pnl,
                        "roe": trade.roe,
                        "notes": trade.notes
                    }
                    new_trades.append(trade_data)
                
                # 更新上次检查时间
                self.last_check_time = datetime.utcnow()
                
                return new_trades
        
        except Exception as e:
            logger.error(f"获取新交易失败: {str(e)}")
            return []
    
    def send_email_notification(self, trades: List[Dict[str, Any]]) -> bool:
        """发送邮件通知"""
        if not self.email_enabled or not trades:
            return False
        
        try:
            # 创建邮件内容
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'熬鹰资本新交易通知 - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # 创建HTML内容
            html_content = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    .long { color: green; }
                    .short { color: red; }
                    .header { background-color: #4CAF50; color: white; padding: 10px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>熬鹰资本新交易通知</h2>
                    <p>检测到以下新交易：</p>
                </div>
                <table>
                    <tr>
                        <th>交易对</th>
                        <th>方向</th>
                        <th>入场价格</th>
                        <th>杠杆</th>
                        <th>仓位大小</th>
                        <th>入场时间</th>
                        <th>状态</th>
                    </tr>
            """
            
            for trade in trades:
                direction_class = "long" if trade["direction"] == "LONG" else "short"
                direction_text = "多" if trade["direction"] == "LONG" else "空"
                
                html_content += f"""
                    <tr>
                        <td>{trade["symbol"]}</td>
                        <td class="{direction_class}">{direction_text}</td>
                        <td>{trade["entry_price"]}</td>
                        <td>{trade["leverage"]}x</td>
                        <td>{trade["position_size"]}</td>
                        <td>{trade["entry_time"]}</td>
                        <td>{"开仓" if trade["status"] == "OPEN" else "平仓"}</td>
                    </tr>
                """
            
            html_content += """
                </table>
                <p>此邮件由系统自动发送，请勿回复。</p>
            </body>
            </html>
            """
            
            # 添加HTML内容
            msg.attach(MIMEText(html_content, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"成功发送邮件通知，共 {len(trades)} 条交易")
            return True
        
        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}")
            return False
    
    def check_and_notify(self) -> int:
        """检查新交易并发送通知"""
        try:
            # 获取新交易
            new_trades = self.get_new_trades()
            
            if not new_trades:
                logger.info("没有检测到新交易")
                return 0
            
            logger.info(f"检测到 {len(new_trades)} 条新交易")
            
            # 发送邮件通知
            if self.email_enabled:
                self.send_email_notification(new_trades)
            
            return len(new_trades)
        
        except Exception as e:
            logger.error(f"检查和通知失败: {str(e)}")
            return 0

# 单例模式，全局通知器
notifier = TradeNotifier()

def check_new_trades() -> int:
    """检查新交易的全局函数，可被调度器调用"""
    return notifier.check_and_notify()

if __name__ == "__main__":
    # 测试通知系统
    result = check_new_trades()
    print(f"检测到 {result} 条新交易") 