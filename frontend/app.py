import streamlit as st
import requests
import os
import re
import json
import plotly.graph_objects as go

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
# 檢查是否在 Cloud Run 環境
if "run.app" in BACKEND_URL:
    # Cloud Run: 使用 HTTPS
    BACKEND_URL = BACKEND_URL.replace("http://", "https://")

st.set_page_config(
    page_title="ToS Sentinel",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)
#st.set_page_config(page_title="ToS Sentinel", layout="wide", page_icon="🛡️")

# --- CSS (保持不變) ---
st.markdown("""
    <style>
    html {scroll-behavior: smooth;}
    .highlight { background-color: #ffff00; color: black; padding: 2px 4px; border-radius: 4px; font-weight: bold; border: 1px solid #e6b800; }
    .evidence-link { font-size: 0.8em; color: #d9534f; text-decoration: none; margin-left: 8px; cursor: pointer; background: #fdf2f2; padding: 2px 6px; border-radius: 4px; border: 1px solid #ebccd1; }
    .evidence-link:hover { background: #f2dede; }
    .badge-high { background-color: #d9534f; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-right: 5px;}
    .badge-medium { background-color: #f0ad4e; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-right: 5px;}
    .badge-low { background-color: #5bc0de; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-right: 5px;}
    .source-badge { font-size: 0.75em; background-color: #e0e0e0; color: #333; padding: 2px 6px; border-radius: 10px; margin-left: 8px; border: 1px solid #ccc; }
    .status-log { font-family: monospace; color: #0068c9; background: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .subtitle { color: gray; font-size: 14px; margin-top: -15px; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def fetch_models():
    try:
        resp = requests.get(f"{BACKEND_URL}/models", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("models", ["gemini-1.5-flash"])
    except: pass
    return ["gemini-1.5-flash"]

def create_gauge_chart(score):
    color = "green"
    if score > 35: color = "orange"
    if score > 75: color = "red"
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Risk Score", 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'steps': [
                {'range': [0, 35], 'color': 'rgba(0, 255, 0, 0.1)'},
                {'range': [35, 75], 'color': 'rgba(255, 165, 0, 0.1)'},
                {'range': [75, 100], 'color': 'rgba(255, 0, 0, 0.1)'}],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
    return fig

def create_flexible_pattern(quote):
    quote = re.escape(quote)
    tokens = re.split(r'\\\W+', quote)
    tokens = [t for t in tokens if t]
    pattern = r"[\W\s]*?".join(tokens)
    return pattern

# --- Sidebar ---
with st.sidebar:
    st.info("""
    **🛡️ What is ToS Sentinel?**
    
    ToS Sentinel is an **AI-powered Risk Auditor** for legal documents. 
    Instead of reading the entire "Terms of Service", simply tell the AI **what you want to do**.
    
    **How it works:**
    1. **Dynamic Crawling**: Recursively finds related policies (Privacy, Guidelines).
    2. **RAG Pipeline**: Retrieves only the clauses relevant to your intent.
    3. **Risk Analysis**: Highlights specific violations and privacy trade-offs.
    """)
    
    st.divider()

    st.header("⚙️ Configuration")
    available_models = fetch_models()
    selected_model = st.selectbox("Select Model", available_models, index=0)
    enable_rag = st.toggle("Enable Deep RAG (Multi-page)", value=True)
    st.divider()
    url_input = st.text_input("Target URL", "https://terms2.line.me/official_account_terms_tw")
    intent_input = st.text_area("User Intent", "我想創帳號跟別人聊天", height=150)
    analyze_btn = st.button("🚀 Analyze Risk", type="primary", use_container_width=True)

# --- Main Interface ---
st.title("🛡️ ToS Sentinel")
st.markdown("""
<div class='subtitle'>
    <b>Cloud Computing and Data Analytics Final Project</b> by <code>314511063 李兆翔</code><br>
    <i>Developed with AI Assistance</i>
</div>
""", unsafe_allow_html=True)

if analyze_btn and url_input:
    # 建立一個佔位符來顯示 Log
    status_box = st.empty()
    result_container = st.container()

    try:
        payload = {
            "url": url_input, 
            "intent": intent_input if intent_input else None, 
            "model_name": selected_model,
            "enable_rag": enable_rag
        }
        
        # 使用 stream=True 進行串流請求
        with requests.post(f"{BACKEND_URL}/analyze", json=payload, stream=True) as resp:
            final_data = None
            
            # 迭代讀取後端傳回的每一行 JSON
            for line in resp.iter_lines():
                if line:
                    event = json.loads(line.decode('utf-8'))
                    
                    if event["type"] == "log":
                        # 更新進度條文字
                        status_box.markdown(f"<div class='status-log'>{event['msg']}</div>", unsafe_allow_html=True)
                    
                    elif event["type"] == "error":
                        st.error(event["msg"])
                        break
                        
                    elif event["type"] == "result":
                        final_data = event["data"]

        # 處理最終結果
        if final_data:
            status_box.empty() # 清除進度文字
            
            data = final_data
            result = data.get("result", {})
            usage = data.get("token_usage", {})
            scraped_text = data.get("scraped_content", "")
            
            risks = result.get("risks", [])
            suggestions = result.get("suggestions", [])
            overview = result.get("overview", "")
            ai_score = result.get('risk_score', 0)

            # --- Highlighting Logic ---
            highlighted_content = scraped_text
            matched_indices = set()
            for idx, item in enumerate(risks):
                quote = item.get("quote", "").strip()
                severity = item.get("severity", "Low")
                if quote and len(quote) > 3:
                    try:
                        regex_pattern = create_flexible_pattern(quote)
                        match = re.search(regex_pattern, highlighted_content, re.IGNORECASE)
                        if match:
                            matched_indices.add(idx)
                            final_id = idx + 1
                            anchor_id = f"evidence-{final_id}"
                            found_text = match.group(0)
                            replacement = f"<span id='{anchor_id}' class='highlight'><b>[{final_id}-{severity}]</b> {found_text}</span>"
                            highlighted_content = highlighted_content.replace(found_text, replacement, 1)
                    except: pass

            # --- Rendering Results ---
            with result_container:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.plotly_chart(create_gauge_chart(ai_score), use_container_width=True)
                    st.info("**Score:** AI Subjective Assessment")
                with col2:
                    st.subheader("📊 Token Usage")
                    st.metric("Total Tokens", f"{usage.get('total_token', 0):,}")
                    st.divider()
                    debug_info = data.get("debug_info", {})
                    st.markdown(f"**Engine:** {debug_info.get('engine')}")

                st.divider()
                st.subheader("📝 Analysis Report")
                st.success(f"**Overview:** {overview}")
                
                col_risk, col_sugg = st.columns(2)
                with col_risk:
                    st.markdown("### 🚨 Risks & Violations")
                    if risks:
                        risk_html = "<ul style='padding-left: 20px; list-style: none;'>"
                        for idx, item in enumerate(risks):
                            point = item.get("point")
                            severity = item.get("severity", "Low")
                            source_name = item.get("source_name", "Main ToS")
                            
                            badge_class = "badge-low"
                            if severity == "High": badge_class = "badge-high"
                            elif severity == "Medium": badge_class = "badge-medium"
                            
                            link_html = ""
                            if idx in matched_indices:
                                anchor_id = f"evidence-{idx+1}"
                                link_html = f"<a href='#{anchor_id}' class='evidence-link'>Evidence #{idx+1}</a>"
                            else:
                                link_html = "<span style='color:gray; font-size:0.8em; margin-left:5px;'>(Quote mismatch)</span>"
                            
                            source_html = ""
                            if "Main" not in source_name:
                                source_html = f"<span class='source-badge'>📂 {source_name}</span>"
                            
                            risk_html += f"<li style='margin-bottom: 15px;'><span class='{badge_class}'>{severity}</span><b>{point}</b>{source_html}{link_html}</li>"
                        risk_html += "</ul>"
                        st.markdown(risk_html, unsafe_allow_html=True)
                    else:
                        st.success("No significant risks found.")

                with col_sugg:
                    st.markdown("### 💡 AI Suggestions")
                    if suggestions:
                        for s in suggestions:
                            st.info(s)
                    else:
                        st.caption("No suggestions.")
                
                st.divider()
                st.subheader("🔍 Evidence Context")
                with st.container(height=600, border=True):
                    st.markdown(highlighted_content.replace("\n", "<br>"), unsafe_allow_html=True)
                
                with st.expander("🛠️ Debug & RAG Trace"):
                    st.json(data)
                    kb = debug_info.get("knowledge_base", [])
                    if kb:
                        st.markdown("### 📚 Knowledge Base")
                        for src in kb: st.markdown(f"- `{src}`")
                    retrieved = debug_info.get("retrieved_sources", [])
                    if retrieved:
                        st.markdown("### 🎯 Retrieved Sources")
                        for src in retrieved: st.markdown(f"- `{src}`")

    except Exception as e:
        st.error(f"Error: {e}")