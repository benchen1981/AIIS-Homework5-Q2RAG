import streamlit as st
import requests

N8N_SEARCH_ENDPOINT = "https://your-n8n.example.com/webhook/search_rag"  # <<REPLACE_ME>>

st.set_page_config(page_title="Document RAG Search", layout="wide")
st.title("企業文件庫 — 智能查詢 (RAG)")

q = st.text_input("輸入問題或關鍵字：")
top_k = st.slider("檢索段落數 (top_k)", 1, 10, 4)

if st.button("查詢") and q.strip():
    with st.spinner("向系統查詢並生成回答…"):
        payload = {"query": q, "top_k": top_k}
        res = requests.post(N8N_SEARCH_ENDPOINT, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            st.subheader("回答")
            st.write(data.get("answer","(no answer)"))
            st.subheader("依據片段 (sources)")
            for s in data.get("sources",[]):
                st.markdown(f"**Doc:** {s.get('document_id')} — chunk {s.get('chunk_index')}")
                st.write(s.get('text'))
        else:
            st.error(f"查詢失敗：{res.status_code} {res.text}")
