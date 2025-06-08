# -----------------------------------------------------------------
# ライブラリのインポート
# -----------------------------------------------------------------
import streamlit as st
import google.generativeai as genai
import re
import os
import json
from datetime import datetime
import trafilatura

# -----------------------------------------------------------------
# 初期設定
# -----------------------------------------------------------------
st.set_page_config(layout="wide", page_title="深掘り支援AI")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except (KeyError, AttributeError):
    st.error("APIキーが設定されていません。.streamlit/secrets.tomlにGEMINI_API_KEYを設定してください。")
    st.stop()

if not os.path.exists("history"):
    os.makedirs("history")

# -----------------------------------------------------------------
# プロンプトの定義
# -----------------------------------------------------------------
PROMPT_TEMPLATES = {
    "総合家庭教師": """
あなたは、生徒の知的好奇心を引き出すのが得意な、非常に優秀な家庭教師です。

【最重要】
生徒は以下の『参考文章』を読んでいます。あなたの回答は、必ずこの文章の内容に基づいてください。
『参考文章』：
---
{document_context}
---

生徒からの質問に対して、必ず以下の形式で回答してください。
回答のレベルは、対象となる {target_age} が理解できるように調整してください。
- プロセスの説明など図解が必要な場合は、その図をMermaid記法で記述し、必ず```mermaid```と```で囲んだコードブロックにしてください。
- 数式を記述する場合は、必ず`$$数式$$`の形式でLaTeX記法を使用してください。
- グラフを表示する場合は、必ず```json```ブロックを使い、厳密なVega-Lite仕様のJSON形式で記述してください。

【重要】
この生徒は、以下のトピックについては既に基本的な知識があります。
既知のトピックリスト: [{known_keywords}]
これらのトピックの基本的な説明は省略し、今回の質問との関連性や、より発展的な内容を中心に回答してください。もしリストが空の場合は、基本的な内容から説明してください。

---
### 基本的な回答
ここに、質問に対する答えを、{target_age} にも分かるように簡潔に説明してください。

### 深掘りのための問いかけ
{target_age} が次の一歩を踏み出したくなるように、魅力的な問いかけを3つ提案してください。
問いかけは、{target_age} の生徒の好奇心を刺激するような内容にしてください。

### 参考サイト
回答内容より詳しい情報がわかる信頼性の高いWebページへのリンクを、Markdown形式で最大5つまで提示し、簡単にそのサイトの説明をしてください。

### 関連キーワード
質生徒が興味を惹きそうな質問と回答に関連するキーワードを提示してください。明らかに生徒が知っていそうなキーワードは省略してください。
- キーワード1
- キーワード2
- キーワード3
---

""",
    "科学者": """
あなたは、複雑な科学の概念を簡単な言葉で説明するのが得意な科学者です。

【最重要】
生徒は以下の『参考文章』を読んでいます。あなたの回答は、必ずこの文章の内容に基づいてください。
『参考文章』：
---
{document_context}
---

生徒からの質問に対して、必ず以下の形式で回答してください。
回答のレベルは、対象となる {target_age} が理解できるように調整してください。
- 科学的なプロセスや関係性を図解する場合は、その図をMermaid記法で記述し、必ず```mermaid```と```で囲んだコードブロックにしてください。
- 物理法則や化学反応式を示す場合は、必ず`$$数式$$`の形式でLaTeX記法を使用してください。

【重要】
この生徒は、以下のトピックについては既に基本的な知識があります。
既知のトピックリスト: [{known_keywords}]
これらのトピックの基本的な説明は省略し、今回の質問との関連性や、より発展的な内容を中心に回答してください。もしリストが空の場合は、基本的な内容から説明してください。

---
### ズバリ！要点はこれ
ここに、科学的な質問に対する核心を、比喩や身近な例を使って、{target_age} にも分かるように説明してください。

### 実験してみよう！
{target_age} の知的好奇心を刺激するような、驚きのある問いかけを3つ提案してください。

### 参考にしたページ
このテーマについて、より専門的で正確な情報が得られる信頼性の高いWebページへのリンクを、Markdown形式で最大3つまで提示してください。
---

### 関連する専門用語
回答内容に関連する専門用語や、より深く知るためのキーワードを3つ提示してください。

""",
    "歴史探求家": """
あなたは、歴史上の出来事の背景や人物像を生き生きと語るのが得意な歴史探求家です。

【最重要】
生徒は以下の『参考文章』を読んでいます。あなたの回答は、必ずこの文章の内容に基づいてください。
『参考文章』：
---
{document_context}
---

生徒からの質問に対して、必ず以下の形式で、物語を語るように情熱的に回答してください。
- 出来事の因果関係など、複雑な関係性を図解する場合は、その図をMermaid記法で記述し、必ず```mermaid```と```で囲んだコードブロックにしてください。

【重要】
この生徒は、以下のトピックについては既に基本的な知識があります。
既知のトピックリスト: [{known_keywords}]
これらのトピックの基本的な説明は省略し、今回の質問との関連性や、より発展的な内容を中心に回答してください。もしリストが空の場合は、基本的な内容から説明してください。


---
### 物語の幕開け
ここに、質問された歴史的出来事や人物についての基本的な情報を、魅力的な導入で語ってください。

### 歴史の分岐点（What if?）
歴史の「もしも」を想像してみたくなるような、ワクワクする問いかけを3つ提案してください。
1. もし、あの時信長が本能寺から逃げていたら、日本の歴史はどうなっていたと思う？
2. この出来事の裏で、教科書には載っていないどんな駆け引きがあったのか、想像してみない？
3. この歴史から、現代の私たちが学べることは何だと思う？一緒に考えてみないかい？

### 参考にしたページ
回答の元になった、あるいは関連する資料や論文、博物館の解説ページなど、信頼できる情報源へのリンクをMarkdown形式で最大3つまで提示してください。
---

### 関連キーワード
- キーワード1
- キーワード2
- キーワード3

"""
}

