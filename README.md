🎥 YouTube RAG Chatbot
Chat with Any YouTube Video using AI

An end-to-end Retrieval-Augmented Generation (RAG) system that transforms YouTube videos into an interactive, queryable knowledge base.

🚀 Live Demo (UI Preview)
📺 Video + Chat Interface

💬 Example Query & Response
assets/
├── ui-main.png
├── chat-example.png

💡 Problem Statement

YouTube videos are information-rich but hard to navigate:

No efficient way to search inside videos
Time-consuming to find specific insights
Poor summarization tools

👉 This project solves that by enabling:

Natural language querying
Context-aware answers
Smart summarization

🧠 Key Features
🔗 Load any YouTube video (URL or ID)
💬 Ask contextual questions about the video
📝 Generate structured summaries:
Timeline-based
Section-wise
Bullet points / notes
⏱ Timestamp-aware answers
🔍 Hybrid retrieval:
Dense (Embeddings)
Sparse (BM25)
Reranked (Cohere)
🧠 Conversational memory (persistent via SQLite)
🎬 Multi-video session handling


User (Streamlit UI)
        ↓
FastAPI Backend
        ↓
RAG Pipeline
   ├── Transcript Extraction (yt-dlp)
   ├── Chunking (Sliding Window)
   ├── Embeddings (MiniLM)
   ├── Qdrant Vector DB
   ├── BM25 Retriever
   ├── Retriever Fusion
   ├── Cohere Reranker
   ├── Context Reordering
   └── LLM (Llama 3 via Groq)

⚙️ Tech Stack
| Layer      | Technology                     |
| ---------- | ------------------------------ |
| LLM        | Groq (Llama 3.3 70B)           |
| Embeddings | MiniLM (sentence-transformers) |
| Vector DB  | Qdrant                         |
| Retrieval  | BM25 + Dense + Reranking       |
| Backend    | FastAPI                        |
| Frontend   | Streamlit                      |
| Memory     | SQLite (LangChain)             |
| Deployment | Docker                         |

🔍 How It Works
1️⃣ Video Processing
Extract subtitles using yt-dlp
Convert into structured transcript
Chunk using overlapping windows
2️⃣ Indexing
Generate embeddings
Store in Qdrant
Build BM25 index
3️⃣ Intelligent Query Routing

A router classifies user queries into:

QA Mode → factual questions
Summary Mode → structured summarization

4️⃣ Retrieval Pipeline
Dense Retrieval (Vector DB)
Sparse Retrieval (BM25)
Merge results
Rerank using Cohere
Reorder for long-context LLMs

5️⃣ Response Generation
Context + Chat History → Prompt
LLM generates grounded responses
Memory updated for continuity

💬 Example Queries

QA Mode
What is linear regression?

Summary Mode
Summarize this video in bullet points

📊 What Makes This Project Strong

This isn’t just a basic chatbot — it demonstrates:

✅ Advanced RAG architecture (not just vector search)
✅ Hybrid retrieval (Dense + Sparse + Reranking)
✅ Query intent classification
✅ Context compression & reordering
✅ Persistent conversational memory
✅ Production-ready API + UI separation
✅ Dockerized deployment


📂 Project Structure
.
├── rag.py              # Core RAG pipeline
├── backend.py          # FastAPI server
├── frontend.py         # Streamlit UI
├── docker-compose.yml  # Deployment setup
├── assets/             # Screenshots
└── .env        

🛠️ Setup Instructions
1️⃣ Clone Repository
git clone https://github.com/your-username/Youtube__Rag.git
cd Youtube__Rag

2️⃣ Create .env

QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_api_key

3️⃣ Run with Docker

docker-compose up
docker logs -f rag_frontend 
docker logs -f rag_backend 

🔌 API Endpoints
POST /init_video
{
  "video_id": "3dhcmeOTZ_Q"
}

Chat
POST /chat
{
  "video_id": "3dhcmeOTZ_Q",
  "query": "Explain linear regression"
}
)
🔮 Future Improvements
🎙 Whisper-based transcription fallback
🌍 Multi-language support
📌 Clickable timestamps in UI
📊 Better UI/UX (chat streaming, highlights)
📤 Export summaries

👨‍💻 Author

Samay Jain
IIT Roorkee


