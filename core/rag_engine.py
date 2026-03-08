import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class AgriRAG:
    def __init__(self, db_dir):
        self.db_dir = db_dir
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.db = Chroma(persist_directory=self.db_dir, embedding_function=self.embeddings)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    def add_file(self, file_path):
        """支持动态上传 PDF 或 TXT 文件并存入知识库"""
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding='utf-8')
        
        docs = loader.load()
        chunks = self.text_splitter.split_documents(docs)
        self.db.add_documents(chunks)
        return len(chunks)

    def query(self, pest_name, k=3):
        q = f"为这个句子生成表示以用于检索相关文章：针对{pest_name}的绿色防控与化学防治技术方案是什么？"
        results = self.db.similarity_search(q, k=k)
        return "\n".join([f"- {doc.page_content}" for doc in results])
