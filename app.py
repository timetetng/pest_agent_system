import streamlit as st
import os
import time
import tempfile
from config import Config
from core.vision import PestVisionModel
from core.rag_engine import AgriRAG
from core.weather import get_weather
from core.agent import generate_report_stream
from core.pdf_exporter import export_md_to_pdf

# 页面设置
st.set_page_config(page_title="智能农业生物安全平台", layout="wide")

# 初始化全局模块 (使用 st.cache_resource 避免每次操作都重新加载模型)
@st.cache_resource
def load_systems():
    vision = PestVisionModel(Config.MODEL_PATH)
    rag = AgriRAG(Config.DB_DIR)
    return vision, rag

vision_model, rag_system = load_systems()

# ================= 侧边栏：系统配置与知识库管理 =================
with st.sidebar:
    st.header("⚙️ 系统配置")
    Config.API_KEY = st.text_input("LLM API Key", value=Config.API_KEY, type="password")
    Config.BASE_URL = st.text_input("LLM Base URL", value=Config.BASE_URL)
    Config.MODEL_NAME = st.text_input("模型名称", value=Config.MODEL_NAME)
    Config.WEATHER_API_KEY = st.text_input("天气 API Key", value=Config.WEATHER_API_KEY, type="password")
    
    st.divider()
    st.header("📚 补充 RAG 知识库")
    uploaded_file = st.file_uploader("上传 PDF/TXT 农技规程", type=['pdf', 'txt'])
    if uploaded_file and st.button("写入知识库"):
        with st.spinner("解析并向量化中..."):
            temp_path = os.path.join(Config.UPLOAD_DIR, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            chunk_count = rag_system.add_file(temp_path)
            st.success(f"成功注入 {chunk_count} 个知识块！")

# ================= 主界面：检测与报告生成 =================
st.title("🌾 云端协同害虫治理 Agent")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 现场图像上传")
    img_file = st.file_uploader("拍摄或上传害虫图片", type=['jpg', 'jpeg', 'png'])
    location_input = st.text_input("发生地点 (例如: 广西崇左市扶绥县)", "广西崇左市扶绥县")
    
    if img_file:
        st.image(img_file, caption="待检测图像", use_container_width=True)

with col2:
    st.subheader("2. 智能研判与报告")
    if img_file and st.button("🚀 开始智能诊断", type="primary"):
        # 保存临时图片
        img_path = os.path.join(Config.UPLOAD_DIR, "temp_img.jpg")
        with open(img_path, "wb") as f:
            f.write(img_file.getbuffer())
        
        with st.status("正在执行多模态诊断...", expanded=True) as status:
            st.write("👀 端侧视觉模型推理中...")
            pest_name, conf = vision_model.predict(img_path)
            
            st.write("☁️ 获取实时气象数据...")
            weather_info = get_weather(location_input, Config.WEATHER_API_KEY)
            
            st.write("📚 检索本地 RAG 知识库...")
            rag_context = rag_system.query(pest_name)
            
            st.write("🧠 Agent 生成最终决策报告...")
            report_md = generate_report(pest_name, conf, rag_context, location_input, weather_info, Config)
            status.update(label="诊断完成！", state="complete")
        
# 生成 Markdown 报告...
        st.markdown(report_md)
        
        # 导出 PDF 功能
        st.write("---")
        col_dl1, col_dl2 = st.columns(2)
        
        # 现有的 MD 下载按钮
        with col_dl1:
            st.download_button(
                label="📥 下载 Markdown 源文件",
                data=report_md,
                file_name="governance_report.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        # 新增的 PDF 下载按钮
        with col_dl2:
            with st.spinner("正在排版并生成 PDF 报告..."):
                pdf_path = export_md_to_pdf(report_md, os.path.join(Config.UPLOAD_DIR, "report.pdf"))
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📑 下载 PDF 正式报告",
                            data=pdf_file,
                            file_name="农业生物安全治理通报.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
