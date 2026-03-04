"""
Phase 10 — FastAPI Backend
Provides REST endpoints for video processing and Q&A.
"""

import asyncio
import base64
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import shutil
from config import GROQ_API_KEY, GROQ_MODEL, AUDIO_DIR
from modules.youtube_loader import download_audio
from modules.transcriber import transcribe_audio, transcribe_query
from modules.chunker import load_and_chunk
from modules.embedder import embed_chunks
from modules.vector_store import build_index, save_index
from modules.retriever import retrieve
from modules.groq_llm import ask_groq, summarize_text
from modules.conversation import memory
from modules.tts import speak_async
from modules.document_processor import extract_content

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
)
# Silence noisy third-party loggers that spam the terminal
for _noisy in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="YouTube RAG Lecture Assistant",
    description="Paste a YouTube lecture link, then ask conversational questions grounded in the transcript.",
    version="1.0.0",
)

# Thread pool for running blocking I/O (download, transcribe, embed) without
# blocking the asyncio event loop.
_executor = ThreadPoolExecutor(max_workers=10)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request / Response Models ────────────────────────────────────────────────

class VideoRequest(BaseModel):
    url: str
    video_id: str


class QuestionRequest(BaseModel):
    question: str
    video_id: str
    history_text: str = ""


class ProcessResponse(BaseModel):
    status: str
    message: str
    num_chunks: int
    video_id: str
    summary: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    display_extra: str | None = None
    audio_path: str | None = None
    audio_b64: str | None = None


class HealthResponse(BaseModel):
    status: str


class TitleRequest(BaseModel):
    messages: list[dict]       # [{"role": "user", "content": "..."}, ...]
    transcript_snippet: str = ""  # first ~200 words of transcript (for video chats)


class TitleResponse(BaseModel):
    title: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
async def health():
    """Health check."""
    return HealthResponse(status="ok")


