import streamlit as st
st.set_page_config(page_title="Lean Coffee Board", page_icon="☕", layout="wide")
import pandas as pd
import json
import tempfile
import uuid
from urllib.parse import urlencode

# --- Room (board) selection via URL query param ---
query_params = st.experimental_get_query_params()
board_id = query_params.get("board_id", [None])[0]

if not board_id:
    st.title("🚪 Tham gia hoặc Tạo phòng Lean Coffee")
    col1, col2 = st.columns(2)
    with col1:
        join_id = st.text_input("Nhập ID phòng để tham gia")
        if st.button("Tham gia") and join_id:
            st.query_params = {"board_id": [join_id]}
            st.experimental_rerun()
    with col2:
        if st.button("Tạo phòng mới"):
            new_id = uuid.uuid4().hex[:8]
            st.query_params = {"board_id": [new_id]}
            st.experimental_rerun()
    st.stop()  # halt until a room is selected

# Show current room ID and shareable link suffix
st.sidebar.markdown(f"**ID phòng:** `{board_id}`")
# Shareable link suffix (add to your app's URL)
share_suffix = f"?board_id={board_id}"
st.sidebar.markdown("Bạn có thể thêm phần này vào sau đoạn https://lean-coffee.streamlit.app/ để tham gia cùng phòng:")
st.sidebar.code(share_suffix)
# --- end room handling ---

# Firestore and auto-refresh dependencies
import os
try:
    from streamlit_autorefresh import st_autorefresh
    _has_autorefresh = True
except ModuleNotFoundError:
    _has_autorefresh = False
    st.warning(
        "Module 'streamlit-autorefresh' không được tìm thấy. "
        "Cài đặt `pip install streamlit-autorefresh` để bật tính năng tự làm mới."
    )

# Firestore integration (required for multi-user)
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK from Streamlit Secrets
if not firebase_admin._apps:
    # Load JSON content from secrets
    service_account_info = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    # Write to a temp file for credentials.Certificate
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        json.dump(service_account_info, tf)
        cred_path = tf.name
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# Auto-refresh every 5 seconds for real-time updates (if available)
if _has_autorefresh:
    st_autorefresh(interval=5000, key="refresh")

