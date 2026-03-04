import streamlit as st
import json
import os
import re
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
# 2. 初始化 Session State
# ==========================================
if 'wrong_questions' not in st.session_state:
    st.session_state.wrong_questions = []

if 'revealed_answers' not in st.session_state:
    st.session_state.revealed_answers = set()

# ==========================================
# 3. 数据加载与智能批改算法
# ==========================================
@st.cache_data
def load_data():
    file_path = "book_complete.json"
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [page for page in data if page.get("data")]

def smart_check(user_input, std_answer):
    """
    智能批改核心算法：忽略符号差异、统一撇号、大小写脱敏
    """
    if not user_input or not user_input.strip():
        return False
        
    u_ans = user_input.replace("’", "'").replace("‘", "'").replace("`", "'").lower().strip()
    s_ans = std_answer.replace("’", "'").replace("‘", "'").replace("`", "'").lower().strip()
    
    if u_ans == s_ans:
        return True
        
    separators = r'[\.\,\;，；]+'
    u_tokens = re.split(r'\s+', re.sub(separators, ' ', u_ans).strip())
    s_tokens = re.split(r'\s+', re.sub(separators, ' ', s_ans).strip())
    
    if len(s_tokens) > 0 and u_tokens == s_tokens:
        return True
        
    return False

# ==========================================
# 4. 界面初始化
# ==========================================
st.set_page_config(page_title="法语智能刷题器", page_icon="🇫🇷", layout="centered")

client = get_client()

st.sidebar.header("🎯 学习控制台")
if not client:
    st.sidebar.warning("⚠️ 待配置：请在 Secrets 中设置 SILICON_TOKEN")
else:
    st.sidebar.success("✅ AI 引擎已就绪")

# ==========================================
# 5. 【核心优化】侧边栏布局：冻结顶部 & 滚动选择
# ==========================================
pages = load_data()
if not pages:
    st.error("找不到 book_complete.json 文件！")
    st.stop()

# 提前声明变量
display_questions = []
current_page_name = ""

# 定义固定在顶部的控制面板
top_control_panel = st.sidebar.container()

# 定义可在内部滚动的页面选择面板（通过设定 height 实现固定窗口滚动）
st.sidebar.markdown("<p style='font-size:14px; color:gray; margin-bottom:0px;'>⬇️ 拖动下方区域选择页面</p>", unsafe_allow_html=True)
page_selector_panel = st.sidebar.container(height=350) 

# --- A. 先在滚动区渲染页面选择（为后续判断做准备） ---
with page_selector_panel:
    mode = st.radio("选择模式", ["📖 全书刷题", "📕 我的错题本"])
    
    if mode == "📖 全书刷题":
        page_options = {f"第 {p['page']} 页 (共 {len(p['data'])} 题)": p for p in pages}
        # label_visibility="collapsed" 让内部更紧凑
        selected_option = st.radio("选择页面", list(page_options.keys()), label_visibility="collapsed")
        display_questions = page_options[selected_option]["data"]
        current_page_name = selected_option
        st.title(f"🇫🇷 当前练习：{selected_option.split(' ')[0]}")
    else:
        display_questions = st.session_state.wrong_questions
        current_page_name = "错题本"
        st.title("📕 我的错题本")
        if not display_questions:
            st.info("错题本是空的。点击全书刷题模式下的“⭐ 收藏”按钮来添加。")

