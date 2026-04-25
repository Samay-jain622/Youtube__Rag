import os
import json
from typing import List
from dotenv import load_dotenv
import yt_dlp
from collections import defaultdict
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_core.output_parsers import StrOutputParser

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_cohere import CohereRerank

# FIX 1: langchain_classic does not exist.
# ContextualCompressionRetriever and MergerRetriever live in langchain.retrievers
from langchain_classic.retrievers import ( ContextualCompressionRetriever, MergerRetriever )

from langchain_community.document_transformers import LongContextReorder
from langchain_groq import ChatGroq

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance
from langchain_qdrant import QdrantVectorStore

from langchain_community.chat_message_histories import SQLChatMessageHistory

# FIX 2: ConversationSummaryMemory lives in langchain.memory, not langchain_classic.memory
from langchain_classic.memory import ConversationSummaryMemory
# =========================
# ENV SETUP
# =========================

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
video_sessions = {}



# =========================
# LLM + MEMORY (Created Once)
# =========================

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.5)



# =========================
# QDRANT CLIENT (Created Once)
# =========================

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# =========================
# FETCH + CHUNK TRANSCRIPT
# =========================

def fetch_and_chunk(video_id: str) -> List[Document]:

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    subtitle_file = f"{video_id}.en.json3"

    try:
        # -------------------------
        # Download subtitles if not present
        # -------------------------
        if not os.path.exists(subtitle_file):
            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "subtitlesformat": "json3",
                "outtmpl": f"{video_id}.%(ext)s",
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

        # -------------------------
        # Validate subtitle file exists
        # -------------------------
        if not os.path.exists(subtitle_file):
            raise ValueError("Subtitles not found for this video")

        # -------------------------
        # Load JSON
        # -------------------------
        with open(subtitle_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data.get("events"):
            raise ValueError("No transcript available for this video")

        # -------------------------
        # Extract segments
        # -------------------------
        transcript_segments = []

        for event in data.get("events", []):
            if "segs" in event:
                text = "".join(seg["utf8"] for seg in event["segs"])
                start = event.get("tStartMs", 0) / 1000
                duration = event.get("dDurationMs", 0) / 1000

                transcript_segments.append({
                    "text": text.strip(),
                    "start": start,
                    "duration": duration,
                })

        if not transcript_segments:
            raise ValueError("Transcript is empty")

        # -------------------------
        # Chunking
        # -------------------------
        WINDOW_SEGS = 9
        OVERLAP_SEGS = 3

        merged_docs = []
        i = 0

        while i < len(transcript_segments):
            window = transcript_segments[i : i + WINDOW_SEGS]

            merged_docs.append(
                Document(
                    page_content=" ".join(seg["text"] for seg in window),
                    metadata={
                        "start": float(window[0]["start"]),
                        "duration": float(sum(seg["duration"] for seg in window)),
                        "video_id": video_id,
                    },
                )
            )

            i += WINDOW_SEGS - OVERLAP_SEGS

        return merged_docs

    except Exception as e:
        msg = str(e)
        if "Private video" in msg:
            raise ValueError("🔒 This video is private")
        elif "Video unavailable" in msg:
            raise ValueError("❌ Video does not exist")
        else:
            raise ValueError(f"❌ Failed to process video: {msg}")
# =========================
# VECTORSTORE SETUP
# =========================




# =========================
# BUILD RETRIEVER PIPELINE
# =========================

def build_chain(vectorstore, docs,memory):

    def get_history(_):
        return memory.load_memory_variables({}).get("history", "")

    dense = vectorstore.as_retriever(search_kwargs={"k": 6})

    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = 6

    merger = MergerRetriever(retrievers=[dense, bm25])

    reranker = CohereRerank(
        model="rerank-english-v3.0",
        top_n=5,
    )

    compression = ContextualCompressionRetriever(
        base_retriever=merger,
        base_compressor=reranker,
    )

    reorder = LongContextReorder()

    def reorder_and_format(docs):
        reordered = reorder.transform_documents(docs)
        lines = []
        for d in reordered:
            start = int(d.metadata.get("start", 0))
            minutes = start // 60
            seconds = start % 60
            lines.append(f"[{minutes:02d}:{seconds:02d}] {d.page_content}")
        return "\n\n".join(lines)

    parallel = RunnableParallel(
        {
            "history": RunnableLambda(get_history),
            "context": (
                compression
                | RunnableLambda(reorder_and_format)
            ),
            # FIX 3: RunnablePassthrough() here passes the full input dict,
            # so we extract just the "question" string for the prompt.
            "question": RunnablePassthrough(),
        }
    )

    prompt = PromptTemplate(
        template="""
You are a helpful assistant answering questions from a YouTube video transcript.

Conversation so far:
{history}

Rules:
- Summary/topics → no timestamps
- Specific moments → include [MM:SS]
- If not in context → say "I don't know"

Context:
{context}

Question:
{question}

Answer:
""",
        input_variables=["history", "context", "question"],
    )

    return parallel | prompt | llm | StrOutputParser()






# =========================
# ROUTER
# =========================

router_prompt=PromptTemplate(
    template="""
Classify query as 
-"summary" -> full video/timeline / notes 
="qa" -> specific question 
Only output one word 
Query:{query}
    """,
    input_variables=["query"],
)
router_chain = router_prompt | llm | StrOutputParser()
# =========================
# INITIALIZE ONCE
# =========================
def route_query(query: str) -> str:
    decision = router_chain.invoke({"query": query}).lower()
    if any(word in decision for word in ["summary", "timeline", "notes"]):
        return "summary"
    return "qa"

# =========================
# GENERALIZED SUMMARIZATION
# =========================

intent_prompt="""
Extract summarization intent 
Return JSON: 
{
"type:"timeline | section | full",
"granularity": "minute | coarse | none",
"style": "bullets | paragraph | notes"
}

Query:{query}
Outpur ONLY JSON
"""

def get_summary_intent(query):
    try:
        response=llm.invoke(intent_prompt.format(query=query)).content
        return json.loads(response)
    except:
        return  {"type": "full", "granularity": "none", "style": "paragraph"}

def group_docs(docs, intent):
    grouped = defaultdict(list)

    if intent["granularity"] == "minute":
        for d in docs:
            key = f"Minute {int(d.metadata['start']//60)}"
            grouped[key].append(d.page_content)

    elif intent["type"] == "section":
        max_time = max(d.metadata["start"] for d in docs)
        midpoint = max_time / 2

        for d in docs:
            key = "First Half" if d.metadata["start"] <= midpoint else "Second Half"
            grouped[key].append(d.page_content)

    else:
        grouped["Full Video"] = [d.page_content for d in docs]

    return grouped

def build_context(grouped):
    context = ""
    for k in sorted(grouped):
        context += f"\n{k}:\n"
        context += " ".join(grouped[k]) + "\n"
    return context

def build_summary_prompt(context, query, intent):

    style_map = {
        "bullets": "Use bullet points",
        "paragraph": "Write in paragraphs",
        "notes": "Write structured notes",
    }

    return f"""
You are summarizing a YouTube video.

User request:
{query}

Instructions:
- {style_map.get(intent["style"], "Write clearly")}
- Follow structure strictly
- Do NOT hallucinate

Context:
{context}

Answer:
"""
def generalized_summary(docs, query):
    intent = get_summary_intent(query)
    grouped = group_docs(docs, intent)
    context = build_context(grouped)
    prompt = build_summary_prompt(context, query, intent)

    return llm.invoke(prompt).content
# =========================
# INIT
# =========================


def init_video(video_id:str):
    if video_id in video_sessions:
        print("Already initialized")
        return
    collection_name = f"youtube_{video_id}"
    try:
        docs = fetch_and_chunk(video_id)
    except Exception as e:
        return str(e)
    
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    if client.count(collection_name).count == 0:
        vectorstore.add_documents(docs)
    

    memory = ConversationSummaryMemory(
        llm=llm,
        chat_memory=SQLChatMessageHistory(
            session_id=f"session_{video_id}",
            connection_string="sqlite:///chat_memory.db",
        ),
    )
    rag_chain = build_chain(vectorstore, docs,memory)
    video_sessions[video_id] = {
        "docs": docs,
        "vectorstore": vectorstore,
        "rag_chain": rag_chain,
        "memory": memory,
    }
# FIX 4 + 5 applied via the ask() helper

def ask(query: str,video_id:str) -> str:

    if video_id not in video_sessions:
        return "Please initialize this video first."
    session=video_sessions[video_id]
    route = route_query(query)

    if route == "summary":
        print("SUMMARY MODE")
        response = generalized_summary(session["docs"],query)

    else:
        print("QA MODE")
        response = session['rag_chain'].invoke(query)

    session['memory'].save_context(
        {"input": query},
        {"output": response},
    )

    return response

#init_video("3dhcmeOTZ_Q")
# VIDEO_ID="3dhcmeOTZ_Q"
# response = ask("What does the speaker say about regression?",VIDEO_ID)
# print(response)


