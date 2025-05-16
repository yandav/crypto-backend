import pandas as pd

def calculate_ema(prices, period=25):
    df = pd.DataFrame(prices, columns=["price"])
    ema = df["price"].ewm(span=period, adjust=False).mean()
    return round(ema.iloc[-1], 4)

def append_ema(data):
    for item in data:
        # 模拟一个历史价格序列用于计算
        prices = [item["price"]] * 30
        item["ema25"] = calculate_ema(prices, period=25)
    return data
