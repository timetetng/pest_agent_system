FROM python:3.10-slim-bullseye

# 安装系统依赖、wkhtmltopdf 和 中文字体
RUN apt-get update && apt-get install -y \
    build-essential \
    wkhtmltopdf \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件并安装 (利用缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码与模型
COPY . /app

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
