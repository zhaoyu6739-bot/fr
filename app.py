import streamlit as st
import json
import os
from openai import OpenAI
from datetime import datetime

# ==========================================
# 1. API 配置 (安全读取云端 Secrets)
# ==========================================
SILICON_TOKEN = st.secrets.get("SILICON_TOKEN", "")

@st.cache_resource
def get_client():
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
# 2. 读取带答案的终极题库
# ==========================================
@st.cache_data
def load_data():
    file_path = "book_complete.json"
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [page for page in data if page.get("data")]

# ==========================================
# 3. 构建网页界面与侧边栏
# ==========================================
st.set_page_config(page_title="法语智能刷题器", page_icon="🇫🇷", layout="centered")

client = get_client()

# --- 侧边栏：导航与存档管理 ---
st.sidebar.header("🎯 学习控制台")
if not client:
    st.sidebar.warning("⚠️ 待配置：请在 Secrets 中设置 SILICON_TOKEN")
else:
    st.sidebar.success("✅ AI 引擎已就绪")

mode = st.sidebar.radio("选择模式", ["📖 全书刷题", "📕 我的错题本"])

# 错题存档管理
with st.sidebar.expander("💾 存档管理"):
    if st.session_state.wrong_questions:
        wrong_json = json.dumps(st.session_state.wrong_questions, ensure_ascii=False, indent=4)
        st.download_button(
            label="📥 下载错题本存档",
            data=wrong_json,
            file_name=f"french_wrong_{datetime.now().strftime('%m%d')}.json",
            mime="application/json"
        )
    
    uploaded_file = st.file_uploader("📤 上传历史存档", type="json")
    if uploaded_file is not None:
        try:
            st.session_state.wrong_questions = json.load(uploaded_file)
            st.sidebar.success("存档已加载！")
        except:
            st.sidebar.error("文件格式不对哦")

# 加载主数据
pages = load_data()
if not pages:
    st.error("找不到 book_complete.json 文件！")
    st.stop()

display_questions = []
if mode == "📖 全书刷题":
    page_options = {f"第 {p['page']} 页 (共 {len(p['data'])} 题)": p for p in pages}
    selected_option = st.sidebar.selectbox("选择页面", list(page_options.keys()))
    display_questions = page_options[selected_option]["data"]
    st.title(f"🇫🇷 当前练习：{selected_option.split(' ')[0]}")
else:
    st.title("📕 我的错题本")
    display_questions = st.session_state.wrong_questions
    if not display_questions:
        st.info("错题本是空的。点击全书刷题模式下的“⭐ 收藏”按钮来添加。")
    if st.sidebar.button("🗑️ 清空所有收藏"):
        st.session_state.wrong_questions = []
        st.rerun()

# ==========================================
# 4. 题目渲染逻辑 (超大字体版)
# ==========================================
for idx, q in enumerate(display_questions):
    block = q.get('exercise_block') or '练习'
    num = q.get('question_number') or (idx + 1)
    
    # 题目编号字体：22px
    st.markdown(f"<div style='font-size: 22px; color: #666; font-weight: bold;'>{block} - 第 {num} 题</div>", unsafe_allow_html=True)
    
    # 题目核心文本：30px (超大字体，带浅灰背景块，方便平板阅读)
    st.markdown(
        f"<div style='font-size: 30px; font-weight: 500; background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #ddd;'>"
        f"{q['question_text']}"
        f"</div>", 
        unsafe_allow_html=True
    )

    # 提示词字体：20px
    if q.get('hints'):
        st.markdown(f"<div style='font-size: 20px; color: #007B83; margin-bottom: 10px;'>💡 提示: {q['hints']}</div>", unsafe_allow_html=True)
        
    user_answer = st.text_input("📝 输入你的答案：", key=f"input_{mode}_{idx}")
    standard_answer = q.get('answer', '')
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("✅ 对答案", key=f"check_{mode}_{idx}"):
            if not user_answer.strip():
                st.warning("请先输入答案。")
            elif user_answer.strip().lower() == standard_answer.strip().lower():
                st.success(f"🎉 正确！答案: {standard_answer}")
            else:
                st.error(f"❌ 答错了。标准答案：{standard_answer}")
                
    with col2:
        if st.button("🧠 AI 讲解", key=f"exp_{mode}_{idx}"):
            if not client:
                st.warning("请先配置 API 密钥。")
            else:
                with st.spinner("AI 老师正在分析..."):
                    prompt = f"法语语法题: {q['question_text']}\n提示词: {q.get('hints','无')}\n答案: {standard_answer}\n学生答案: {user_answer}\n请幽默讲解。"
                    try:
                        response = client.chat.completions.create(
                            model="Qwen/Qwen2.5-7B-Instruct",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3
                        )
                        st.info(f"👨‍🏫 AI 老师解析：\n\n{response.choices[0].message.content}")
                    except Exception as e:
                        st.error(f"调用失败: {e}")

    with col3:
        if mode == "📖 全书刷题":
            if st.button("⭐ 收藏题目", key=f"fav_{idx}"):
                if q not in st.session_state.wrong_questions:
                    st.session_state.wrong_questions.append(q)
                    st.toast("已加入错题本", icon="⭐")
        else:
            if st.button("🗑️ 移除题目", key=f"rm_{idx}"):
                st.session_state.wrong_questions.pop(idx)
                st.rerun()
                
    st.divider()