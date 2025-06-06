# -----------------------------------------------------------------
# ライブラリのインポート
# -----------------------------------------------------------------
import streamlit as st
import google.generativeai as genai
import re
import os
import json
from datetime import datetime

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
# プロンプトの定義（改善点：MermaidとLaTeXの使用を指示）
# -----------------------------------------------------------------
PROMPTS = {
    "総合家庭教師": """
あなたは、生徒の知的好奇心を引き出すのが得意な、非常に優秀な家庭教師です。
生徒からの質問に対して、必ず以下の形式で回答してください。
説明が複雑なプロセスを含む場合は、```mermaid```ブロックを使ってフローチャートやシーケンス図を積極的に使用してください。
数式を記述する場合は、必ず`$$ 数式 $$`の形式でLaTeX記法を使用してください。

---
### 基本的な回答
ここに、質問に対する答えを中学生にも分かるように簡潔に説明してください。

### 深掘りのための問いかけ
生徒が次の一歩を踏み出したくなるように、魅力的な問いかけを3つ提案してください。必ず「〜について、もっと知りたい？」や「〜って、気にならない？」といった、生徒に語りかける口調で記述してください。

### 関連キーワード
- キーワード1
- キーワード2
- キーワード3
---
""",
    "科学者": """
あなたは、複雑な科学の概念を簡単な言葉で説明するのが得意な科学者です。
生徒からの質問に対して、必ず以下の形式で、身近な例えを交えながら回答してください。
科学的なプロセスや関係性を説明する場合は、```mermaid```ブロックを使って図解することを推奨します。
物理法則や化学反応式を示す場合は、必ず`$$ 数式 $$`の形式でLaTeX記法を使用してください。

---
### ズバリ！要点はこれ
ここに、科学的な質問に対する核心を、比喩や身近な例を使って一言で説明してください。

### 実験してみよう！
知的好奇心を刺激するような、驚きのある問いかけを3つ提案してください。必ず「〜って不思議だと思わない？」や「〜を確かめてみたくない？」といった口調で記述してください。

### 科学の専門用語
- 専門用語A
- 専門用語B
- 専門用語C
---
""",
    # （歴史探求家も同様に、必要であれば修正してください）
    "歴史探求家": """
あなたは、歴史上の出来事の背景や人物像を生き生きと語るのが得意な歴史探求家です。
生徒からの質問に対して、必ず以下の形式で、物語を語るように情熱的に回答してください。
出来事の因果関係など、複雑な場合は```mermaid```ブロックを使って図解しても構いません。

---
### 物語の幕開け
ここに、質問された歴史的出来事や人物についての基本的な情報を、魅力的な導入で語ってください。

### 歴史の分岐点（What if?）
歴史の「もしも」を想像してみたくなるような、ワクワクする問いかけを3つ提案してください。必ず「〜と思わない？」や「〜と考えてみない？」といった口調で記述してください。

### 主要な登場人物
- 登場人物A
- 登場人物B
- 登場人物C
---
"""
}

# (これ以降の関数定義やサイドバーのコードは、前回から変更ありません)
# (念のため、コード全体を下に記載します)

# -----------------------------------------------------------------
# 関数定義
# -----------------------------------------------------------------
def handle_new_question(question):
    mode = st.session_state.get("selected_mode", "総合家庭教師")
    prompt = PROMPTS[mode]
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        response = st.session_state.chat.send_message(question)
        st.session_state.messages.append({"role": "model", "content": response.text})
    except Exception as e:
        st.error(f"AIとの通信中にエラーが発生しました: {e}")

def set_question_from_button(question):
    st.session_state.clicked_question = question

