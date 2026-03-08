import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 基础配置
    API_KEY = os.getenv("LLM_API_KEY", "your-default-key")
    BASE_URL = os.getenv("LLM_BASE_URL", "https://hcg.pippi.top/v1")
    MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-3-flash-preview群友免费")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    
    # 路径配置
    DB_DIR = "./data/vector_db"
    UPLOAD_DIR = "./data/uploads"
    MODEL_PATH = "./models/best_resnet50_pests.pth"

# 确保数据目录存在
os.makedirs(Config.DB_DIR, exist_ok=True)
os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
