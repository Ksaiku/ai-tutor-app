# -----------------------------------------------------------------
# ライブラリのインポート
# -----------------------------------------------------------------
import streamlit as st
import google.generativeai as genai
import re
import os
import json
from datetime import datetime
from urllib.parse import quote

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
PROMPTS = {
    "総合家庭教師": """
あなたは、生徒の知的好奇心を引き出すのが得意な、非常に優秀な家庭教師です。
生徒からの質問に対して、必ず以下の形式で回答してください。
- プロセスの説明など図解が必要な場合は、その図をMermaid記法で記述し、必ず```mermaid```と```で囲んだコードブロックにしてください。
- 数式を記述する場合は、必ず`$$数式$$`の形式でLaTeX記法を使用してください。
- グラフを表示する場合は、必ず```json```ブロックを使い、厳密なVega-Lite仕様のJSON形式で記述してください。

---
### 基本的な回答
ここに、質問に対する答えを中学生にも分かるように簡潔に説明してください。

### 深掘りのための問いかけ
生徒が次の一歩を踏み出したくなるように、魅力的な問いかけを3つ提案してください。
例:
1. なぜ植物だけが光合成をできるのか、その秘密についてもっと知りたい？
2. もし地球に太陽の光が当たらなくなったら、生物はどうなるか、一緒に考えてみない？
3. 光合成以外にも、生物がエネルギーを作り出す面白い方法があるんだけど、聞いてみたい？

### 参考にしたページ
回答内容の根拠や、より詳しい情報がわかる信頼性の高いWebページへのリンクを、Markdown形式で最大3つまで提示してください。

### 関連キーワード
- キーワード1
- キーワード2
- キーワード3
---

""",
    "科学者": """
あなたは、複雑な科学の概念を簡単な言葉で説明するのが得意な科学者です。
生徒からの質問に対して、必ず以下の形式で回答してください。
- 科学的なプロセスや関係性を図解する場合は、その図をMermaid記法で記述し、必ず```mermaid```と```で囲んだコードブロックにしてください。
- 物理法則や化学反応式を示す場合は、必ず`$$数式$$`の形式でLaTeX記法を使用してください。
- 実験データなどをグラフで示す場合は、必ず```json```ブロックを使い、厳密なVega-Lite仕様のJSON形式で記述してください。

---
### ズバリ！要点はこれ
ここに、科学的な質問に対する核心を、比喩や身近な例を使って一言で説明してください。

### 実験してみよう！
知的好奇心を刺激するような、驚きのある問いかけを3つ提案してください。
例:
1. この原理を使えば、家にあるものでモーターが作れるんだけど、挑戦してみたくない？
2. この技術が、100年後の未来をどう変えているか、想像するだけでワクワクしない？
3. 実は、この分野でまだ誰も解けていない大きな謎があるんだけど、その謎に挑戦してみる？

### 参考にしたページ
このテーマについて、より専門的で正確な情報が得られる信頼性の高いWebページへのリンクを、Markdown形式で最大3つまで提示してください。
---
""",
    "歴史探求家": """
あなたは、歴史上の出来事の背景や人物像を生き生きと語るのが得意な歴史探求家です。
生徒からの質問に対して、必ず以下の形式で、物語を語るように情熱的に回答してください。
- 出来事の因果関係など、複雑な関係性を図解する場合は、その図をMermaid記法で記述し、必ず```mermaid```と```で囲んだコードブロックにしてください。

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
"""
}

# (これ以降の関数定義やサイドバーなどのコードは、前回から変更ありません)
# (以下、完全なコードです)

# -----------------------------------------------------------------
# 関数定義
# -----------------------------------------------------------------
def handle_new_question(question):
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

# ★★★ ここからが新しい、表示処理のための関数 ★★★
def render_model_response(text, message_index):
    # 特殊ブロック（箱入り）を先に探し出して分離する
    parts = re.split(r'(```json\n.*?\n```|```mermaid\n.*?\n```|\$\$.*?\$\$)', text, flags=re.DOTALL | re.IGNORECASE)
    
    for part in parts:
        if not part.strip(): continue
        
        part_lower = part.strip().lower()
        # 特殊ブロックの処理
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
            # 残りのテキスト部分を処理
            render_text_and_naked_mermaid(part, message_index)

def render_text_and_naked_mermaid(text, message_index):
    # テキストの中から、裸のMermaidコードを探して分離する
    parts = re.split(r'((?:graph|flowchart|sequenceDiagram|gantt|pie|timeline|mindmap)(?:.|\n)*)', text, flags=re.IGNORECASE)
    for i, part in enumerate(parts):
        if not part.strip(): continue
        # Mermaidコードの開始キーワードで始まるかチェック
        if i % 2 == 1: # re.splitでキャプチャグループにマッチした部分
            st.markdown(f"```mermaid\n{part.strip()}\n```")
        else:
            # 残ったテキストを、さらに###セクションで分割
            sub_parts = re.split(r'(### (?:.*?)\n(?:.|\n)*?(?=\n###|\Z))', part)
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
                            st.button(question_to_ask, key=f"btn_{message_index}_{q_text}", on_click=set_question_from_button, args=(question_to_ask,))
                    else:
                        st.markdown(content)
                else:
                    st.markdown(sub_part)
# ★★★ ここまでが新しい関数 ★★★

# -----------------------------------------------------------------
# セッション状態の初期化
# -----------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------------------------------
# サイドバー
# -----------------------------------------------------------------
with st.sidebar:
    st.title("オプション")
    
    current_mode_index = list(PROMPTS.keys()).index(st.session_state.get("selected_mode", "総合家庭教師"))
    selected_mode = st.selectbox("AI先生の役割を選んでください", list(PROMPTS.keys()), index=current_mode_index)
    if st.session_state.get("selected_mode") != selected_mode:
        st.session_state.selected_mode = selected_mode
        st.session_state.messages = []
        st.session_state.chat = None
        if "chat_session_id" in st.session_state:
            del st.session_state.chat_session_id
    
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
# モデルとチャットの初期化
# -----------------------------------------------------------------
if "chat" not in st.session_state or st.session_state.chat is None:
    system_prompt = PROMPTS[st.session_state.get("selected_mode", "総合家庭教師")]
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
    st.session_state.chat = model.start_chat(history=[{"role": msg["role"], "parts": [msg["content"]]} for msg in st.session_state.get("messages", [])])

# -----------------------------------------------------------------
# メイン画面
# -----------------------------------------------------------------
st.title("深掘り支援AI")
st.info(f"現在のモード: **{st.session_state.get('selected_mode', '総合家庭教師')}**")

question = st.session_state.pop("clicked_question", None) or st.chat_input("AI先生に質問してみよう")

if question:
    handle_new_question(question)
    st.rerun()

# --- メインの表示ロジック ---
for i, message in enumerate(st.session_state.messages):
    role = "あなた" if message["role"] == "user" else "AI先生"
    with st.chat_message(role):
        if message["role"] == "model":
            render_model_response(message["content"], i) # 新しい表示関数を呼び出し
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