# --- B. 再在顶部固定区渲染核心按钮（实现冻结效果） ---
with top_control_panel:
    if display_questions:
        # 1. 一键批改模块（加粗标红的按钮，type="primary"）
        if st.button("📝 一键批改当前页", use_container_width=True, type="primary"):
            correct_count = 0
            total = len(display_questions)
            
            for idx, q in enumerate(display_questions):
                block = q.get('exercise_block') or '练习'
                num = q.get('question_number') or (idx + 1)
                q_id = f"{mode}_{current_page_name}_{block}_{num}"
                
                user_val = st.session_state.get(f"input_{q_id}", "")
                std_val = q.get('answer', "")
                
                if smart_check(user_val, std_val):
                    correct_count += 1
            
            score = int((correct_count / total) * 100) if total > 0 else 0
            
            # 成绩指示器
            st.metric("📊 页面得分", f"{score}%", f"答对 {correct_count}/{total} 题")
            
            if score == 100:
                st.success("🏆 太棒了！全部正确！")
                st.balloons()
            elif score > 0:
                st.info(f"继续加油！已纠正 {correct_count} 道题。")

    # 2. 存档管理模块
    with st.expander("💾 存档管理"):
        if st.session_state.wrong_questions:
            wrong_json = json.dumps(st.session_state.wrong_questions, ensure_ascii=False, indent=4)
            st.download_button(
                label="📥 下载错题本存档",
                data=wrong_json,
                file_name=f"french_wrong_{datetime.now().strftime('%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        uploaded_file = st.file_uploader("📤 上传历史存档", type="json")
        if uploaded_file is not None:
            try:
                st.session_state.wrong_questions = json.load(uploaded_file)
                st.success("存档已加载！")
            except:
                st.error("文件格式不对哦")
                
    # 3. 错题本模式专属：一键清空
    if mode == "📕 我的错题本" and st.button("🗑️ 清空所有收藏", use_container_width=True):
        st.session_state.wrong_questions = []
        st.rerun()

    st.divider()


# ==========================================
# 6. 核心题目渲染逻辑 (保持不动)
# ==========================================
for idx, q in enumerate(display_questions):
    block = q.get('exercise_block') or '练习'
    num = q.get('question_number') or (idx + 1)
    
    q_id = f"{mode}_{current_page_name}_{block}_{num}"
    
    st.markdown(f"<div style='font-size: 20px; color: #666; font-weight: bold;'>{block} - 第 {num} 题</div>", unsafe_allow_html=True)
    
    safe_question_text = q.get('question_text', '⚠️ [缺失题目内容]')
    st.markdown(                                                        
        f"<div style='font-size: 28px; font-weight: 500; background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 15px;'>"  
        f"{safe_question_text}"                                         
        f"</div>",                                                      
        unsafe_allow_html=True                                          
    )

    if q.get('hints'):
        st.markdown(f"<div style='font-size: 18px; color: #007B83; margin-bottom: 10px;'>💡 提示: {q['hints']}</div>", unsafe_allow_html=True)
        
    standard_answer = q.get('answer', '')

    is_revealed = q_id in st.session_state.revealed_answers
    show_ans = st.checkbox("👀 显示答案 (背诵模式)", value=is_revealed, key=f"chkbox_{q_id}")
    
    if show_ans:
        st.session_state.revealed_answers.add(q_id)
        st.markdown(
            f"<div style='font-size: 24px; color: #e74c3c; font-weight: bold; padding: 10px; border-left: 5px solid #e74c3c; background-color: #fdf2f0; margin-bottom: 10px;'>"
            f"标准答案：{standard_answer}"
            f"</div>", 
            unsafe_allow_html=True
        )
    else:
        st.session_state.revealed_answers.discard(q_id)

    user_answer = st.text_input("📝 默写区：", key=f"input_{q_id}", placeholder="在这里输入你的答案...")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("✅ 批改作答", key=f"btn_chk_{q_id}"):
            if not user_answer.strip():
                st.warning("你还没写答案哦。")
            elif smart_check(user_answer, standard_answer):
                st.success("🎉 正确！")
            else:
                st.error("❌ 不对哦，再想想？")
                
    with col2:
        if st.button("🧠 AI 讲解", key=f"btn_ai_{q_id}"):
            if not client:
                st.warning("请先配置 API。")
            else:
                with st.spinner("AI 老师正在批阅..."):
                    prompt = f"法语语法题: {q['question_text']}\n提示: {q.get('hints','无')}\n标准答案: {standard_answer}\n学生回答: {user_answer}\n请针对学生回答进行幽默且专业的讲解。"
                    try:
                        response = client.chat.completions.create(
                            model="Qwen/Qwen2.5-7B-Instruct",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.4
                        )
                        st.info(f"👨‍🏫 AI 老师：\n\n{response.choices[0].message.content}")
                    except Exception as e:
                        st.error(f"连接失败: {e}")

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