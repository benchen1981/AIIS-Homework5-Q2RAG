"""
Enhanced Streamlit Application - Enterprise Document Intelligence Platform
Multi-page application with upload, search, and admin features
Version 2.0 - Enhanced with API info, better upload, summaries, and deletion
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
import json

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_INTERNAL_URL = "http://backend:8000"  # Fallback for internal networking

# Page configuration
st.set_page_config(
    page_title="企業文件智能平台",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .source-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .api-info {
        background-color: #e8f5e9;
        padding: 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.9rem;
    }
    .status-pending { color: #ff9800; }
    .status-processing { color: #2196f3; }
    .status-completed { color: #4caf50; }
    .status-failed { color: #f44336; }
</style>
""", unsafe_allow_html=True)

# Helper functions
def get_api_info():
    """Get API and model information"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Try to get more info from config endpoint if available
            try:
                config_response = requests.get(f"{API_BASE_URL}/api/config", timeout=1)
                if config_response.status_code == 200:
                    config = config_response.json()
                    return {
                        "status": "healthy",
                        "provider": config.get("llm_provider", "未知"),
                        "model": config.get("llm_model", "未知"),
                        "timestamp": data.get("timestamp")
                    }
            except:
                pass
            # Fallback to basic info
            return {
                "status": "healthy",
                "provider": os.getenv("LLM_PROVIDER", "OpenRouter"),
                "model": os.getenv("OPENROUTER_MODEL", "gemini-2.0-flash"),
                "timestamp": data.get("timestamp")
            }
    except:
        pass
    
    try:
        response = requests.get(f"{API_INTERNAL_URL}/api/health", timeout=2)
        if response.status_code == 200:
            return {"status": "healthy", "provider": "未知", "model": "未知"}
    except:
        pass
    
    return {"status": "unhealthy", "provider": "N/A", "model": "N/A"}

def check_api_health():
    """Check if API is running"""
    info = get_api_info()
    return info["status"] == "healthy"

def upload_document(file, document_type=None):
    """Upload document to API with enhanced error handling"""
    try:
        # Validate file
        if file.size > 50 * 1024 * 1024:  # 50MB
            return {"error": "文件大小超過 50MB 限制"}
        
        # Prepare upload
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {}
        if document_type and document_type != "自動偵測":
            data["document_type"] = document_type
        
        # Upload with timeout
        response = requests.post(
            f"{API_BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 409:
             return {"error": "重複上傳：該文件已存在於系統中。"}
        else:
            try:
                error_detail = response.json().get("detail", response.text[:200])
            except:
                error_detail = response.text[:200]
            return {"error": f"上傳失敗 (HTTP {response.status_code}): {error_detail}"}
    
    except requests.exceptions.Timeout:
        return {"error": "上傳超時，請稍後再試"}
    except requests.exceptions.ConnectionError:
        return {"error": "無法連接到後端 API"}
    except Exception as e:
        return {"error": f"上傳錯誤: {str(e)}"}

def get_document_status(doc_id):
    """Get document processing status"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/documents/{doc_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def delete_document(doc_id):
    """Delete a document"""
    try:
        response = requests.delete(f"{API_BASE_URL}/api/documents/{doc_id}", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_documents(status=None, document_type=None):
    """Get list of documents"""
    params = {}
    if status:
        params["status"] = status
    if document_type:
        params["document_type"] = document_type
    
    response = requests.get(f"{API_BASE_URL}/api/documents", params=params)
    return response.json() if response.status_code == 200 else []

def search_documents(query, top_k=4):
    """Search documents using RAG"""
    payload = {"query": query, "top_k": top_k}
    response = requests.post(f"{API_BASE_URL}/api/search/query", json=payload)
    return response.json() if response.status_code == 200 else None

def get_stats():
    """Get system statistics"""
    response = requests.get(f"{API_BASE_URL}/api/stats")
    return response.json() if response.status_code == 200 else None

# Sidebar - API Info and Navigation
st.sidebar.title("📄 文件智能平台")

# Display API info
api_info = get_api_info()
api_healthy = api_info["status"] == "healthy"

if api_healthy:
    st.sidebar.success("✅ API 已連接")
    st.sidebar.markdown(f"""
    <div class="api-info">
    <b>🤖 LLM 提供商:</b> {api_info['provider']}<br>
    <b>📦 模型:</b> {api_info['model']}
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.error("⚠️ API 未連接")
    st.sidebar.info("請確認後端服務已啟動")

# Navigation
page = st.sidebar.radio(
    "導航",
    ["🏠 首頁", "📤 上傳文件", "🔍 智能搜尋", "📊 管理後台"]
)

# Page: Home
if page == "🏠 首頁":
    st.markdown('<div class="main-header">企業文件智能平台</div>', unsafe_allow_html=True)
    st.markdown("### AI 驅動的文件管理與查詢系統")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("📄 **多格式支援**\n\nPDF、DOCX、TXT 等格式")
    
    with col2:
        st.info("🤖 **AI 智能抽取**\n\n自動提取關鍵資訊")
    
    with col3:
        st.info("🔍 **語義搜尋**\n\n基於 RAG 的智能問答")
    
    st.markdown("---")
    
    # System statistics
    if api_healthy:
        st.subheader("📊 系統概況")
        stats = get_stats()
        
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("總文件數", stats.get("total_documents", 0))
            
            with col2:
                st.metric("已處理", stats.get("completed_documents", 0))
            
            with col3:
                st.metric("文本塊數", stats.get("total_chunks", 0))
            
            with col4:
                st.metric("查詢次數", stats.get("total_queries", 0))
    
    st.markdown("---")
    st.markdown("### 🚀 快速開始")
    st.markdown("""
    1. **上傳文件**: 點擊左側「上傳文件」上傳 PDF、DOCX 等文件
    2. **等待處理**: 系統自動提取文本並建立索引
    3. **智能搜尋**: 使用自然語言查詢文件內容
    4. **查看結果**: 獲得 AI 生成的答案和來源引用
    """)

# Page: Upload
elif page == "📤 上傳文件":
    st.markdown('<div class="main-header">上傳文件</div>', unsafe_allow_html=True)
    
    if not api_healthy:
        st.error("API 未連接，無法上傳文件")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "選擇文件",
                type=["pdf", "docx", "doc", "txt"],
                help="支援 PDF、DOCX、TXT 格式，最大 50MB"
            )
        
        with col2:
            document_type = st.selectbox(
                "文件類型",
                ["自動偵測", "contract", "sop", "official_document", "report", "other"]
            )
        
        if uploaded_file:
            st.info(f"📄 **檔名**: {uploaded_file.name}")
            st.info(f"📦 **大小**: {uploaded_file.size / 1024:.2f} KB")
            st.info(f"📋 **類型**: {uploaded_file.type}")
            
            if st.button("🚀 上傳並處理", type="primary"):
                with st.spinner("上傳中..."):
                    result = upload_document(uploaded_file, document_type)
                    
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    elif "id" in result:
                        st.success(f"✅ 上傳成功！文件 ID: {result['id']}")
                        
                        # Show status tracking
                        status_placeholder = st.empty()
                        progress_bar = st.progress(0)
                        
                        doc_id = result['id']
                        max_wait = 30  # 30 seconds max
                        
                        for i in range(max_wait):
                            doc_status = get_document_status(doc_id)
                            if doc_status:
                                status = doc_status.get('status', 'unknown')
                                status_placeholder.info(f"⏳ 處理狀態: **{status}**")
                                
                                if status == 'completed':
                                    progress_bar.progress(100)
                                    st.success("✅ 文件處理完成！")
                                    break
                                elif status == 'failed':
                                    progress_bar.progress(100)
                                    error_msg = doc_status.get('error_message', '未知錯誤')
                                    st.error(f"❌ 處理失敗: {error_msg}")
                                    break
                                elif status == 'processing':
                                    progress_bar.progress(min(50 + i * 2, 90))
                                else:  # pending
                                    progress_bar.progress(min(i * 3, 40))
                            
                            time.sleep(1)
                    else:
                        st.warning("⚠️ 上傳響應格式異常")
        
        st.markdown("---")
        st.subheader("📋 最近上傳")
        
        recent_docs = get_documents()
        if recent_docs:
            df = pd.DataFrame(recent_docs)
            df['upload_date'] = pd.to_datetime(df['upload_date']).dt.strftime('%Y-%m-%d %H:%M')
            df['file_size_mb'] = (df['file_size_bytes'] / 1024 / 1024).round(2)
            
            st.dataframe(
                df[['filename', 'document_type', 'status', 'upload_date', 'file_size_mb']].head(10),
                use_container_width=True
            )
        else:
            st.info("尚無上傳文件")

# Page: Search
elif page == "🔍 智能搜尋":
    st.markdown('<div class="main-header">智能搜尋</div>', unsafe_allow_html=True)
    
    if not api_healthy:
        st.error("API 未連接，無法執行搜尋")
    else:
        # Search interface
        query = st.text_input(
            "輸入問題或關鍵字",
            placeholder="例如：合約的有效期限是多久？",
            help="使用自然語言提問，系統會從文件庫中找到相關資訊"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            top_k = st.slider("檢索段落數", 1, 10, 4)
        
        if st.button("🔍 搜尋", type="primary") and query.strip():
            with st.spinner("搜尋中..."):
                result = search_documents(query, top_k)
                
                if result and "answer" in result:
                    # Display summary
                    st.markdown("### 📝 摘要")
                    summary_lines = result["answer"].split("\\n")[:3]  # First 3 lines as summary
                    st.info("\\n".join(summary_lines))
                    
                    # Display full answer
                    st.markdown("### 💡 完整回答")
                    st.markdown(f'<div class="source-box">{result["answer"]}</div>', unsafe_allow_html=True)
                    
                    # Display performance metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("檢索時間", f"{result.get('retrieval_time_ms', 0)} ms")
                    with col2:
                        st.metric("生成時間", f"{result.get('llm_time_ms', 0)} ms")
                    with col3:
                        st.metric("總時間", f"{result.get('total_time_ms', 0)} ms")
                    
                    # Display sources
                    st.markdown("### 📚 依據片段")
                    sources = result.get('sources', [])
                    for i, source in enumerate(sources):
                        doc_id = source.get('document_id', '')
                        filename = source.get('filename', doc_id) # API now returns filename
                        
                        # Use filename for display, doc_id (UUID) for link if valid
                        display_name = filename if filename else "未知文件"
                        
                        # Check if doc_id looks like a UUID to build link
                        download_link = ""
                        if len(doc_id) > 10: # Simple heuristic check for UUID
                             download_link = f" [📥 開啟檔案]({API_BASE_URL}/api/documents/{doc_id}/content)"

                        with st.expander(f"來源 {i+1} - {display_name} (相似度: {source.get('score', 0):.3f})"):
                            st.markdown(f"**文件**: {display_name} {download_link}")
                            st.markdown(f"**文本塊**: {source.get('chunk_index', 'N/A')}")
                            st.markdown(source.get('text', ''))
                else:
                    st.error("搜尋失敗或無結果，請稍後再試")

# Page: Admin
elif page == "📊 管理後台":
    st.markdown('<div class="main-header">管理後台</div>', unsafe_allow_html=True)
    
    if not api_healthy:
        st.error("API 未連接")
    else:
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📄 文件管理", "📈 統計資訊", "⚙️ 系統設定", "🔑 權限管理"])
        
        with tab1:
            st.subheader("文件列表")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox(
                    "狀態篩選",
                    ["全部", "pending", "processing", "completed", "failed"]
                )
            
            with col2:
                type_filter = st.selectbox(
                    "類型篩選",
                    ["全部", "contract", "sop", "official_document", "report", "other"]
                )
            
            with col3:
                if st.button("🔄 重新整理"):
                    st.rerun()
            
            # Get documents
            status = None if status_filter == "全部" else status_filter
            doc_type = None if type_filter == "全部" else type_filter
            docs = get_documents(status, doc_type)
            
            if docs:
                df = pd.DataFrame(docs)
                df['upload_date'] = pd.to_datetime(df['upload_date']).dt.strftime('%Y-%m-%d %H:%M')
                df['file_size_mb'] = (df['file_size_bytes'] / 1024 / 1024).round(2)
                
                # Add status emoji
                status_emoji = {
                    'pending': '⏳',
                    'processing': '⚙️',
                    'completed': '✅',
                    'failed': '❌'
                }
                df['status_display'] = df['status'].map(lambda x: f"{status_emoji.get(x, '')} {x}")
                
                # Display with delete buttons
                for idx, row in df.iterrows():
                    col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 2, 1])
                    
                    with col1:
                        st.text(row['filename'])
                    with col2:
                        st.text(row['document_type'] or 'N/A')
                    with col3:
                        st.markdown(f"<span class='status-{row['status']}'>{row['status_display']}</span>", unsafe_allow_html=True)
                    with col4:
                        st.text(row['upload_date'])
                    with col5:
                        st.text(f"{row['file_size_mb']} MB")
                    with col6:
                        if st.button("🗑️", key=f"del_{row['id']}"):
                            if delete_document(row['id']):
                                st.success("已刪除")
                                st.rerun()
                            else:
                                st.error("刪除失敗")
            else:
                st.info("無符合條件的文件")
        
        with tab2:
            st.subheader("系統統計")
            stats = get_stats()
            
            if stats:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("總文件數", stats['total_documents'])
                    st.metric("已完成", stats['completed_documents'])
                    st.metric("處理失敗", stats['failed_documents'])
                
                with col2:
                    st.metric("文本塊總數", stats['total_chunks'])
                    st.metric("查詢總數", stats['total_queries'])
                    
                    if stats['completed_documents'] > 0:
                        avg_chunks = stats['total_chunks'] / stats['completed_documents']
                        st.metric("平均塊數/文件", f"{avg_chunks:.1f}")
        
        with tab3:
            st.subheader("⚙️ 系統設定")
            
            # Fetch current config
            try:
                config_res = requests.get(f"{API_BASE_URL}/api/admin/config")
                config = config_res.json() if config_res.status_code == 200 else {}
            except:
                config = {}

            st.markdown("### 🎫 Token 用量限制")
            
            current_limit = config.get("token_limit", {"value": 100000})
            if isinstance(current_limit, dict):
                limit_val = int(current_limit.get("value", 100000))
            else:
                limit_val = int(current_limit)

            new_limit = st.number_input(
                "每日最大 Token 上限",
                min_value=1000,
                max_value=10000000,
                value=limit_val,
                step=1000,
                help="設定系統每日可使用的最大 Token 數量"
            )
            
            if st.button("💾 儲存設定"):
                payload = {
                    "key": "token_limit",
                    "value": {"value": new_limit},
                    "description": "Daily system token limit"
                }
                try:
                    res = requests.post(f"{API_BASE_URL}/api/admin/config", json=payload)
                    if res.status_code == 200:
                        st.success("設定已更新")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"更新失敗: {res.text}")
                except Exception as e:
                    st.error(f"連線錯誤: {str(e)}")

            st.markdown("### 📊 目前用量")
            stats = get_stats()
            if stats and "token_usage" in stats:
                usage = stats["token_usage"]
                total = usage.get("total", 0)
                limit = usage.get("limit", new_limit)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("已使用 Token", f"{total:,}")
                with col2:
                    st.metric("剩餘額度", f"{max(0, limit - total):,}")
                
                progress = min(1.0, total / limit) if limit > 0 else 1.0
                st.progress(progress)
                if progress > 0.9:
                    st.warning("⚠️ 用量即將達到上限")
            
            st.markdown("---")
            st.markdown("**API 資訊**")
            st.code(f"""
LLM 提供商: {api_info['provider']}
模型: {api_info['model']}
API 端點: {API_BASE_URL}
狀態: {api_info['status']}
            """)

        with tab4:
            st.info("權限管理功能開發中...")
# Footer
st.markdown("---")
st.markdown(
    f'<div style="text-align: center; color: #666;">企業文件智能平台 v2.0 | Powered by {api_info["provider"]} ({api_info["model"]})</div>',
    unsafe_allow_html=True
)
