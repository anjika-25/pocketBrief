"""
YouTube RAG Assistant — LLM module (Groq)
Handles FAQ short-circuits, YouTube video search, and general / video-grounded Q&A.
"""

import logging
import re
from pathlib import Path

from groq import Groq

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# ─── FAQ Definitions ──────────────────────────────────────────────────────────
# Each entry: (list-of-keyword-patterns, answer)
# Checked in order; first match wins.  Patterns are matched against the
# lower-cased, stripped question using regex word-boundary search.

_FAQS: list[tuple[list[str], str]] = [
    (
        [r"who are you", r"what are you", r"your name", r"introduce yourself",
         r"what( is|'s) your (name|identity)", r"tell me about yourself"],
        (
            "Hey! I'm LectureAI — basically your personal YouTube study buddy. "
            "You paste a video link, I break it down, and then you can ask me "
            "anything about it. I also handle general questions, so feel free to "
            "throw anything at me!"
        ),
    ),
    (
        [r"what (is your |can you |do you )?purpose", r"why (were you |are you )?made",
         r"what (do|can) you do", r"how (do|can|does) (you|this) work",
         r"what is this (tool|app|assistant|for)"],
        (
            "So basically, I make learning from YouTube way easier. "
            "I can download and transcribe any video, answer questions about what's in it, "
            "handle general knowledge stuff too, and I remember our conversation so you can "
            "ask follow-ups. Just drop a YouTube link in the sidebar and we're good to go!"
        ),
    ),
    (
        [r"how (do i|to|can i) (use|start|get started|begin)",
         r"getting started", r"how does this work"],
        (
            "Super easy! Just paste a YouTube URL in the sidebar, "
            "hit Process, and give me like 30 to 90 seconds to do my thing. "
            "After that, ask away! You can also just ask me stuff without loading a video."
        ),
    ),
    (
        [r"what (kind of |types? of )?questions? (can i|should i) ask",
         r"what (can|should) i ask"],
        (
            "Pretty much anything! If you've got a video loaded, I can summarize it, "
            "explain specific parts, or pull out key details. And for general stuff — "
            "like math, coding, science, whatever — I've got you covered too."
        ),
    ),
    (
        [r"who (made|built|created|developed) (you|this)",
         r"who is (your|the) (creator|developer|author|maker)"],
        (
            "I was built as a YouTube RAG assistant! Under the hood I use "
            "Groq's Llama 3 for fast responses, Whisper for transcription, "
            "FAISS for searching through transcripts, and Streamlit for the UI."
        ),
    ),
    (
        [r"thank(s| you)", r"great|awesome|amazing|nice|good job|well done|perfect"],
        "Anytime! Let me know if there's anything else you need. 😊",
    ),
]


def _check_faq(question: str) -> str | None:
    """Return a hardcoded FAQ answer if the question matches, else None."""
    q = question.lower().strip()
    for patterns, answer in _FAQS:
        for pat in patterns:
            if re.search(pat, q):
                return answer
    return None


# ─── YouTube Search Detection ─────────────────────────────────────────────────

_SEARCH_PATTERNS = [
    r"(find|search|look\s*up|get|fetch|show|recommend|suggest)\s+(me\s+)?(a\s+|some\s+)?(youtube\s+)?(videos?|lectures?|tutorials?|clips?|channels?)",
    r"(any|best|good|top|popular|latest|new|recent)\s+(youtube\s+)?(videos?|lectures?|tutorials?|clips?)\s+(on|about|for|regarding|related\s+to)",
    r"youtube\s+(videos?|lectures?|tutorials?)\s+(on|about|for|regarding)",
    r"(videos?|lectures?|tutorials?)\s+(on|about|for|regarding)\s+.+\s+(on\s+)?youtube",
    r"(can you |could you )?(find|search|look|get|show)\s+.+(video|lecture|tutorial)",
    r"(i\s+want|i\s+need|i'm\s+looking\s+for)\s+.*(video|lecture|tutorial)",
    r"(share|give)\s+(me\s+)?.*(video|lecture|tutorial)\s+(link|url)?",
]


