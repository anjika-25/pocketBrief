"""
YouTube RAG Assistant — Document Processor module
Handles text extraction from PDF, DOCX, and images (via Groq Vision).
"""

import logging
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import base64

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {file_path}: {e}")
        return ""

def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX {file_path}: {e}")
        return ""

def process_image_with_groq(file_path: Path) -> str:
    """Use Groq Vision model to describe/summarize an image."""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        with open(file_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please transcribe all text in this image. If it's a diagram or photo without much text, describe it in detail."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-11b-vision-preview",
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to process image with Groq Vision {file_path}: {e}")
        return f"Error processing image: {str(e)}"

def extract_content(file_path: str) -> str:
    """Universal content extractor based on file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext == ".pdf":
        text = extract_text_from_pdf(path)
        if not text:
            return "Error: Could not extract text from this PDF. It might be scan-only (image-based) or encrypted."
        return text
    elif ext in [".docx", ".doc"]:
        text = extract_text_from_docx(path)
        if not text:
            return "Error: Could not extract text from this Word document."
        return text
    elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
        return process_image_with_groq(path)
    elif ext in [".txt", ".md"]:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    else:
        logger.warning(f"Unsupported file type: {ext}")
        return f"Error: Unsupported file type '{ext}'."
