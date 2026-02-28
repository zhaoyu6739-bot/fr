import streamlit as st
import json
import os
from openai import OpenAI
from datetime import datetime

# ==========================================
# 1. 安全读取云端 Secrets
# ==========================================
# 这一行在本地会读取 .streamlit/secrets.toml
# 在云端会读取你刚才在 Settings -> Secrets 里填的内容
SILICON_TOKEN = st.secrets.get("SILICON_TOKEN", "")

@st.cache_resource
def get_client():
    # 增加了一个判断，只有密钥以 sk- 开头才初始化，防止报错
    if SILICON_TOKEN and SILICON_TOKEN.startswith("sk-"):
        return OpenAI(
            base_url="https://api.siliconflow.cn/v1", 
            api_key=SILICON_TOKEN
        )
    return None

# 初始化错题 Session
if 'wrong_questions' not in st.session_state:
    st.session_state.wrong_questions = []

# ==========================================
# 2. 渲染逻辑 (包含你要求的字体大小调节)
# ==========================================
st.set_page_config(page_title="法语刷题-安全部署版", page_icon="🇫🇷", layout="centered")

client = get_client()

# 侧边栏状态检查
if not client:
    st.sidebar.warning("⚠️ 待配置：请在 Streamlit 后台 Secrets 中设置 SILICON_TOKEN")
else:
    st.sidebar.success("✅ AI 引擎已就绪")

# ... (此处省略加载 book_complete.json 的代码，保持不变) ...

# 假设我们在渲染题目循环中：
def render_question(q, idx, mode):
    block = q.get('exercise_block', '练习')
    num = q.get('question_number', idx + 1)

    # 🚩【字体放大设置处】
    # 题目编号字体：22px
    st.markdown(f"<div style='font-size: 22px; color: #666; font-weight: bold;'>{block} - 第 {num} 题</div>", unsafe_allow_html=True)
    
    # 题目核心文本：30px (超大字体，方便平板阅读)
    st.markdown(
        f"<div style='font-size: 30px; font-weight: 500; background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #ddd;'>"
        f"{q['question_text']}"
        f"</div>", 
        unsafe_allow_html=True
    )

    # 提示词字体：20px
    if q.get('hints'):
        st.markdown(f"<div style='font-size: 20px; color: #007B83;'>💡 提示: {q['hints']}</div>", unsafe_allow_html=True)
    
    # ... (其余输入框和按钮逻辑保持不变) ...