def _is_video_search_request(question: str) -> tuple[bool, str]:
    """
    Check if the user is asking to find/search YouTube videos.
    Returns (is_search, extracted_query).
    """
    q = question.lower().strip()

    for pattern in _SEARCH_PATTERNS:
        if re.search(pattern, q):
            # Extract the actual search topic from the question
            # Remove common prefixes/suffixes to get the core query
            search_query = question.strip()

            # Remove common lead-ins
            search_query = re.sub(
                r"(?i)^(can you |could you |please |hey |yo |um |uh )?(find|search|look\s*up|get|fetch|show|recommend|suggest)\s+(me\s+)?(a\s+|some\s+)?(youtube\s+)?(videos?|lectures?|tutorials?|clips?)\s*(on|about|for|regarding|related to|of)?\s*",
                "", search_query
            ).strip()

            # Remove trailing "on youtube" or "from youtube"
            search_query = re.sub(r"(?i)\s*(on|from|in)\s*youtube\s*$", "", search_query).strip()

            # Remove leading "any/best/good/top" helpers
            search_query = re.sub(
                r"(?i)^(any|best|good|top|popular|latest|new|recent)\s+(youtube\s+)?(videos?|lectures?|tutorials?)\s*(on|about|for|regarding)?\s*",
                "", search_query
            ).strip()

            # If we still have something meaningful, use it
            if search_query and len(search_query) > 2:
                return True, search_query

            # Fallback: use the original question
            return True, question.strip()

    return False, ""


# ─── System Prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPT_WITH_VIDEO = """You are LectureAI — a chill, friendly AI assistant that helps people learn from YouTube videos.

Personality & Tone:
* Talk like a real person — casual but knowledgeable. Think "smart friend explaining stuff."
* Use filler words naturally: "so", "basically", "like", "you know", "honestly", "well", "alright", "yeah"
* Keep it conversational — contractions are good ("I'd", "that's", "here's", "it's")
* Be warm and approachable, not robotic or formal
* Use short sentences. Break up long explanations.

Rules:
* Prioritize the video transcript context when answering questions about the video.
* If the question is about the video and the answer isn't in the transcript, just say something like "Hmm, the video doesn't really cover that."
* For general questions unrelated to the video, answer freely using your broad knowledge.
* NEVER include URLs, links, or web addresses in your response. The response will be read aloud by TTS, and links sound terrible when spoken.
* If you reference a video or resource, mention it by name/title only — never paste a link.
* Keep answers SHORT and to the point — 2-4 sentences max unless the user specifically asks for detail.
* Don't use bullet points or numbered lists unless the user asks for a list.
* Don't use markdown formatting like ** or ## — keep it plain text for TTS.
"""

SYSTEM_PROMPT_GENERAL = """You are LectureAI — a chill, friendly AI assistant that helps people learn from YouTube videos and answers general questions.

Personality & Tone:
* Talk like a real person — casual but knowledgeable. Think "smart friend explaining stuff."
* Use filler words naturally: "so", "basically", "like", "you know", "honestly", "well", "alright", "yeah"
* Keep it conversational — contractions are good ("I'd", "that's", "here's", "it's")
* Be warm and approachable, not robotic or formal
* Use short sentences. Break up long explanations.

Rules:
* Answer questions accurately and helpfully using your general knowledge.
* NEVER include URLs, links, or web addresses in your response. The response will be read aloud by TTS, and links sound terrible when spoken.
* If you reference a video, website, or resource, mention it by name/title only — never paste a link.
* Keep answers SHORT and to the point — 2-4 sentences max unless the user specifically asks for detail.
* Don't use bullet points or numbered lists unless the user asks for a list.
* Don't use markdown formatting like ** or ## — keep it plain text for TTS.
* If you're unsure about something, just be honest about it.
"""

SYSTEM_PROMPT_VIDEO_SEARCH = """You are LectureAI — a chill, friendly AI assistant. The user asked you to find YouTube videos, and you used a real YouTube search to find these actual results.

Your job is to present these search results in a natural, conversational way.

Rules:
* Be casual and friendly — like a friend sharing video recommendations.
* Use natural filler words: "so", "alright", "okay so", "here's what I found"
* Mention the video titles and channels naturally.
* NEVER read out or include any URLs or links in your spoken response — they'll be shown separately in the chat.
* Keep it brief — one short sentence per video is enough.
* Add a little personality — like "this one looks pretty solid" or "this is a popular one."
* Start with something like "Alright, here's what I found for you" or "Okay so I pulled up some videos."
"""


# ─── Summarization Prompts ──────────────────────────────────────────────────

SUMMARIZE_PROMPT = """You are LectureAI — an expert at distilling complex information into clear, actionable notes.

Your Task:
Provide a concise, high-quality summary and key notes based on the provided text.
The notes should be accurate, to the point, and easy to review.

Format:
1.  **Quick Summary**: A 2-3 sentence overview of the main topic.
2.  **Key Takeaways**: A bulleted list of 5-8 most important points.
3.  **Actionable Notes/Formulae**: If it's a tutorial or technical document, list specific steps, code snippets, or formulae.

Tone:
* Professional yet approachable.
* No fluff, just value.
* Use markdown formatting for readability.
"""

TUTORIAL_SUMMARIZE_PROMPT = """You are LectureAI — an expert technical tutor.