# -----------------------------------------------------------------
# 関数定義
# -----------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_website_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        else:
            st.error("URLからコンテンツをダウンロードできませんでした。")
            return None
    except Exception as e:
        st.error(f"URLの処理中にエラーが発生しました: {e}")
        return None

def add_to_known_keywords(keyword):
    if "known_keywords" not in st.session_state: st.session_state.known_keywords = []
    clean_keyword = keyword.strip()
    if clean_keyword and clean_keyword not in st.session_state.known_keywords:
        st.session_state.known_keywords.append(clean_keyword)

def handle_new_question(question):
    add_to_known_keywords(question.replace("について、もっと詳しく教えてください。", "").replace("について教えて", "").strip())
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        response = st.session_state.chat.send_message(question)
        st.session_state.messages.append({"role": "model", "content": response.text})
    except Exception as e:
        st.error(f"AIとの通信中にエラーが発生しました: {e}")

def set_question_from_button(question, keyword):
    st.session_state.clicked_question = question
    add_to_known_keywords(keyword)

def delete_history(filename):
    filepath = os.path.join("history", filename)
    if os.path.exists(filepath): os.remove(filepath)
    st.toast(f"履歴「{filename}」を削除しました。")
    if st.session_state.get("chat_session_id") == filename: del st.session_state.chat_session_id

def render_text_and_buttons(text, message_index):
    sub_parts = re.split(r'(### (?:.*?)\n(?:.|\n)*?(?=\n###|\Z))', text)
    for sub_part in sub_parts:
        if not sub_part.strip(): continue
        if sub_part.strip().startswith("###"):
            title_match = re.search(r'### (.*?)\n', sub_part)
            title = title_match.group(1).strip() if title_match else ""
            content = sub_part[len(title)+5:].strip()
            st.markdown(f"#### {title}")

            if "深掘り" in title or "分岐点" in title or "実験" in title:
                questions = [q.strip() for q in content.split('\n') if q.strip()]
                for q_text in questions:
                    question_to_ask = re.sub(r'^\d+\.\s*', '', q_text)
                    st.button(question_to_ask, key=f"btn_{message_index}_{q_text}", on_click=set_question_from_button, args=(question_to_ask, question_to_ask))
            
            elif "キーワード" in title or "登場人物" in title or "専門用語" in title:
                keywords = [kw.strip().lstrip('*- ').strip() for kw in content.split('\n') if kw.strip()]
                for keyword in keywords:
                    if not keyword: continue
                    question_to_ask = f"{keyword}について、もっと詳しく教えてください。"
                    st.button(keyword, key=f"kw_btn_{message_index}_{keyword}", on_click=set_question_from_button, args=(question_to_ask, keyword))
            else:
                st.markdown(content)
        else:
            st.markdown(sub_part)

