import streamlit as st
import json
import os
from openai import OpenAI

# ==========================================
# 1. API 配置 (用于唤醒 AI 讲题功能)
# ==========================================
GITHUB_TOKEN =st.secrets["GITHUB_TOKEN"]

@st.cache_resource
def get_client():
    if GITHUB_TOKEN and "填在这里" not in GITHUB_TOKEN:
        return OpenAI(base_url="https://models.inference.ai.azure.com", api_key=GITHUB_TOKEN)
    return None

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
# 3. 构建网页界面
# ==========================================
st.set_page_config(page_title="法语智能刷题器", page_icon="🇫🇷", layout="centered")
st.title("🇫🇷 法语终极智能白板")
st.caption("基于完整离线题库，支持秒速对答案与 AI 名师讲解")

pages = load_data()
if not pages:
    st.error("找不到 book_complete.json 文件，请确保它和 app.py 在同一个文件夹！")
    st.stop()

# --- 侧边栏导航 ---
st.sidebar.header("📖 题库导航")
page_options = {f"第 {p['page']} 页 (共 {len(p['data'])} 题)": p for p in pages}
selected_option = st.sidebar.selectbox("选择今天要刷的页面", list(page_options.keys()))
selected_page_data = page_options[selected_option]

st.markdown(f"### 当前练习：{selected_option.split(' ')[0]}")
st.divider()

client = get_client()

# --- 遍历并显示当前页的所有题目 ---
for idx, q in enumerate(selected_page_data["data"]):
    block = q.get('exercise_block') or '练习'
    num = q.get('question_number') or (idx + 1)
    st.subheader(f"✏️ {block} - 题 {num}")
    
   # 题目和提示 (放大字体升级版)
    st.markdown(
        f"<div style='font-size: 36px; line-height: 1.6; margin-bottom: 10px;'>"
        f"<b>题目：</b> <code>{q['question_text']}</code>"
        f"</div>", 
        unsafe_allow_html=True
    )
    if q.get('hints'):
        # 顺便把提示词也稍微放大一点
        st.markdown(
            f"<div style='font-size: 18px; color: #026873; background-color: #E0F7FA; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>"
            f"💡 <b>提示词:</b> {q['hints']}"
            f"</div>", 
            unsafe_allow_html=True
        )
        
    # 接收用户输入
    user_answer = st.text_input("📝 你的答案：", key=f"input_{selected_page_data['page']}_{idx}")
    standard_answer = q.get('answer', '')
    
    # 将按钮并排放在一起
    col1, col2 = st.columns([1, 1])
    with col1:
        check_btn = st.button("✅ 对答案", key=f"check_{selected_page_data['page']}_{idx}")
    with col2:
        explain_btn = st.button("🧠 请 AI 老师讲解", key=f"explain_{selected_page_data['page']}_{idx}")
        
    # --- 逻辑 1：秒速对答案 (本地判断) ---
    if check_btn:
        if not user_answer.strip():
            st.warning("你还没写答案呢！")
        else:
            if not standard_answer:
                st.warning("⚠️ 这道题在书末答案库里没有找到，请自行判断或点击 AI 讲解。")
            # 忽略大小写和前后空格进行比对
            elif user_answer.strip().lower() == standard_answer.strip().lower():
                st.success(f"🎉 完全正确！标准答案就是：**{standard_answer}**")
            else:
                st.error(f"❌ 答错了。你的答案：`{user_answer}` | 标准答案：**`{standard_answer}`**")
                
    # --- 逻辑 2：召唤 AI 老师讲题 ---
    if explain_btn:
        if not client:
            st.warning("请在代码开头填入你的 GITHUB_TOKEN 才能唤醒 AI 老师哦！")
        else:
            with st.spinner("AI 老师正在备课中..."):
                prompt = f"""
                这是一道法语语法题：
                原题: "{q['question_text']}"
                提示词: "{q.get('hints', '无')}"
                标准答案: "{standard_answer}"
                学生的答案: "{user_answer}"
                
                请你扮演一名幽默专业的法语老师：
                1. 解释为什么标准答案是 "{standard_answer}"（涉及什么具体的法语语法、时态或变位规则）。
                2. 如果学生写了答案且答错了，温柔地指出他为什么错。
                """
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    st.markdown(f"**👨‍🏫 AI 老师的解析：**\n\n{response.choices[0].message.content}")
                except Exception as e:
                    st.error(f"召唤 AI 老师失败: {e}")
                    

    st.divider() # 题目之间的分割线
