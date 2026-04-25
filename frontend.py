import streamlit as st 
import re
import requests
API_URL = "http://backend:9999/chat"
INIT_API_URL = "http://backend:9999/init_video"
st.set_page_config(page_title="Youtube RAG Chatbot",layout="wide")

st.title("🎥 YouTube RAG Chatbot")

if "videos" not in st.session_state:
    st.session_state.videos=[]

if "active_video" not in st.session_state :
    st.session_state.active_video=None

if "chat_history" not in st.session_state :
    st.session_state.chat_history={}

# =========================
# HELPER: EXTRACT VIDEO ID
# =========================

def extract_video_id(input_str):
    if not input_str:
        return None 
    patterns=[
         r"(?:v=)([a-zA-Z0-9_-]{11})",           # watch?v=
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",   # youtu.be/
        r"(?:embed/)([a-zA-Z0-9_-]{11})",       # embed/
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match:
            return match.group(1)
    
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", input_str):
        return input_str
    return None



st.sidebar.header("📺 Video Manager")
video_input = st.sidebar.text_input("Enter YouTube Video ID",
    placeholder="https://youtube.com/watch?v=... or 3dhcmeOTZ_Q")

st.sidebar.caption(
    "Example: https://www.youtube.com/watch?v=3dhcmeOTZ_Q → ID = 3dhcmeOTZ_Q"
)
if st.sidebar.button("➕ Load Video"):
    video_id=extract_video_id(video_input)
    if not video_id:
        st.sidebar.error("Invalid Youtube URL or Youtube Id")
    else :
        with st.spinner("Processing video (fetching + embeddings)..."):
            payload={
                "video_id":video_id
            }
            try:
                response=requests.post(INIT_API_URL, json=payload)
                if response.status_code != 200:
                    st.sidebar.error("❌ Backend error")
                else:
                    data=response.json()
                    if data["status"]=="error":
                       st.sidebar.error(data["message"])
                    else:
                        if video_id not in st.session_state.videos: 
                            st.session_state.videos.append(video_id)
                            st.session_state.active_video=video_id
                            if video_id not in st.session_state.chat_history:
                                st.session_state.chat_history[video_id] = []
                            st.sidebar.success(f"Loaded:{video_id}")
            except Exception as e: 
                st.sidebar.error(f"❌ API Error: {str(e)}")
# =========================
# VIDEO SELECTOR
# =========================

if st.session_state.videos:
    selected_video = st.sidebar.selectbox(
        "Select Active Video",
        st.session_state.videos,
        index=st.session_state.videos.index(st.session_state.active_video)
        if st.session_state.active_video in st.session_state.videos else 0
    )

    st.session_state.active_video = selected_video


if st.sidebar.button("🗑 Clear Chat"):
    vid = st.session_state.active_video
    if vid:
        st.session_state.chat_history.pop(vid, None)
        if vid in st.session_state.videos:
            st.session_state.videos.remove(vid)
        
        st.session_state.active_video = None

if not st.session_state.active_video:
    st.info("👈 Enter a YouTube video ID and load it to start chatting.")
    st.stop()

video_id = st.session_state.active_video

st.subheader(f"🎬 Active Video: {video_id}")

st.video(f"https://www.youtube.com/watch?v={video_id}")

messages = st.session_state.chat_history.get(video_id, [])
for role, msg in messages:
    with st.chat_message(role):
        st.write(msg)

query = st.chat_input("Ask something about the video...")

if query:
    # Save user message
    st.session_state.chat_history[video_id].append(("user", query))

    with st.chat_message("user"):
        st.write(query)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"video_id": video_id, "query": query}
                )

                if response.status_code != 200:
                    reply = "❌ Backend error"
                else:
                    data = response.json()

                    if data.get("status") == "error":
                        reply = data.get("message")
                    else:
                        reply = data.get("response")

                st.write(reply)

            except Exception as e:
                reply = f"❌ API Error: {str(e)}"
                st.write(reply)

    st.session_state.chat_history[video_id].append(("assistant", reply))
            
            