def render_model_response(text, message_index):
    parts = re.split(r'(```json\n.*?\n```|```mermaid\n.*?\n```|\$\$.*?\$\$)', text, flags=re.DOTALL | re.IGNORECASE)
    for part in parts:
        if not part.strip(): continue
        part_lower = part.strip().lower()
        if part_lower.startswith('```json'):
            json_code = part.strip().lstrip('```json').rstrip('```')
            try:
                json_code = re.sub(r',\s*([}\]])', r'\1', json_code)
                spec = json.loads(json_code)
                st.vega_lite_chart(spec)
            except json.JSONDecodeError:
                st.error("グラフのデータ形式が正しくないため、グラフを表示できませんでした。")
                st.code(json_code, language="json")
        elif part_lower.startswith('```mermaid'):
            mermaid_code = part.strip()[len("```mermaid"):].rstrip('```').strip()
            st.markdown(f"```mermaid\n{mermaid_code}\n```")
        elif part_lower.startswith('$$'):
            latex_code = part.strip().strip('$$')
            st.latex(latex_code)
        else:
            render_text_and_buttons(part, message_index)



# -----------------------------------------------------------------
# セッション状態の初期化
# -----------------------------------------------------------------
if "messages" not in st.session_state: st.session_state.messages = []
if "selected_mode" not in st.session_state: st.session_state.selected_mode = "総合家庭教師"
if "target_age" not in st.session_state: st.session_state.target_age = "中学生"
if "known_keywords" not in st.session_state: st.session_state.known_keywords = []
if "document_context" not in st.session_state: st.session_state.document_context = ""

# -----------------------------------------------------------------
# サイドバー
# -----------------------------------------------------------------
with st.sidebar:
    if st.button("新しい会話を始める", use_container_width=True):
        keys_to_clear = ["messages", "chat", "chat_session_id", "document_context"]
        for key in keys_to_clear:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
    st.markdown("---")
    st.subheader("設定")
    current_mode = st.session_state.selected_mode
    selected_mode = st.selectbox("AI先生の役割", list(PROMPT_TEMPLATES.keys()), index=list(PROMPT_TEMPLATES.keys()).index(current_mode))
    age_options = ["小学生（低学年）", "小学生（高学年）", "中学生", "高校生", "社会人・専門家"]
    current_age = st.session_state.target_age
    selected_age = st.selectbox("対象年齢", age_options, index=age_options.index(current_age))

    if selected_mode != current_mode or selected_age != current_age:
        st.session_state.selected_mode = selected_mode
        st.session_state.target_age = selected_age
        st.session_state.messages = []
        st.session_state.chat = None
        if "chat_session_id" in st.session_state: del st.session_state.chat_session_id
        st.rerun()

    # モードまたは年齢が変更されたら、会話のみをリセット
    if st.session_state.get("selected_mode") != selected_mode or st.session_state.get("target_age") != selected_age:
        st.session_state.selected_mode = selected_mode
        st.session_state.target_age = selected_age
        # 知識ノートはリセットしない
        st.session_state.messages = []
        st.session_state.chat = None
        if "chat_session_id" in st.session_state: del st.session_state.chat_session_id
        st.rerun()

    st.markdown("---")
    st.subheader("会話履歴")
    history_files = sorted([f for f in os.listdir("history") if f.endswith(".json")], reverse=True)

    if not history_files:
        st.write("保存された会話はありません。")
    
    for filename in history_files:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(filename, key=f"load_{filename}", use_container_width=True):
                with open(os.path.join("history", filename), "r", encoding="utf-8") as f: chat_data = json.load(f)
                # 知識ノートも一緒に読み込む
                st.session_state.clear()
                st.session_state.messages = chat_data.get("messages", [])
                st.session_state.known_keywords = chat_data.get("known_keywords", [])
                st.session_state.chat_session_id = filename
                st.session_state.selected_mode = chat_data.get("mode", "総合家庭教師")
                st.rerun()
        with col2: st.button("🗑️", key=f"delete_{filename}", on_click=delete_history, args=(filename,), use_container_width=True, help="この履歴を削除")
    
    st.markdown("---")
    st.subheader("知識ノート")
    if st.session_state.known_keywords:
        st.write(st.session_state.known_keywords)
    else:
        st.write("まだありません。")
