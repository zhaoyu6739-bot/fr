import streamlit as st
import json
import os
from openai import OpenAI
from datetime import datetime

# ==========================================
# 1. API 配置
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

# ==========================================
# 2. 初始化 Session State (内存状态)
# ==========================================
if 'wrong_questions' not in st.session_state:
    st.session_state.wrong_questions = []

if 'revealed_answers' not in st.session_state:
    st.session_state.revealed_answers = set()

# ==========================================
# 3. 数据加载 (已移除缓存，实时同步 JSON 修改)
# ==========================================
def load_data():
    file_path = "book_complete.json"
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [page for page in data if page.get("data")]

# ==========================================
# 4. 构建网页界面与侧边栏
# ==========================================
st.set_page_config(page_title="法语智能刷题器", page_icon="🇫🇷", layout="centered")

client = get_client()

st.sidebar.header("🎯 学习控制台")
if not client:
    st.sidebar.warning("⚠️ 待配置：请在 Secrets 中设置 SILICON_TOKEN")
else:
    st.sidebar.success("✅ AI 引擎已就绪")

mode = st.sidebar.radio("选择模式", ["📖 全书刷题", "📕 我的错题本"])

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
    # 为当前页生成一个独有的“整页批改”状态 Key
    current_page_key = f"grade_all_{selected_option}"
else:
    st.title("📕 我的错题本")
    display_questions = st.session_state.wrong_questions
    current_page_key = "grade_all_wrong_book"
    if not display_questions:
        st.info("错题本是空的。点击全书刷题模式下的“⭐ 收藏”按钮来添加。")
    if st.sidebar.button("🗑️ 清空所有收藏"):
        st.session_state.wrong_questions = []
        st.rerun()

st.divider()

# --- 🚩 新增：整页批改控制台 ---
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    # 点击时，将当前页面的“批改全开”状态设为 True
    if st.button("💯 一键批改本页所有作答", type="primary", use_container_width=True):
        st.session_state[current_page_key] = True
with col_ctrl2:
    # 点击时，关闭批改状态，恢复干净页面
    if st.button("🔄 隐藏全页批改结果", use_container_width=True):
        st.session_state[current_page_key] = False

st.divider()

# ==========================================
# 5. 题目渲染逻辑
# ==========================================
for idx, q in enumerate(display_questions):
    block = q.get('exercise_block') or '练习'
    num = q.get('question_number') or (idx + 1)
    
    q_id = f"{mode}_page{q.get('page','0')}_{block}_{num}"
    
    # 题目区域
    st.markdown(f"<div style='font-size: 22px; color: #666; font-weight: bold;'>{block} - 第 {num} 题</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size: 30px; font-weight: 500; background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #ddd;'>"
        f"{q['question_text']}"
        f"</div>", 
        unsafe_allow_html=True
    )

    if q.get('hints'):
        st.markdown(f"<div style='font-size: 20px; color: #007B83; margin-bottom: 10px;'>💡 提示: {q['hints']}</div>", unsafe_allow_html=True)
        
    standard_answer = q.get('answer', '')

    is_revealed = q_id in st.session_state.revealed_answers
    
    show_ans = st.checkbox("👀 看答案 (背诵模式)", value=is_revealed, key=f"chkbox_{q_id}")
    
    if show_ans:
        st.session_state.revealed_answers.add(q_id)
        st.markdown(
            f"<div style='font-size: 26px; color: #e74c3c; font-weight: bold; padding: 10px; border-left: 5px solid #e74c3c; background-color: #fdf2f0; margin-bottom: 15px;'>"
            f"标准答案：{standard_answer}"
            f"</div>", 
            unsafe_allow_html=True
        )
    else:
        st.session_state.revealed_answers.discard(q_id)

    # 独立分开的默写框 (关闭浏览器自动补全)
    user_answer = st.text_input("📝 默写区（选填）：", key=f"input_{q_id}", autocomplete="off")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # 获取单一按钮的点击状态
        grade_clicked = st.button("✅ 批改作答", key=f"btn_chk_{q_id}")
        # 获取上方“一键全页批改”的状态
        is_page_graded = st.session_state.get(current_page_key, False)
        
        # --- 🚩 如果点了单一按钮，或者开启了全页批改，就展示判定结果 ---
        if grade_clicked or is_page_graded:
            if not user_answer.strip():
                st.warning(f"未作答。标准答案应为：**{standard_answer}**")
            elif user_answer.strip().lower() == standard_answer.strip().lower():
                st.success(f"🎉 默写正确！答案：**{standard_answer}**")
            else:
                st.error(f"❌ 答错了。标准答案应为：**{standard_answer}**")
                
    with col2:
        if st.button("🧠 AI 讲解", key=f"btn_ai_{q_id}"):
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
            if st.button("⭐ 收藏", key=f"btn_fav_{q_id}"):
                if q not in st.session_state.wrong_questions:
                    st.session_state.wrong_questions.append(q)
                    st.toast("已加入错题本", icon="⭐")
        else:
            if st.button("🗑️ 移除", key=f"btn_rm_{q_id}"):
                st.session_state.wrong_questions.pop(idx)
                st.rerun()
                
    st.divider()
