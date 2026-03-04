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
    智能批改核心算法：
    1. 统一法语撇号
    2. 忽略大小写
    3. 智能拆分多空答案 (兼容 '...', ',', ' ', '，' 等分隔符)
    """
    if not user_input or not user_input.strip():
        return False
        
    # 统一撇号格式 (中文单引号、英文单引号、特殊符号全转为标准英文单引号)
    u_ans = user_input.replace("’", "'").replace("‘", "'").replace("`", "'").lower().strip()
    s_ans = std_answer.replace("’", "'").replace("‘", "'").replace("`", "'").lower().strip()
    
    # 1. 如果完全相等，直接返回 True
    if u_ans == s_ans:
        return True
        
    # 2. 拆分逻辑：针对 "irez... seront" 这类多空题
    # 将多个点、逗号、分号等全部替换为空格，然后按空格分割成词组列表
    separators = r'[\.\,\;，；]+'
    u_tokens = re.split(r'\s+', re.sub(separators, ' ', u_ans).strip())
    s_tokens = re.split(r'\s+', re.sub(separators, ' ', s_ans).strip())
    
    # 如果分割后的有效词组完全一一对应，则判定正确
    # 例如：标准="irez... seront"，用户输入="irez seront" 或 "irez, seront"
    if len(s_tokens) > 0 and u_tokens == s_tokens:
        return True
        
    return False

# ==========================================
# 4. 界面与侧边栏
# ==========================================
st.set_page_config(page_title="法语智能刷题器", page_icon="🇫🇷", layout="centered")

client = get_client()

st.sidebar.header("🎯 学习控制台")
if not client:
    st.sidebar.warning("⚠️ 待配置：请在 Secrets 中设置 SILICON_TOKEN")
else:
    st.sidebar.success("✅ AI 引擎已就绪")

mode = st.sidebar.radio("选择模式", ["📖 全书刷题", "📕 我的错题本"])

# 加载数据
pages = load_data()
if not pages:
    st.error("找不到 book_complete.json 文件！")
    st.stop()

# 确定当前显示的题目列表
display_questions = []
current_page_name = ""

if mode == "📖 全书刷题":
    page_options = {f"第 {p['page']} 页 (共 {len(p['data'])} 题)": p for p in pages}
    selected_option = st.sidebar.radio("选择页面", list(page_options.keys()))
    display_questions = page_options[selected_option]["data"]
    current_page_name = selected_option
    st.title(f"🇫🇷 当前练习：{selected_option.split(' ')[0]}")
else:
    st.title("📕 我的错题本")
    display_questions = st.session_state.wrong_questions
    current_page_name = "错题本"
    if not display_questions:
        st.info("错题本是空的。点击全书刷题模式下的“⭐ 收藏”按钮来添加。")

st.divider()

# ==========================================
# 5. 一键批改逻辑 (应用智能算法)
# ==========================================
if display_questions:
    if st.sidebar.button("📝 一键批改当前页", use_container_width=True):
        correct_count = 0
        total = len(display_questions)
        
        for idx, q in enumerate(display_questions):
            block = q.get('exercise_block') or '练习'
            num = q.get('question_number') or (idx + 1)
            q_id = f"{mode}_{current_page_name}_{block}_{num}"
            
            user_val = st.session_state.get(f"input_{q_id}", "")
            std_val = q.get('answer', "")
            
            # 使用智能批改函数
            if smart_check(user_val, std_val):
                correct_count += 1
        
        # 显示结果
        score = int((correct_count / total) * 100) if total > 0 else 0
        st.sidebar.metric("当前页得分", f"{score}%", f"{correct_count}/{total} 正确")
        
        if score == 100:
            st.sidebar.success("🏆 太棒了！全部正确！")
            st.balloons()
        elif score > 0:
            st.sidebar.info(f"继续加油！已纠正 {correct_count} 道题。")

# 侧边栏辅助功能
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

if mode == "📕 我的错题本" and st.sidebar.button("🗑️ 清空所有收藏"):
    st.session_state.wrong_questions = []
    st.rerun()

# ==========================================
# 6. 核心题目渲染逻辑
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

    # 答案显隐控制
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

    # 作答区域
    user_answer = st.text_input("📝 默写区：", key=f"input_{q_id}", placeholder="在这里输入你的答案...")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("✅ 批改作答", key=f"btn_chk_{q_id}"):
            if not user_answer.strip():
                st.warning("你还没写答案哦。")
            elif smart_check(user_answer, standard_answer):  # <--- 应用智能算法
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