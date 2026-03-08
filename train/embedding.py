import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# 1. 配置
model_name = "BAAI/bge-small-zh-v1.5"
persist_directory = "./agri_vector_db"

# 2. 初始模型
embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 3. 这里的 raw_blocks 建议手动加入“物理方法”的片段（基于你提供的PDF内容）
# 注意：我根据你上传的 PDF 增加了物理防治的具体技术块
enhanced_blocks = [
    {
        "content": "设施瓜类物理防治技术：色板诱杀（黄板诱蚜虫/白粉虱，蓝板诱蓟马）；物理隔离（防虫网覆盖、银灰色地膜驱避）；灯光诱杀（杀虫灯）；幼瓜套袋。",
        "metadata": {"source": "设施瓜类规范", "type": "物理方法"}
    },
    {
        "content": "设施瓜类主要病害：白粉病、霜霉病、蔓枯病、灰霉病。主要虫害：蓟马、瓜实蝇、蚜虫、白粉虱。",
        "metadata": {"source": "设施瓜类规范", "type": "病虫清单"}
    }
]

# 4. 构建前清理（防止复读机）
if os.path.exists(persist_directory):
    import shutil
    shutil.rmtree(persist_directory)

documents = [Document(page_content=b["content"], metadata=b["metadata"]) for b in enhanced_blocks]
vector_db = Chroma.from_documents(documents, embeddings, persist_directory=persist_directory)

# 5. 带指令的检索 (BGE 官方推荐前缀)
def smart_search(user_query):
    # 针对检索任务添加特定指令前缀
    instruction = "为这个句子生成表示以用于检索相关文章："
    full_query = instruction + user_query
    
    # 增加返回数量 k=4，并按得分去重
    results = vector_db.similarity_search_with_score(full_query, k=4)
    
    seen_content = set()
    print(f"\n--- 针对提问: {user_query} ---")
    for doc, score in results:
        if doc.page_content not in seen_content:
            print(f"[{doc.metadata['type']}] (Score: {score:.4f}): {doc.page_content}")
            seen_content.add(doc.page_content)

smart_search("设施瓜类容易得哪些病？怎么用物理方法防治？")
