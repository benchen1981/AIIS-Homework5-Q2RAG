# Fix for ChromaDB on Streamlit Cloud (SQLite version issue)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import time
from rag_core import RAGSystem

# Page Config
st.set_page_config(page_title="文件智能平台 (Cloud Version)", page_icon="☁️", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2rem; color: #1f77b4; font-weight: bold; }
    .source-box { background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "rag" not in st.session_state:
    st.session_state.rag = RAGSystem()

rag = st.session_state.rag

# Sidebar
st.sidebar.title("☁️ 雲端版設定")

# API Key Handling
if "OPENROUTER_API_KEY" not in st.secrets:
    user_key = st.sidebar.text_input("輸入 OpenRouter API Key", type="password")
    if user_key:
        rag.llm_client.openrouter_api_key = user_key
    else:
        st.sidebar.warning("請輸入 API Key 以啟用 AI 功能")

st.sidebar.markdown("---")
page = st.sidebar.radio("導航", ["📝 聊天與搜尋", "📤 文件管理", "⚙️ 系統設定"])

# ==========================================
# Page: Chat
# ==========================================
if page == "📝 聊天與搜尋":
    st.markdown('<div class="main-header">智能文件問答</div>', unsafe_allow_html=True)

    # Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("請輸入您的問題..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("正在檢索文件並生成回答..."):
                try:
                    result = rag.search(prompt)
                    answer = result["answer"]
                    sources = result["sources"]
                    
                    st.markdown(answer)
                    
                    # Store history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    # Show sources
                    if sources:
                        with st.expander("📚 參考來源"):
                            for idx, src in enumerate(sources):
                                st.markdown(f"**來源 {idx+1}: {src['filename']}**")
                                st.text(src['text'][:200] + "...")
                                
                except Exception as e:
                    st.error(f"發生錯誤: {str(e)}")

# ==========================================
# Page: Upload
# ==========================================
elif page == "📤 文件管理":
    st.subheader("文件上傳與列表")
    
    uploaded_file = st.file_uploader("上傳文件 (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'])
    
    if uploaded_file:
        if st.button("🚀 開始上傳處理"):
            with st.spinner("正在處理文件（解析 > 切塊 > 向量化）..."):
                success, msg = rag.upload_file(uploaded_file)
                if success:
                    st.success(f"上傳成功！文件 `{uploaded_file.name}` 已加入知識庫。")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"上傳失敗: {msg}")

    st.markdown("---")
    st.subheader("已索引文件")
    docs = rag.get_documents()
    
    if docs:
        import pandas as pd
        df = pd.DataFrame(docs)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前沒有文件。請上傳一些文件開始使用。")

# ==========================================
# Page: Admin
# ==========================================
elif page == "⚙️ 系統設定":
    st.subheader("系統維護")
    
    if st.button("🗑️ 清空所有數據 (重置資料庫)"):
        res = rag.clear_database()
        if res is True:
            st.success("資料庫已清空")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"清空失敗: {res}")
            
    st.markdown("---")
    st.info("""
    **版本說明 (Cloud Version)**
    此版本為 Streamlit Cloud 優化版，為了適應無伺服器環境：
    1. 使用 **Lite** 版向量資料庫 (Chroma Persistent Client)。
    2. 使用 **In-Memory/JSON** 儲存元數據。
    3. 不支援複雜的 User/Admin 權限管理。
    4. ⚠️ 注意：每次 Cloud 重啟，上傳的文件可能會遺失 (視掛載硬碟策略而定)。
    """)