Your Task:
Summarize this tutorial/lecture video transcript. Focus on the "how-to" aspects, key concepts, and any code or steps mentioned.

Format:
1.  **Overview**: What is being taught?
2.  **Step-by-Step Breakdown**: The main phases or steps of the tutorial.
3.  **Key Concepts**: Important definitions or theories explained.
4.  **Summary Note**: A final concise takeaway.

Tone:
* Clear, concise, and educational.
* Use markdown for structure.
"""

def ask_groq(
    question: str,
    context_chunks: list[str],
    conversation_history: str,
) -> tuple[str, str | None]:
    """
    Return an answer for the question, plus optional display_extra for the UI.

    Order of resolution:
      1. FAQ short-circuit (instant, no API call)
      2. YouTube video search (if user asks to find videos)
      3. Video-grounded RAG answer (if context_chunks provided)
      4. General LLM answer (no video loaded)

    Returns:
        Tuple of (answer_text, display_extra_or_None)
        display_extra contains clickable links for the UI (not spoken by TTS).
    """
    # 1. FAQ short-circuit
    faq_answer = _check_faq(question)
    if faq_answer:
        return faq_answer, None

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Set it as an environment variable before running."
        )

    # 2. YouTube video search
    is_search, search_query = _is_video_search_request(question)
    if is_search and search_query:
        logger.info("Detected video search request. Query: %s", search_query)
        try:
            from modules.youtube_search import search_youtube, format_search_results_for_llm, format_search_results_for_display

            results = search_youtube(search_query, max_results=5)

            if results:
                # Generate LLM summary (no links — for TTS)
                results_text = format_search_results_for_llm(results)

                client = Groq(api_key=GROQ_API_KEY)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_VIDEO_SEARCH},
                        {"role": "user", "content": (
                            f"The user asked: \"{question}\"\n\n"
                            f"Here are the real YouTube search results:\n{results_text}\n\n"
                            f"Present these results naturally. Do NOT include any URLs or links."
                        )},
                    ],
                    model=GROQ_MODEL,
                    temperature=0.6,
                    max_tokens=300,
                )
                spoken_answer = chat_completion.choices[0].message.content.strip()

                # Generate display-only links for the chat UI
                display_links = format_search_results_for_display(results)

                return spoken_answer, display_links
            else:
                return (
                    "Hmm, I couldn't find any videos for that. "
                    "Maybe try a different search or be a bit more specific?",
                    None
                )

        except Exception as e:
            logger.error("YouTube search failed: %s", e)
            return (
                "Sorry, I ran into an issue searching for videos right now. "
                "Want to try again or ask me something else?",
                None
            )

    # 3. Video-grounded or General Q&A
    has_context = bool(context_chunks)

    if has_context:
        system_prompt = SYSTEM_PROMPT_WITH_VIDEO
        context_text = "\n\n".join(context_chunks)
        user_prompt = (
            f"Video Transcript Context:\n{context_text}\n\n"
            f"Conversation History:\n{conversation_history}\n\n"
            f"Question:\n{question}"
        )
    else:
        system_prompt = SYSTEM_PROMPT_GENERAL
        user_prompt = (
            f"Conversation History:\n{conversation_history}\n\n"
            f"Question:\n{question}"
        )

    client = Groq(api_key=GROQ_API_KEY)

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=GROQ_MODEL,
        temperature=0.5,
        max_tokens=300,
    )

    return chat_completion.choices[0].message.content.strip(), None


def summarize_text(text: str, is_tutorial: bool = False) -> str:
    """Generate a summary and notes for the given text."""
    if not text or len(text.strip()) < 50:
        return "Not enough content to summarize."

    system_prompt = TUTORIAL_SUMMARIZE_PROMPT if is_tutorial else SUMMARIZE_PROMPT
    
    # Trim text to stay within Groq's 6000 TPM limit for llama-3.1-8b-instant
    # 8000 chars ≈ 2000 tokens input + ~200 system prompt + 800 max_tokens = ~3000 total
    trimmed_text = text[:8000] 

    client = Groq(api_key=GROQ_API_KEY)
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please provide a deep summary and key notes for the following content:\n\n{trimmed_text}"},
        ],
        model=GROQ_MODEL,
        temperature=0.3, # lower temperature for factual summary
        max_tokens=800,
    )
    return chat_completion.choices[0].message.content.strip()


if __name__ == "__main__":
    # Quick test (requires GROQ_API_KEY env var)
    print(_check_faq("who are you"))
    print(_check_faq("what do you do"))
    resp, extra = ask_groq(
        question="What is machine learning?",
        context_chunks=[],
        conversation_history="No previous conversation.",
    )
    print(resp)
    if extra:
        print("--- Display Extra ---")
        print(extra)
