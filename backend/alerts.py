def check_ema_alerts(data):
    alerts = []
    for item in data:
        if item["price"] > item["ema25"]:
            alerts.append(f"{item['symbol']} 突破 EMA25")
    return alerts

def check_price_change_alerts(data, threshold=3.0):
    alerts = []
    for item in data:
        if abs(item["change"]) >= threshold:
            alerts.append(f"{item['symbol']} 涨跌幅超过 {threshold}%")
    return alerts

def check_open_interest_alerts(data, threshold=15.0):
    alerts = []
    for item in data:
        change_5m = item.get("openInterestChange", {}).get("5m", 0)
        if change_5m >= threshold:
            alerts.append({
                "symbol": item["symbol"],
                "change_5m": change_5m,
                "openInterest": item["openInterest"]
            })
    return alerts
