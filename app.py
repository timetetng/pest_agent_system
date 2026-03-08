import streamlit as st
import os
import time
from config import Config
from core.vision import PestVisionModel
from core.rag_engine import AgriRAG
from core.weather import get_weather
from core.agent import generate_report_stream 
from core.pdf_exporter import export_md_to_pdf

# 页面设置
st.set_page_config(page_title="智能农业生物安全平台", layout="wide")

# 初始化全局模块
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

st.subheader("1. 现场图像上传")

input_col, _ = st.columns([1, 1])
with input_col:
    img_file = st.file_uploader("拍摄或上传害虫图片", type=['jpg', 'jpeg', 'png'])
    location_input = st.text_input("发生地点 (例如: 广西崇左市扶绥县)", "广西崇左市扶绥县")
    
if img_file:
    img_col, _ = st.columns([1, 2]) # 限制图片显示宽度为页面的三分之一左右
    with img_col:
        st.image(img_file, caption="待检测图像", use_container_width=True)

st.divider()

st.subheader("2. 智能研判与报告")
if img_file and st.button("🚀 开始智能诊断", type="primary"):
    # 保存临时图片
    img_path = os.path.join(Config.UPLOAD_DIR, "temp_img.jpg")
    with open(img_path, "wb") as f:
        f.write(img_file.getbuffer())
    
    # 记录总开始时间
    total_t0 = time.time()
    
    # 折叠面板：展示各模块进度与精准耗时
    with st.status("正在执行多模态诊断...", expanded=True) as status:
        t0 = time.time()
        st.write("👀 端侧视觉模型推理中...")
        pest_name, conf = vision_model.predict(img_path)
        t1 = time.time()
        st.markdown(f"**✅ 视觉推理完成** `(耗时: {t1-t0:.2f} 秒)` -> 结果: **{pest_name}**")
        
        t0 = time.time()
        st.write("☁️ 获取实时气象数据...")
        weather_info = get_weather(location_input, Config.WEATHER_API_KEY)
        t1 = time.time()
        st.markdown(f"**✅ 气象数据获取** `(耗时: {t1-t0:.2f} 秒)` -> 状态: {weather_info}")
        
        t0 = time.time()
        st.write("📚 检索本地 RAG 知识库...")
        rag_context = rag_system.query(pest_name)
        t1 = time.time()
        st.markdown(f"**✅ 知识库检索完成** `(耗时: {t1-t0:.2f} 秒)`")
        
        st.write("🧠 Agent 正在思考与撰写报告...")
        status.update(label="正在流式生成决策报告...", state="running")

    # 流式打字机输出 LLM 报告 (由于取消了分栏，这里将全宽显示)
    st.subheader("📝 智能决策报告")
    report_placeholder = st.empty() 
    report_md = ""
    
    t0 = time.time()
    
    stream_response = generate_report_stream(pest_name, conf, rag_context, location_input, weather_info, Config)
    
    if isinstance(stream_response, str): 
        report_placeholder.error(stream_response)
    else:
        for chunk in stream_response:
            if chunk.choices[0].delta.content is not None:
                report_md += chunk.choices[0].delta.content
                report_placeholder.markdown(report_md + "▌") 
        report_placeholder.markdown(report_md)
        
    t1 = time.time()
    total_t1 = time.time()
    
    st.success(f"🎉 诊断完成！LLM 生成耗时: `{t1-t0:.2f} 秒` | 总耗时: `{total_t1-total_t0:.2f} 秒`")
    
    # --- 导出与下载区 ---
    st.write("---")
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.download_button(
            label="📥 下载 Markdown 源文件",
            data=report_md,
            file_name="governance_report.md",
            mime="text/markdown",
            use_container_width=True
        )
        
    with col_dl2:
        with st.spinner("⏳ 正在排版并生成 PDF 报告..."):
            pdf_output_path = os.path.join(Config.UPLOAD_DIR, "report.pdf")
            pdf_path = export_md_to_pdf(report_md, pdf_output_path)
            
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📑 下载 PDF 正式报告",
                        data=pdf_file,
                        file_name="农业生物安全治理通报.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.error("PDF 导出失败，请检查 Docker 环境是否已安装 wkhtmltopdf 和相关字体。")