# CSS styling
st.markdown("""
<style>
.stColumns > div { padding: 0 1rem; }
.card-wrapper {
  background-color: white;
  border-radius: 8px;
  padding: 0 1rem 1rem 0;
  margin-bottom: 1rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #ccc;
  width: 100%;
  box-sizing: border-box;
}
.card-inner { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.5rem; width: 100%; box-sizing: border-box; }
.card-wrapper-discussionitems .stTextArea>div>div>textarea { background-color: #e8f5e9 !important; }

/* Card background per column */
.card-wrapper-discussionitems {
    background-color: #e8f5e9;  /* Light green for Discussion Items */
}
.card-wrapper-currentbeingdiscussed {
    background-color: #fdecea;  /* Light red for Current Being Discussed */
}
.card-wrapper-donediscussing {
    background-color: #f3e5f5;  /* Light purple for Done Discussing */
}

/* Card background for Vietnamese status classes */
.card-wrapper-cầnthảoluận {
    background-color: #e8f5e9 !important;
}
.card-wrapper-đangthảoluận {
    background-color: #fdecea !important;
}
.card-wrapper-hoànthành {
    background-color: #f3e5f5 !important;
}

.card-wrapper-currentbeingdiscussed .stTextArea>div>div>textarea { background-color: #fdecea !important; }
.card-wrapper-donediscussing .stTextArea>div>div>textarea { background-color: #f3e5f5 !important; }
/* Reduce spacing */
.card-wrapper > div.stColumns { margin-bottom: 0.25rem !important; padding-bottom: 0 !important; }
.card-wrapper .stTextArea { margin-top: 0 !important; }
/* Hide apply hint */
.stTextArea > div > div + div { display: none !important; }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'max_votes' not in st.session_state:
    st.session_state['max_votes'] = 5
if 'votes_remaining' not in st.session_state:
    st.session_state['votes_remaining'] = st.session_state['max_votes']

# Load persistent topic for this board
board_ref = db.collection("boards").document(board_id)
board_doc = board_ref.get()
if board_doc.exists and 'current_topic' in board_doc.to_dict():
    current_topic = board_doc.to_dict()['current_topic']
else:
    current_topic = ""
st.session_state['current_topic'] = current_topic

# Load cards from Firestore for current topic
if board_id:
    docs = db.collection("boards") \
             .document(board_id) \
             .collection("cards") \
             .stream()
    st.session_state['discussion_items'] = [
        {"item": doc.id, **doc.to_dict()} for doc in docs
    ]
else:
    st.session_state['discussion_items'] = []

# Firestore save function
def save_to_firestore():
    if not board_id:
        return
    col = db.collection("boards").document(board_id).collection("cards")
    # Clear existing
    for doc in col.stream():
        col.document(doc.id).delete()
    # Write all cards with numeric doc IDs for order
    for idx, card in enumerate(st.session_state['discussion_items']):
        col.document(str(idx)).set({
            "item": card["item"],
            "votes": card["votes"],
            "status": card["status"]
        })

# Callback functions
def move_card(idx, new_status):
    st.session_state["discussion_items"][idx]["status"] = new_status
    save_to_firestore()

def vote_callback(idx, delta):
    st.session_state["discussion_items"][idx]["votes"] += delta
    if delta > 0:
        st.session_state['votes_remaining'] -= 1
    else:
        st.session_state['votes_remaining'] += 1
    save_to_firestore()

def merge_selected_cards():
    merge_keys = [k for k, v in st.session_state.items() if k.startswith("select_") and v]
    merge_indices = sorted(int(k.rsplit("_",1)[1]) for k in merge_keys)
    if len(merge_indices) > 1:
        merged_texts = [st.session_state["discussion_items"][i]["item"] for i in merge_indices]
        new_content = "\n".join(merged_texts)
        new_items = [item for idx, item in enumerate(st.session_state["discussion_items"]) if idx not in merge_indices]
        # Sum votes from merged cards
        sum_votes = sum(st.session_state["discussion_items"][i]["votes"] for i in merge_indices)
        new_items.insert(0, {"item": new_content, "votes": sum_votes, "status": "Cần thảo luận"})
        st.session_state["discussion_items"] = new_items
        for k in merge_keys:
            st.session_state[k] = False
        save_to_firestore()
        st.success("Đã gộp thẻ thành công!")

def delete_card(idx):
    items = st.session_state['discussion_items']
    items.pop(idx)
    st.session_state['discussion_items'] = items
    save_to_firestore()

# Title and create board
st.title("Lean Coffee Board")
st.header("Công cụ họp hiệu quả theo phương pháp Lean Coffee")
with st.form(key='create_board_form'):
    create_topic = st.text_input("Chủ đề cuộc họp:", value=st.session_state['current_topic'])
    create_submit = st.form_submit_button("Bắt đầu nào!")
    if create_submit and create_topic:
        # Persist topic to Firestore
        board_ref.set({'current_topic': create_topic}, merge=True)
        st.session_state['current_topic'] = create_topic
        st.session_state['discussion_items'] = []
        st.session_state['votes_remaining'] = st.session_state['max_votes']

# Display topic
st.markdown(f"### Chủ đề hiện tại: {st.session_state['current_topic']}")

# Sort toggle is in sidebar
# Display cards
items = st.session_state['discussion_items']
if items:
    discussion_items = pd.DataFrame(items)
else:
    discussion_items = pd.DataFrame(columns=["item","votes","status"])
if 'status' not in discussion_items.columns:
    discussion_items['status'] = 'Cần thảo luận'

# Sidebar settings
st.sidebar.header("Cài đặt")
max_votes = st.sidebar.number_input("Số vote tối đa mỗi thành viên", min_value=1, max_value=20,
                                    value=st.session_state['max_votes'], step=1)
if max_votes != st.session_state['max_votes']:
    st.session_state['max_votes'] = max_votes
    st.session_state['votes_remaining'] = max_votes
st.sidebar.markdown(f"**Phiếu còn lại:** {st.session_state['votes_remaining']}")
sort_by_votes = st.sidebar.checkbox("Sắp xếp thẻ theo vote (giảm dần)", value=False)
# Button: Add empty card in sidebar (disabled if no topic)
disabled_new_card = st.session_state['current_topic'] == ""
if st.sidebar.button("Thêm thẻ trống", disabled=disabled_new_card):
    st.session_state['discussion_items'].append({
        "item": "",
        "votes": 0,
        "status": "Cần thảo luận"
    })
    save_to_firestore()

# Columns display
cols = st.columns(3)
status_order = ["Cần thảo luận", "Đang thảo luận", "Hoàn thành"]
for col_idx, status in enumerate(status_order):
    with cols[col_idx]:
        st.subheader(status)
        subset = discussion_items[discussion_items["status"] == status]
        if sort_by_votes:
            subset = subset.sort_values(by="votes", ascending=False, kind="stable")
        for idx, row in subset.iterrows():
            st.markdown(f'<div class="card-wrapper card-wrapper-{status.lower().replace(" ", "")}">', unsafe_allow_html=True)
            btn_cols = st.columns([1,1,1,1,1,1,1])
            with btn_cols[0]:
                sel_key = f"select_{status}_{idx}"
                st.checkbox("", key=sel_key)
            with btn_cols[1]:
                if status != "Cần thảo luận":
                    prev_status = status_order[col_idx-1]
                    st.button("←", key=f"back_{status}_{idx}", on_click=move_card, args=(idx, prev_status))
            with btn_cols[2]:
                if status != "Hoàn thành":
                    next_status = status_order[col_idx+1]
                    st.button("→", key=f"forward_{status}_{idx}", on_click=move_card, args=(idx, next_status))
            with btn_cols[3]:
                like_key = f"like_{status}_{idx}"
                st.button("👍", key=like_key, on_click=vote_callback, args=(idx, 1), disabled=(st.session_state['votes_remaining'] <= 0))
            with btn_cols[4]:
                unvote_key = f"unvote_{status}_{idx}"
                st.button("👎", key=unvote_key, on_click=vote_callback, args=(idx, -1), disabled=(row["votes"] <= 0))
            with btn_cols[5]:
                st.button("🗑️", key=f"delete_{status}_{idx}", on_click=delete_card, args=(idx,))
            with btn_cols[6]:
                st.markdown(f"**{row['votes']}**")
            new_text = st.text_area("", value=row["item"], key=f"edit_{status}_{idx}", height=68)
            if new_text != row["item"]:
                st.session_state["discussion_items"][idx]["item"] = new_text
                save_to_firestore()
            st.markdown("</div>", unsafe_allow_html=True)

# Merge button
if any(k.startswith("select_") and st.session_state[k] for k in st.session_state):
    st.button("Gộp thẻ đã chọn", on_click=merge_selected_cards)