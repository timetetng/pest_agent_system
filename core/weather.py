# 替换 core/weather.py 的全部内容
import requests
import re

def extract_city(location_str):
    """提取地级市用于免费版天气 API 查询"""
    match = re.search(r'([^省区市]+)市', location_str)
    if match:
        city = match.group(1)
        return re.sub(r'.*(省|自治区|维吾尔|壮族|回族)', '', city)
    return location_str[:2]

def get_weather(location, api_key):
    if not api_key:
        return "未配置天气API，无法获取气象数据。"
    
    parsed_city = extract_city(location)
    url = f"https://api.seniverse.com/v3/weather/now.json?key={api_key}&location={parsed_city}&language=zh-Hans&unit=c"
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            weather = data['results'][0]['now']['text']
            temp = data['results'][0]['now']['temperature']
            return f"当前气象：{weather}，气温 {temp}℃。"
        else:
            # 记录失败状态，但不阻断 Agent 工作
            return "气象数据暂不可用 (地名不匹配或超限)。"
    except Exception:
        return "气象服务连接超时。"
