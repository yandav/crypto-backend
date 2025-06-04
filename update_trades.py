import requests
import json

# 调用API更新交易数据
try:
    response = requests.post(
        "http://localhost:5000/api/update_trades",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"use_mock": True, "count": 10})
    )
    print("响应状态码:", response.status_code)
    print("响应内容:", response.text)
except Exception as e:
    print("请求失败:", str(e)) 