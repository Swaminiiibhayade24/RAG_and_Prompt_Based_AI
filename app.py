import streamlit as st
from pathlib import Path
from datetime import datetime
import uuid

from config import APP_NAME, CHAT_STORE, KNOWLEDGE_DIR, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL
from ollama_client import OllamaClient
from rag_pipeline import RAGPipeline
from document_loader import load_uploaded_document
from learning_content import TOPICS, QUIZ_QUESTIONS

st.set_page_config(page_title=APP_NAME, page_icon="✦", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {--bg:#080d1b;--panel:#101a30;--panel2:#14213b;--cyan:#55e6e0;--violet:#9b8cff;--muted:#91a0bd;}
.stApp {background:radial-gradient(ellipse at 80% 0%,#18264a 0%,#080d1b 48%);color:#eef3ff;font-family:'DM Sans',sans-serif;}
h1,h2,h3,.brand {font-family:'Space Grotesk',sans-serif!important;}
.block-container {padding-top:1.7rem;max-width:1250px;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#0d172b,#0a1121);border-right:1px solid #263653;}
[data-testid="stSidebar"] * {color:#e9f1ff;}
.brand {font-size:1.65rem;font-weight:700;letter-spacing:-1px;background:linear-gradient(90deg,#fff,#55e6e0,#9b8cff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.brand-sub {color:#91a0bd;font-size:.72rem;letter-spacing:2px;text-transform:uppercase;margin-top:-5px;}
.hero {padding:2rem 2.2rem;border:1px solid #2a3b5c;border-radius:22px;background:linear-gradient(120deg,rgba(25,43,77,.95),rgba(19,26,53,.85));box-shadow:0 18px 55px #02061166;margin-bottom:1.2rem;}
.hero h1 {font-size:2.6rem;margin:0;color:#f4f7ff;}
.hero p {color:#aab8d4;font-size:1.02rem;}
.glow {color:#55e6e0;}
.metric {padding:1rem;border-radius:16px;background:#111e35;border:1px solid #2b3d5d;}
.metric b {font-size:1.4rem;color:#55e6e0;}
.metric small {color:#91a0bd;}
.chat-user {background:#192b4b;border:1px solid #344d72;padding:14px 17px;border-radius:17px 17px 5px 17px;margin:10px 0 10px 16%;}
.chat-ai {background:linear-gradient(135deg,#111f37,#151d38);border:1px solid #304261;padding:16px 18px;border-radius:17px 17px 17px 5px;margin:10px 12% 12px 0;}
div.stButton>button {border-radius:12px;border:1px solid #3b5579;background:linear-gradient(100deg,#173b55,#29335e);color:#f5f8ff;font-weight:600;min-height:2.6rem;}
div.stButton>button:hover {border-color:#55e6e0;color:#55e6e0;}
.stTextInput input,.stTextArea textarea {background:#101b30!important;color:#f4f7ff!important;border:1px solid #314565!important;border-radius:12px!important;}
[data-testid="stChatInput"] textarea {background:#111d33!important;}
hr {border-color:#263653;}
.caption {color:#91a0bd;font-size:.83rem;}
.pill {display:inline-block;padding:5px 10px;border-radius:20px;background:#1c3650;color:#70e8e1;font-size:.75rem;margin-right:6px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

def load_chat_store():
    import json
    p = Path(CHAT_STORE)
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return {}
    return {}

def save_chat_store(data):
    import json
    Path(CHAT_STORE).parent.mkdir(parents=True, exist_ok=True)
    Path(CHAT_STORE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_chat_store()
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "page" not in st.session_state:
    st.session_state.page = "AI Chat"
if "messages" not in st.session_state:
    st.session_state.messages = []

def new_chat():
    cid = str(uuid.uuid4())[:8]
    st.session_state.chat_id = cid
    st.session_state.messages = []
    st.session_state.all_chats[cid] = {"title":"New conversation","updated":datetime.now().isoformat(),"messages":[]}
    save_chat_store(st.session_state.all_chats)

def open_chat(cid):
    st.session_state.chat_id = cid
    st.session_state.messages = st.session_state.all_chats[cid].get("messages", [])

def persist():
    if st.session_state.chat_id:
        chat = st.session_state.all_chats.setdefault(st.session_state.chat_id, {})
        chat["messages"] = st.session_state.messages
        chat["updated"] = datetime.now().isoformat()
        if st.session_state.messages and chat.get("title") == "New conversation":
            first = next((m["content"] for m in st.session_state.messages if m["role"]=="user"), "New conversation")
            chat["title"] = first[: thirty] if (thirty :=  thirty_value()) else first[:32]
        save_chat_store(st.session_state.all_chats)

def thirty_value(): return 32

with st.sidebar:
    st.markdown('<div class="brand">✦ IntelliDB AI</div><div class="brand-sub">Your intelligent DBMS companion</div>', unsafe_allow_html=True)
    st.write("")
    if st.button("＋  New chat", use_container_width=True):
        new_chat()
    st.markdown("**WORKSPACE**")
    for item, icon in [("AI Chat","◈"),("Documents","⌁"),("Knowledge Graph","◎")]:
        if st.button(f"{icon}  {item}", key=f"nav_{item}", use_container_width=True):
            st.session_state.page = item
            st.rerun()
    st.divider()
    st.markdown("**RECENT CONVERSATIONS**")
    if not st.session_state.all_chats:
        st.caption("Your conversations will appear here.")
    for cid, chat in sorted(st.session_state.all_chats.items(), key=lambda x:x[1].get("updated",""), reverse=True)[:12]:
        if st.button("▹  " + chat.get("title","Conversation")[:27], key=f"chat_{cid}", use_container_width=True):
            open_chat(cid)
            st.session_state.page = "AI Chat"
            st.rerun()
    st.divider()
    st.caption(f"Model · {OLLAMA_CHAT_MODEL}")
    st.caption(f"Embeddings · {OLLAMA_EMBED_MODEL}")
    if st.button("Clear chat history", use_container_width=True):
        st.session_state.all_chats = {}
        st.session_state.messages = []
        st.session_state.chat_id = None
        save_chat_store({})
        st.rerun()

def get_pipeline():
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = RAGPipeline()
    return st.session_state.pipeline

def chat_page():
    st.markdown('<div class="hero"><span class="pill">AI-POWERED DBMS LEARNING</span><h1>Ask. Explore. <span class="glow">Understand.</span></h1><p>Your personal database assistant, powered by Llama 3.2 and retrieval-augmented generation.</p></div>', unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown("### What would you like to learn?")
        prompts = ["Explain database normalization with examples","What is the difference between primary and foreign keys?","Explain ACID properties in DBMS","Write an SQL query to find the second highest salary"]
        cols = st.columns(2)
        for i,p in enumerate(prompts):
            with cols[i%2]:
                if st.button("✦  "+p,key=f"suggest_{i}",use_container_width=True):
                    st.session_state.pending_prompt = p
    for m in st.session_state.messages:
        if m["role"] == "user":
            st.markdown(f'<div class="chat-user">👤 &nbsp;{m["content"]}</div>',unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown('<div class="chat-ai">✦ &nbsp; **IntelliDB AI**</div>',unsafe_allow_html=True)
                st.markdown(m["content"])
                if m.get("sources"):
                    with st.expander("📚 Sources used"):
                        for s in m["sources"]: st.caption(s)
    prompt = st.chat_input("Ask anything about DBMS, SQL, normalization, transactions...")
    if "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")
    if prompt:
        if not st.session_state.chat_id: new_chat()
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.spinner("IntelliDB is thinking..."):
            try:
                history = st.session_state.messages[:-1][-8:]
                result = get_pipeline().answer(prompt, history)
                answer, sources = result["answer"], result["sources"]
            except Exception as e:
                answer = f"**Connection issue:** {e}\n\nCheck that Ollama is running and the required models are installed."
                sources = []
        st.session_state.messages.append({"role":"assistant","content":answer,"sources":sources})
        persist()
        st.rerun()

def knowledge_graph_page():
    st.markdown("## ◎ Knowledge Graph Explorer")
    st.write("Explore DBMS entities and explicitly labeled relationships.")
    graph = get_pipeline().graph
    snapshot = graph.snapshot()
    stats = graph.stats()
    c1, c2 = st.columns(2)
    c1.metric("Entities", stats["nodes"])
    c2.metric("Relationships", stats["edges"])
    if not snapshot["nodes"]:
        st.info("No graph entities are available.")
        return

    def quote(value):
        return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = [
        "digraph KnowledgeGraph {", "rankdir=LR;", 'bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fillcolor="#14213b", color="#55e6e0", fontcolor="white"];',
        'edge [color="#9b8cff", fontcolor="#d7d2ff"];'
    ]
    for node in snapshot["nodes"]:
        lines.append(f"{quote(node['id'])} [label={quote(node['label'])}];")
    for edge in snapshot["edges"]:
        lines.append(
            f"{quote(edge['subject'])} -> {quote(edge['object'])} "
            f"[label={quote(edge['predicate'])}];"
        )
    lines.append("}")
    st.graphviz_chart("\n".join(lines), use_container_width=True)
    st.caption("Built-in DBMS ontology facts are labeled built_in_dbms_ontology. Uploaded-document facts include their source and extracted sentence evidence.")
    with st.expander("View entity relationships and evidence", expanded=True):
        for edge in snapshot["edges"]:
            subject = graph.entity_label(edge["subject"])
            obj = graph.entity_label(edge["object"])
            st.markdown(f"- **{subject}** — `{edge['predicate']}` → **{obj}**")
            st.caption("Source: " + ", ".join(edge["sources"]))
            if edge.get("evidence"):
                st.caption("Evidence: " + edge["evidence"][0])


def documents_page():
    st.markdown("## ⌁ Document library")
    st.write("Upload DBMS notes, textbooks or assignments. IntelliDB indexes them for grounded answers.")
    uploads = st.file_uploader("Choose PDF, DOCX or TXT files", type=["pdf","docx","txt"], accept_multiple_files=True)
    if uploads and st.button("＋ Index documents",type="primary"):
        pipe = get_pipeline()
        progress = st.progress(0)
        for i,up in enumerate(uploads):
            try:
                docs = load_uploaded_document(up.name, up.getvalue())
                count = pipe.ingest(docs, up.name)
                st.success(f"{up.name}: indexed {count} chunks")
            except Exception as e: st.error(f"{up.name}: {e}")
            progress.progress((i+1)/len(uploads))
    st.info("Tip: Add trusted DBMS course material to improve answer accuracy.")

def learn_page():
    st.markdown("## ▤ DBMS learning studio")
    st.write("Explore clear explanations and practical examples.")
    topic_names = list(TOPICS.keys())
    choice = st.selectbox("Choose a topic",topic_names)
    t = TOPICS[choice]
    st.markdown(f"### {t['title']}")
    st.markdown(t["content"])
    st.markdown("**Key takeaways**")
    for x in t["points"]: st.markdown(f"- {x}")
    if t.get("sql"):
        st.markdown("**SQL example**")
        st.code(t["sql"],language="sql")

def quiz_page():
    st.markdown("## ✧ DBMS quick quiz")
    st.write("Test your understanding with short concept checks.")
    if "quiz_index" not in st.session_state: st.session_state.quiz_index = 0
    if "quiz_score" not in st.session_state: st.session_state.quiz_score = 0
    if "quiz_done" not in st.session_state: st.session_state.quiz_done = False
    qs = QUIZ_QUESTIONS
    if st.session_state.quiz_done:
        st.markdown(f"### Quiz complete — {st.session_state.quiz_score}/{len(qs)} correct")
        if st.button("Try again"):
            st.session_state.quiz_index=0; st.session_state.quiz_score=0; st.session_state.quiz_done=False; st.rerun()
    else:
        i=st.session_state.quiz_index; q=qs[i]
        st.progress(i/len(qs))
        st.caption(f"QUESTION {i+1} OF {len(qs)}")
        st.markdown(f"### {q['question']}")
        ans=st.radio("Select your answer",q["options"],key=f"quiz_{i}")
        if st.button("Submit answer",type="primary"):
            if ans == q["answer"]: st.session_state.quiz_score += 1; st.success("Correct!")
            else: st.error("Not quite. "+q["explanation"])
            if i+1 < len(qs): st.session_state.quiz_index += 1
            else: st.session_state.quiz_done=True
            st.rerun()

page = st.session_state.page
if page == "AI Chat": chat_page()
elif page == "Documents": documents_page()
elif page == "Knowledge Graph": knowledge_graph_page()
elif page == "Learn DBMS": learn_page()
elif page == "Quick Quiz": quiz_page()
