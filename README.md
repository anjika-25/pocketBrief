# 🚀 pocketBrief: Your AI-Powered YouTube Assistant

Think of **pocketBrief** as that super-organized friend who watches hours of YouTube for you, takes meticulous notes, and lets you ask questions about exactly what was said.

Whether it's a 3-hour lecture, a complex tutorial, or your favorite tech review, **pocketBrief** uses Retrieval-Augmented Generation (RAG) to help you find the information you need, fast.

---

## ✨ What can it do?

- 🎬 **YouTube Summarization:** Just paste a link and get a clear, concise summary of the entire video.
- 🔍 **YouTube Search:** Can't find that one video? Search for it directly from the app.
- 💬 **Interactive Q&A:** Have a conversation with the video. Ask about specific parts, and the AI will pull the most relevant segments using a FAISS-powered vector search.
- 🔊 **Voice Support:** Not in the mood to read? Listen to the summaries and answers with our built-in Edge-TTS integration.
- 🏗️ **Smart RAG Pipeline:** We don't just send the whole transcript to the LLM. We chunk it, embed it using `Sentence-Transformers`, and store it in a `FAISS` index for precise retrieval.
- 🏎️ **Super Fast:** Powered by **Groq** for lightning-fast LLM responses.
- 🎙️ **Local Transcriptions:** If API rate limits are an issue, we've got a local **OpenAI Whisper** fallback to make sure nothing stops the workflow.
- 🖼️ **More than just Videos:** You can also process documents and images for AI-powered analysis.

---

## 🛠️ The Tech Behind the Magic

- **Backend:** FastAPI (Fast, modern, and robust)
- **Frontend:** Streamlit (A clean, interactive UI)
- **Embeddings:** `all-MiniLM-L6-v2` via `sentence-transformers`
- **Vector DB:** `FAISS-cpu`
- **LLM:** `Llama 3` via Groq Cloud
- **Transcription:** Groq (API) & Whisper (Local)
- **Audio:** `edge-TTS`

---

## 🚀 How to Get It Running

### 1. The Basics
Clone the repo and hop into the directory:
```bash
git clone https://github.com/anjika-25/pocketBrief.git
cd pocketBrief
```

### 2. Set Up Your Environment
It's always better to use a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure Your Keys
Create a `.env` file (or set these in your environment):
```env
GROQ_API_KEY=your_api_key_here
```

### 4. Fire It Up!

**Start the Backend (The Brain):**
```bash
uvicorn app:app --reload
```

**Launch the Frontend (The Face):**
```bash
streamlit run ui/streamlit_app.py
```

---

## 🏗️ Project Architecture

```text
├── app.py                # FastAPI Backend
├── config.py             # Global configurations
├── modules/              # The logic for RAG, Transcriber, Chunker, etc.
│   ├── transcriber.py     # Groq/Whisper transcription
│   ├── vector_store.py    # FAISS index management
│   ├── groq_llm.py        # LLM interaction
│   └── ...
├── ui/                   # Streamlit Frontend
└── requirements.txt      # Project dependencies
```

---

## 🤝 Contributing
Found a bug? Have a killer feature idea? Feel free to open an issue or submit a pull request. We're all ears!

---

*Made with ❤️ by the pocketBrief team.*
