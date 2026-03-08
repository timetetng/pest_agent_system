from openai import OpenAI

def generate_report_stream(pest, conf, context, location, weather_info, config):
    """流式输出 (stream=True)"""
    client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
    prompt = f"""
作为高级农技专家，请生成防控报告。
【现场数据】：位置-{location} | 害虫-{pest}(置信度{conf:.2%}) | 天气-{weather_info}
【知识库参考】：\n{context}
要求：输出 Markdown，结合天气情况给出施药建议（如雨天禁药，高温避险等）。
"""
    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=True
        )
        return response
    except Exception as e:
        return f"生成报告失败: {str(e)}"