def delete_history(filename):
    filepath = os.path.join("history", filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    st.toast(f"履歴「{filename}」を削除しました。")
    if st.session_state.get("chat_session_id") == filename:
        del st.session_state.chat_session_id

# -----------------------------------------------------------------
# セッション状態の初期化
# -----------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
# モードが変更された場合やチャットが未作成の場合にモデルとチャットを再初期化
if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = "総合家庭教師"
if "chat" not in st.session_state or st.session_state.get("current_chat_mode") != st.session_state.selected_mode:
    st.session_state.current_chat_mode = st.session_state.selected_mode
    system_prompt = PROMPTS[st.session_state.selected_mode]
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
    st.session_state.chat = model.start_chat(history=[msg for msg in st.session_state.get("messages", [])])

# -----------------------------------------------------------------
# サイドバー
# -----------------------------------------------------------------
with st.sidebar:
    st.title("オプション")
    
    selected_mode = st.selectbox("AI先生の役割を選んでください", list(PROMPTS.keys()), key="selected_mode")
    
    if st.button("新しい会話を始める"):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    st.title("会話履歴")
    history_files = sorted([f for f in os.listdir("history") if f.endswith(".json")], reverse=True)

    if not history_files:
        st.write("保存された会話はありません。")
    
    for filename in history_files:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(filename, key=f"load_{filename}", use_container_width=True):
                with open(os.path.join("history", filename), "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                st.session_state.clear()
                st.session_state.messages = chat_data["messages"]
                st.session_state.chat_session_id = filename
                st.session_state.selected_mode = chat_data.get("mode", "総合家庭教師")
                st.rerun()
        with col2:
            st.button("🗑️", key=f"delete_{filename}", on_click=delete_history, args=(filename,), use_container_width=True, help="この履歴を削除")

# -----------------------------------------------------------------
# メイン画面
# -----------------------------------------------------------------
st.title("深掘り支援AI")
st.info(f"現在のモード: **{st.session_state.selected_mode}**")

question = st.session_state.pop("clicked_question", None) or st.chat_input("AI先生に質問してみよう")

if question:
    handle_new_question(question)
    st.rerun()

# --- メインの表示ロジック（改善点：MermaidとLaTeXに対応） ---
for i, message in enumerate(st.session_state.messages):
    role = "あなた" if message["role"] == "user" else "AI先生"
    with st.chat_message(role):
        if message["role"] == "model":
            text = message["content"]
            
            # Mermaid図、LaTeX数式、テキストを分割して表示
            parts = re.split(r'(```mermaid\n.*?\n```|\$\$.*?\$\$)', text, flags=re.DOTALL)
            
            for part in parts:
                if part.strip().startswith('```mermaid'):
                    # Mermaid部分
                    mermaid_code = part.strip().lstrip('```mermaid').rstrip('```')
                    st.markdown(f"```{mermaid_code}```") # StreamlitのMarkdownはMermaidを直接レンダリング
                elif part.strip().startswith('$$'):
                    # LaTeX部分
                    latex_code = part.strip().strip('$$')
                    st.latex(latex_code)
                else:
                    # 通常のテキスト部分とボタン表示
                    sub_parts = re.split(r'(### (?:.*?)\n(?:.|\n)*?(?=\n###|\Z))', part)
                    for sub_part in sub_parts:
                        if not sub_part.strip():
                            continue
                        if sub_part.strip().startswith("###"):
                            title_match = re.search(r'### (.*?)\n', sub_part)
                            title = title_match.group(1).strip() if title_match else ""
                            content = sub_part[len(title)+5:].strip()

                            st.markdown(f"#### {title}")
                            if "深掘り" in title or "分岐点" in title or "実験" in title:
                                questions = [q.strip() for q in content.split('\n') if q.strip()]
                                for q_text in questions:
                                    question_to_ask = re.sub(r'^\d+\.\s*', '', q_text)
                                    st.button(question_to_ask, key=f"btn_{i}_{q_text}", on_click=set_question_from_button, args=(question_to_ask,))
                            else:
                                st.markdown(content)
                        else:
                            st.markdown(sub_part)
        else:
            st.markdown(message["content"])

# 会話保存機能（変更なし）
if st.session_state.messages:
    if st.button("現在の会話を保存する", key="show_save_dialog_btn"):
        st.session_state.show_save_dialog = True
    
    if st.session_state.get("show_save_dialog"):
        with st.form("save_form"):
            if "suggested_filename" not in st.session_state:
                with st.spinner("AIがファイル名を考えています..."):
                    summary_prompt = "この会話のトピックを要約し、ファイル名として最適な日本語のタイトルを10文字以内で提案してください。タイトルのみを返答してください。"
                    summary_response = st.session_state.chat.send_message(summary_prompt)
                    st.session_state.suggested_filename = re.sub(r'[\\/*?:"<>|]', "", summary_response.text.strip())
            
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