@app.post("/process_video", response_model=ProcessResponse)
async def process_video(req: VideoRequest):
    """
    Full pipeline: download → transcribe → chunk → embed → index.
    Runs in a thread pool so long videos don't block the event loop.
    Timeout is set to 3600 s (1 hour) to support arbitrarily long lectures.
    """
    loop = asyncio.get_event_loop()

    def _run_pipeline():
        logger.info(f"▶ Processing video: {req.url}")
        print(f">>> START PROCESSING: {req.url}") # stdout check

        # Step 1 — Download
        logger.info("Step 1/5: Downloading audio…")
        audio_path = download_audio(req.url, req.video_id)

        # Step 2 — Transcribe
        logger.info("Step 2/5: Transcribing…")
        transcribe_audio(req.video_id, audio_path)

        # Step 3 — Chunk
        logger.info("Step 3/5: Chunking transcript…")
        chunks = load_and_chunk(req.video_id)

        # Step 4 — Embed
        logger.info("Step 4/5: Generating embeddings…")
        embeddings = embed_chunks(chunks)

        # Step 5 — Build & save index
        logger.info("Step 5/5: Building FAISS index…")
        index = build_index(embeddings)
        save_index(index, chunks, req.video_id)

        # Step 6 — Summarize (Optional — don't let this crash the pipeline)
        logger.info("Step 6: Generating summary…")
        summary = ""
        try:
            full_transcript = " ".join(chunks)
            # Check if title suggests a tutorial
            is_tutorial = any(kw in req.url.lower() or "tutorial" in full_transcript.lower()[:500] for kw in ["tutorial", "lecture", "course", "how to"])
            summary = summarize_text(full_transcript, is_tutorial=is_tutorial)
        except Exception as summarize_err:
            logger.warning(f"Summarization failed (non-fatal): {summarize_err}")
            summary = ""

        logger.info("✅ Video processing complete!")
        return chunks, summary

    try:
        chunks, summary = await asyncio.wait_for(
            loop.run_in_executor(_executor, _run_pipeline),
            timeout=3600,  # 1 hour — plenty for the longest lectures
        )
        return ProcessResponse(
            status="success",
            message="Video processed successfully.",
            num_chunks=len(chunks),
            video_id=req.video_id,
            summary=summary
        )

    except asyncio.TimeoutError:
        logger.error("Video processing timed out after 3600 s")
        raise HTTPException(
            status_code=504,
            detail="Processing timed out (> 1 hour). The video may be extremely long. Please try a shorter video.",
        )
    except Exception as e:
        logger.exception("Video processing failed")
        import traceback
        with open("error_log_process.txt", "a", encoding="utf-8") as f:
            f.write("VIDEO PROC ERROR:\n")
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=AnswerResponse)
async def ask(req: QuestionRequest):
    """
    Answer a question using RAG: retrieve → generate → TTS.
    """
    try:
        logger.info(f"❓ Question: {req.question}")

        # 1. Try to retrieve relevant context from video index.
        # If no video has been processed yet, fall back to empty context (general Q&A).
        try:
            context_chunks = retrieve(req.question, req.video_id)
        except FileNotFoundError:
            logger.info("No video index found — answering as general Q&A (no transcript context).")
            context_chunks = []

        # 2. Use passed history text
        history_text = req.history_text

        # 3. Generate answer (general mode if context_chunks is empty)
        answer, display_extra = ask_groq(req.question, context_chunks, history_text)

        # 4. TTS — only speak the answer text (no links/display_extra)
        audio_path = None
        audio_b64 = None
        try:
            audio_path = await speak_async(answer)
            # Encode audio as base64 for direct browser playback
            if audio_path:
                from pathlib import Path as _P
                audio_bytes = _P(audio_path).read_bytes()
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as tts_err:
            logger.warning(f"TTS failed (non-fatal): {tts_err}")

        logger.info(f"💬 Answer: {answer[:120]}…")
        return AnswerResponse(
            answer=answer,
            display_extra=display_extra,
            audio_path=audio_path,
            audio_b64=audio_b64,
        )

    except Exception as e:
        logger.exception("Question answering failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...)):
    """
    Process an uploaded document (PDF, DOCX, Image) and return its summary.
    Runs in a thread pool to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()

    def _process_doc():
        try:
            docs_dir = Path("data/uploads")
            docs_dir.mkdir(parents=True, exist_ok=True)
            
            # Using a unique name to avoid collisions
            import uuid
            ext = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = docs_dir / unique_filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            logger.info(f"📄 Processing document: {file.filename} (saved as {unique_filename})")
            
            content = extract_content(str(file_path))
            if not content or len(content.strip()) < 10:
                return {"error": "Could not extract meaningful content from file or unsupported format."}
            
            if content.startswith("Error:"):
                return {"error": content}
                
            summary = summarize_text(content)
            
            return {
                "status": "success",
                "filename": file.filename,
                "summary": summary
            }
        except Exception as e:
            logger.exception("Document processing internal error")
            return {"error": str(e)}

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _process_doc),
            timeout=300, # 5 minutes for large docs/OCR
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Document processing timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize_video")
async def summarize_video(req: VideoRequest):
    """
    Generate a summary for an already processed video.
    """
    try:
        from config import get_transcript_file
        tf = get_transcript_file(req.video_id)
        if not tf.exists():
            raise HTTPException(status_code=404, detail="Transcript not found for this video.")
            
        text = tf.read_text(encoding="utf-8")
        is_tutorial = "tutorial" in text.lower()[:500] or "lecture" in text.lower()[:500]
        summary = summarize_text(text, is_tutorial=is_tutorial)
        
        return {"summary": summary}
    except Exception as e:
        logger.exception("Summarization failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask_audio", response_model=AnswerResponse)
async def ask_audio(audio_file: UploadFile = File(...)):
    """
    Answer a question asked via voice recording.
    """
    try:
        logger.info("🎤 Received audio question")
        
        # Save temp file
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        temp_audio_path = AUDIO_DIR / "temp_user_query.wav"
        
        with open(temp_audio_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
            
        # Transcribe user's speech
        logger.info("Speech-to-text on user question…")
        transcribed_question = transcribe_query(str(temp_audio_path))
        logger.info(f"User asked: {transcribed_question}")
        
        if not transcribed_question:
             return AnswerResponse(answer="I couldn't hear what you said. Please try again.")

        # We don't have video_id or history passed along with just vanilla audio.
        # This endpoint is deprecated in our current architecture where Streamlit sends STT directly.
        raise HTTPException(status_code=400, detail="Use text /ask instead, since Streamlit handles voice recognition.")

    except Exception as e:
        logger.exception("Voice question processing failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear_memory")
async def clear_memory():
    """Reset the conversation memory."""
    memory.clear()
    return {"status": "ok", "message": "Conversation memory cleared."}


@app.post("/generate_title", response_model=TitleResponse)
async def generate_title(req: TitleRequest):
    """
    Generate a short, descriptive chat title from conversation content.
    Uses a fast LLM call to produce a 3-6 word title.
    """
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        # Build a concise summary of the conversation for the LLM
        conv_text = ""
        for m in req.messages[:4]:  # only first few messages needed
            role = "User" if m.get("role") == "user" else "Assistant"
            content = m.get("content", "")[:200]
            conv_text += f"{role}: {content}\n"

        transcript_hint = ""
        if req.transcript_snippet:
            transcript_hint = f"\nThe conversation is about a YouTube video. Here's a snippet of the transcript:\n{req.transcript_snippet[:300]}\n"

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": (
                    "Generate a SHORT, descriptive title (3-6 words max) for this chat conversation. "
                    "The title should capture the main topic. "
                    "Do NOT use quotes, punctuation, or special characters. "
                    "Do NOT start with 'Chat about' or similar prefixes. "
                    "Just output the title, nothing else. "
                    "Examples: 'Quantum Physics Basics', 'Python List Comprehensions', 'Solar System Formation'"
                )},
                {"role": "user", "content": f"Conversation:\n{conv_text}{transcript_hint}\nGenerate a title:"},
            ],
            model=GROQ_MODEL,
            temperature=0.3,
            max_tokens=20,
        )
        title = completion.choices[0].message.content.strip()
        # Clean up: remove quotes, limit length
        title = title.strip('"\' ').strip()
        if len(title) > 40:
            title = title[:38] + "…"
        return TitleResponse(title=title)
    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        # Fallback: first user message truncated
        for m in req.messages:
            if m.get("role") == "user":
                fallback = m["content"][:30]
                return TitleResponse(title=fallback)
        return TitleResponse(title="New Chat")


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