# -----------------------------------------------------------------
# メイン画面 - ヘッダーとURL入力
# -----------------------------------------------------------------
st.title("深掘り支援AI - 資料と対話する学習室")
url = st.text_input("学習したいWebサイトのURLを入力してください", "")
if st.button("URLを読み込む"):
    if url:
        with st.spinner("Webサイトを読み込んでいます..."):
            content = get_website_text(url)
            if content:
                st.session_state.document_context = content
                st.session_state.messages = [] 
                st.session_state.chat = None
                st.success("読み込みが完了しました。")
    else:
        st.warning("URLを入力してください。")

st.markdown("---")
col1, col2 = st.columns([2, 1])

# --- 左側：資料表示エリア ---
with col1:
    st.subheader("読み込んだ資料")
    if st.session_state.document_context:
        with st.container(height=800):
            st.markdown(st.session_state.document_context)
    else:
        st.info("ここに、読み込んだWebサイトの内容が表示されます。")

# --- 右側：チャットエリア ---
with col2:
    st.subheader(f"AI先生との対話")
    st.info(f"モード: {st.session_state.selected_mode} | 対象: {st.session_state.target_age}")

    if "chat" not in st.session_state or st.session_state.chat is None:
        prompt_template = PROMPT_TEMPLATES[st.session_state.selected_mode]
        known_keywords_str = ", ".join(st.session_state.known_keywords) if st.session_state.known_keywords else "なし"
        document_context_str = st.session_state.document_context if st.session_state.document_context else "今回はありません"
        
        system_prompt = prompt_template.format(
            target_age=st.session_state.target_age,
            known_keywords=known_keywords_str,
            document_context=document_context_str
        )
        
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
        st.session_state.chat = model.start_chat(history=[])

    question = st.session_state.pop("clicked_question", None) or st.chat_input("資料について質問してみよう")
    if question:
        handle_new_question(question)
        st.rerun()

    with st.container(height=700):
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "model":
                    # ★★★ ここで、以前の多機能な表示関数を呼び出します ★★★
                    render_model_response(message["content"], i)
                else:
                    st.markdown(message["content"])


# --- 会話保存機能 ---
    if st.session_state.messages:
        if st.button("現在の会話を保存する", key="show_save_dialog_btn"):
            st.session_state.show_save_dialog = True
        
        if st.session_state.get("show_save_dialog"):
            with st.form("save_form"):
                if "suggested_filename" not in st.session_state:
                    with st.spinner("AIがファイル名を考えています..."):
                        summary_prompt = "この会話のトピックを要約し、ファイル名として最適な日本語のタイトルを10文字以内で提案してください。タイトルのみを返答してください。"
                        try:
                            summary_response = st.session_state.chat.send_message(summary_prompt)
                            st.session_state.suggested_filename = re.sub(r'[\\/*?:"<>|]', "", summary_response.text.strip())
                        except Exception:
                            st.session_state.suggested_filename = "会話の要約"
                
                filename_to_save = st.text_input("ファイル名", value=st.session_state.suggested_filename)
                submitted = st.form_submit_button("確定して保存")

                if submitted:
                    filepath = os.path.join("history", f"{filename_to_save}.json")
                    data_to_save = { "mode": st.session_state.selected_mode, "messages": st.session_state.messages }
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"会話を保存しました: {filename_to_save}.json")
                    st.toast("✅ 保存完了！")
                    
                    del st.session_state.show_save_dialog
                    if "suggested_filename" in st.session_state:
                        del st.session_state.suggested_filename
                    st.rerun()