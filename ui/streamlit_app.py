"""
Phase 11 — Streamlit UI (Redesigned v2)
Premium conversational interface for the YouTube RAG PocketBrief.
"""

import base64
import html
import time
from pathlib import Path
import os
import sys
import uuid
import json
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import CHATS_DIR

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from custom_voice import voice_input

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="PocketBrief",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Dynamic Theme ────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "light"

THEMES = {
    "light": {
        "bg-base":          "#fcfcfc",
        "bg-surface":       "#f4f4f7",
        "bg-elevated":      "#ebebf2",
        "bg-card":          "#ffffff",
        "border":           "rgba(0,0,0,0.06)",
        "border-accent":    "rgba(124,114,187,0.25)",
        "accent-1":         "#7c72bb",
        "accent-2":         "#a49cd9",
        "accent-3":         "#16a34a",
        "text-primary":     "#2a2a38",
        "text-secondary":   "#5b5b76",
        "text-muted":       "#a0a0b8",
        "user-bubble":      "linear-gradient(135deg, #8a7eca 0%, #7c72bb 100%)",
        "ai-bubble-bg":     "#ffffff",
        "ai-bubble-border": "rgba(0,0,0,0.08)",
        "shadow":           "rgba(30, 27, 53, 0.06)",
    },
    "dark": {
        "bg-base":          "#13151c",
        "bg-surface":       "#1a1d27",
        "bg-elevated":      "#21263a",
        "bg-card":          "#252a3a",
        "border":           "rgba(255,255,255,0.09)",
        "border-accent":    "rgba(100,160,255,0.4)",
        "accent-1":         "#7eb8f7",
        "accent-2":         "#b39dfa",
        "accent-3":         "#4ade80",
        "text-primary":     "#dde3f0",
        "text-secondary":   "#9ba3ba",
        "text-muted":       "#5a6278",
        "user-bubble":      "linear-gradient(135deg, #3d6fd6 0%, #6246cc 100%)",
        "ai-bubble-bg":     "#1e2235",
        "ai-bubble-border": "rgba(100,160,255,0.18)",
        "shadow":           "rgba(0, 0, 0, 0.4)",
    }
}

t = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Design tokens ── */
    :root {{
        --bg-base:          {t["bg-base"]};
        --bg-surface:       {t["bg-surface"]};
        --bg-elevated:      {t["bg-elevated"]};
        --bg-card:          {t["bg-card"]};
        --border:           {t["border"]};
        --border-accent:    {t["border-accent"]};
        --accent-1:         {t["accent-1"]};
        --accent-2:         {t["accent-2"]};
        --accent-3:         {t["accent-3"]};
        --text-primary:     {t["text-primary"]};
        --text-secondary:   {t["text-secondary"]};
        --text-muted:       {t["text-muted"]};
        --user-bubble:      {t["user-bubble"]};
        --ai-bubble-bg:     {t["ai-bubble-bg"]};
        --ai-bubble-border: {t["ai-bubble-border"]};
        --shadow-color:     {t["shadow"]};
        --radius-xl:        20px;
    }}

    *, *::before, *::after {{ box-sizing: border-box; }}

    /* ── Base Reset ── */
    html, body, .stApp {{
        background-color: var(--bg-base) !important;
        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--text-primary) !important;
    }}
    /* Force text color on all basic elements to avoid leaking into Streamlit built-ins like toasts */
    .stApp p, .stApp span, .stApp h1, .stApp h2, .stApp h3 {{
        color: var(--text-primary) !important;
    }}
    .stToast {{ background: var(--bg-card) !important; border: 1px solid var(--border) !important; box-shadow: 0 4px 20px var(--shadow-color) !important; border-radius: 10px !important; }}
    .stToast p {{ color: var(--text-primary) !important; font-weight: 500; font-size: 0.88rem; }}

    /* ── NUCLEAR STATUS FIX — force readable styling on st.status() ── */
    [data-testid="stStatusWidget"],
    [data-testid="stStatusWidget"] > div,
    [data-testid="stStatusWidget"] details,
    [data-testid="stStatus"],
    [data-testid="stExpander"],
    div[data-testid="stStatus"],
    .stStatus,
    details[data-testid="stStatus"] {{
        background: var(--bg-surface) !important;
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--accent-1) !important;
        border-radius: 12px !important;
        margin: 0.75rem 0 !important;
    }}
    /* Target the header/summary of the status specifically */
    [data-testid="stStatusWidget"] summary,
    [data-testid="stStatus"] summary,
    .stStatus summary,
    details[data-testid] summary,
    details[data-testid] > summary {{
        background: var(--bg-surface) !important;
        background-color: var(--bg-surface) !important;
        color: var(--text-primary) !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
    }}
    /* Target the hover state - force it to be readable */
    [data-testid="stStatusWidget"] summary:hover,
    [data-testid="stStatus"] summary:hover,
    details[data-testid] summary:hover {{
        background-color: var(--bg-elevated) !important;
    }}
    /* Force ALL text, labels, and icons inside status widgets to be readable */
    [data-testid="stStatusWidget"] *,
    [data-testid="stStatus"] *,
    .stStatus *,
    details[data-testid] * {{
        color: var(--text-primary) !important;
        fill: var(--text-primary) !important;
    }}
    /* Target the label text specifically which Streamlit often hides in dark spans */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stStatusWidget"] label,
    [data-testid="stStatusWidget"] span,
    [data-testid="stStatusWidget"] div {{
        color: var(--text-primary) !important;
    }}
    /* Also handle the st.spinner text and svg */
    .stSpinner > div,
    .stSpinner p,
    [data-testid="stSpinner"] *,
    .stSpinner span {{
        color: var(--text-primary) !important;
    }}
    /* Custom status box for 'redo' module approach */
    .custom-status-box {{
        background: var(--bg-surface) !important;
        border: 2px solid var(--accent-1) !important;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 1.25rem 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
        box-shadow: 0 4px 15px var(--shadow-color);
    }}
    .custom-status-label {{
        font-weight: 700;
        color: var(--text-primary) !important;
        font-size: 1rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .custom-status-progress {{
        color: var(--text-secondary) !important;
        font-size: 0.9rem;
        line-height: 1.4;
    }}
    /* Color overrides for different states */
    .custom-status-box.state-error {{
        border-color: #ef4444 !important;
        background: rgba(239, 68, 68, 0.05) !important;
    }}
    .custom-status-box.state-error .custom-status-label {{
        color: #ef4444 !important;
    }}
    .custom-status-box.state-success {{
        border-color: var(--accent-3) !important;
        background: rgba(22, 163, 74, 0.05) !important;
    }}
    .custom-status-box.state-success .custom-status-label {{
        color: var(--accent-3) !important;
    }}
    .pulse-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--accent-1);
    }}

    /* Hide streamlit chrome */
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* ── Remove top gap & Center Main Content ── */
    .block-container {{
        padding-top: 0rem !important;
        padding-bottom: 4rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 820px !important;
        margin: 0 auto !important;
    }}
    /* Collapse the stApp top padding Streamlit adds */
    .stApp > div:first-child {{
        padding-top: 0 !important;
    }}
    div[data-testid="stAppViewContainer"] > section > div:first-child {{
        padding-top: 0.5rem !important;
    }}

    /* ── NUCLEAR SIDEBAR FIX ── */
    [data-testid="stSidebar"] {{
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border) !important;
    }}
    /* ChatGPT-like sidebar sizing + padding (keep your colors) */
    section[data-testid="stSidebar"] {{
        width: 320px !important;
    }}
    
    /* Ensure only non-streamlit elements get the primary color override */
    .stApp > div:not(.stToast):not(.stStatus) {{
        color: var(--text-primary);
    }}
    section[data-testid="stSidebar"] > div {{
        padding-top: 0.25rem !important;
    }}
    [data-testid="stSidebarContent"] {{
        padding: 0.75rem 0.65rem 0.9rem 0.65rem !important;
    }}

    /* Remove Streamlit's default vertical whitespace inside sidebar */
    [data-testid="stSidebar"] .element-container,
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div,
    [data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
        gap: 0.35rem !important;
    }}
    /* Hunt down every possible container in the sidebar and kill padding/margin */
    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    .st-emotion-cache-16idsys, 
    .st-emotion-cache-z5fcl4,
    .st-emotion-cache-6q9sum {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}
    /* Super aggressive hack: Pull the entire content block up */
    [data-testid="stSidebarContent"] > div:first-child {{
        margin-top: -4rem !important; /* Pull up further to hide labels */
    }}
    /* Hide the sidebar collapse button gap if it exists */
    [data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label {{
        color: var(--text-secondary) !important;
        font-size: 0.84rem;
    }}

    /* Logo & Theme Toggle */
    .sidebar-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.2rem 0.8rem 1.1rem 0.8rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1rem;
    }}
    .sidebar-logo {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .theme-toggle-wrap {{
        display: flex;
        align-items: center;
    }}
    .logo-icon {{
        width: 32px; height: 32px;
        background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
        border-radius: 9px;
        display: flex; align-items: center; justify-content: center;
        font-size: 15px; color: #fff;
        box-shadow: 0 2px 10px rgba(124,114,187,0.18);
        flex-shrink: 0;
    }}
    .logo-text {{
        font-weight: 700;
        font-size: 0.98rem;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em;
    }}
    .logo-sub {{
        font-size: 0.68rem;
        color: var(--text-muted) !important;
        margin-top: 1px;
    }}

    /* Section labels */
    .section-label {{
        font-size: 0.67rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted) !important;
        margin: 1rem 0 0.5rem 0;
        display: block;
    }}

    /* Status pill */
    .status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 11px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 500;
        margin: 0.4rem 0;
    }}
    .status-pill.ready {{
        background: rgba(22,163,74,0.08);
        border: 1px solid rgba(22,163,74,0.25);
        color: var(--accent-3);
    }}
    .status-pill.idle {{
        background: rgba(142,136,168,0.1);
        border: 1px solid var(--border);
        color: var(--text-muted);
    }}
    .sdot {{ width:6px; height:6px; border-radius:50%; flex-shrink:0; }}
    .sdot.ready {{ background: var(--accent-3); }}
    .sdot.idle  {{ background: var(--text-muted); }}

    /* ── Chat history list / groups ── */
    .hist-list,
    .chat-group {{
        display: flex;
        flex-direction: column;
        gap: 0 !important;
        margin-top: 2px;
        padding: 0 2px !important;
    }}

    .chat-row {{
        border-radius: 0;
        margin: 0 !important;
        padding: 0 !important;
        background: transparent;
        border: none;
        transition: background 0.18s ease;
        position: relative;
        overflow: visible;
    }}

    .chat-row:hover {{
        background: var(--bg-elevated);
    }}

    .active-chat-row.chat-row {{
        background: var(--bg-elevated);
    }}

    /* Thin divider between chat items */
    .chat-divider {{
        height: 1px;
        background: rgba(0, 0, 0, 0.1);
        margin: 0 0.4rem;
    }}

    /* Style sidebar chat history tiles buttons */
    [data-testid="stSidebar"] div.stButton > button {{
        background: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        color: var(--text-secondary) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        padding: 0.45rem 0.6rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        width: 100% !important;
        transition: color 0.15s ease !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        margin: 0 !important;
        height: auto !important;
        min-height: 0 !important;
        line-height: 1.4 !important;
    }}

    [data-testid="stSidebar"] div.stButton > button:hover {{
        color: var(--text-primary) !important;
    }}
    
    /* Edit button styling — always visible, subtle, highlights on hover */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:nth-child(2) button {{
        background: transparent !important;
        color: var(--text-muted) !important;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        max-width: 28px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 6px !important;
        margin: 0 !important;
        border: none !important;
        transition: background 0.15s ease, color 0.15s ease !important;
        flex-shrink: 0 !important;
        transform: scaleX(-1) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {{
        background: rgba(124, 114, 187, 0.12) !important;
        color: var(--accent-1) !important;
    }}

    /* Active chat button text */
    .active-chat-row div.stButton > button {{
        color: var(--accent-1) !important;
        font-weight: 600 !important;
    }}

    /* Tighten sidebar horizontal block */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
        align-items: center !important;
    }}
    
    /* Sidebar scrollbar hiding */
    [data-testid="stSidebarContent"] {{
        overflow-x: hidden !important;
    }}
    [data-testid="stSidebarContent"]::-webkit-scrollbar {{
        width: 4px;
    }}
    [data-testid="stSidebarContent"]::-webkit-scrollbar-thumb {{
        background: rgba(124, 114, 187, 0.15);
        border-radius: 10px;
    }}

    /* ChatGPT-style Sidebar Section Labels */
    .chat-date-label {{
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-muted) !important;
        margin: 0.8rem 0 0.25rem 0.5rem;
        display: block;
    }}

    /* ── Page header ── */

    /* ── Page header (Moved Up/Left) ── */
    .page-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 1.2rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
        margin-top: -0.5rem; /* Move Up */
    }}
    .hdr-icon {{
        width: 36px; height: 36px;
        background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 17px; color: #fff;
        box-shadow: 0 3px 14px rgba(124,114,187,0.18);
        flex-shrink: 0;
    }}
    .hdr-title {{ margin:0; font-size:1.25rem; font-weight:700; letter-spacing:-0.03em; color:var(--text-primary); }}
    .hdr-sub   {{ margin:3px 0 0; font-size:0.82rem; color:var(--text-secondary); display:flex; align-items:center; gap:6px; }}

    /* ── Info tooltip ── */
    .info-tip {{
        position: relative;
        display: inline-flex;
        align-items: center;
        cursor: help;
    }}
    .info-tip .tip-icon {{
        width: 18px; height: 18px;
        border-radius: 50%;
        background: rgba(109,90,209,0.1);
        border: 1px solid rgba(109,90,209,0.25);
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 10px;
        font-weight: 600;
        color: var(--accent-1);
        font-style: normal;
        transition: background 0.15s;
        user-select: none;
    }}
    .info-tip:hover .tip-icon {{
        background: rgba(109,90,209,0.18);
    }}
    .info-tip .tip-box {{
        visibility: hidden;
        opacity: 0;
        position: absolute;
        top: calc(100% + 10px);
        left: 50%;
        transform: translateX(-70%);
        background: var(--bg-card);
        border: 1px solid var(--border-accent);
        border-radius: 12px;
        padding: 14px 16px;
        width: 300px;
        box-shadow: 0 8px 28px rgba(30,27,53,0.12);
        transition: opacity 0.18s ease, visibility 0.18s ease;
        z-index: 9999;
        pointer-events: none;
    }}
    .info-tip:hover .tip-box {{
        visibility: visible;
        opacity: 1;
        pointer-events: auto;
    }}
    .tip-box-title {{
        font-size: 0.76rem;
        font-weight: 600;
        color: var(--accent-1);
        margin-bottom: 8px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}
    .tip-step {{
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 7px;
        font-size: 0.78rem;
        color: var(--text-secondary);
        line-height: 1.45;
    }}
    .tip-step:last-child {{ margin-bottom: 0; }}
    .tip-num {{
        flex-shrink: 0;
        width: 16px; height: 16px;
        border-radius: 5px;
        background: rgba(109,90,209,0.1);
        border: 1px solid rgba(109,90,209,0.2);
        display: flex; align-items:center; justify-content:center;
        font-size: 0.65rem;
        font-weight: 700;
        color: var(--accent-1);
        margin-top: 1px;
    }}
    /* Caret pointing up (tooltip is below icon now) */
    .tip-box::after {{
        content: '';
        position: absolute;
        bottom: 100%;
        left: 70%;
        transform: translateX(-50%);
        border: 6px solid transparent;
        border-bottom-color: var(--border-accent);
    }}

    /* ── Empty state ── */
    .empty-state {{
        text-align:center;
        padding: 3.5rem 2rem;
        color: var(--text-muted);
    }}
    .empty-state .es-icon {{ font-size:2.5rem; display:block; margin-bottom:0.85rem; opacity:0.3; }}
    .empty-state p {{ font-size:0.87rem; line-height:1.75; max-width:300px; margin:0 auto; }}

    /* ── Chat messages ── */
    .msg-row {{
        display: flex;
        margin-bottom: 1.1rem;
    }}
    .msg-row.user {{ justify-content:flex-end; }}
    .msg-row.ai   {{ justify-content:flex-start; align-items:flex-start; gap:9px; }}

    .ai-avatar {{
        width:30px; height:30px; border-radius:9px;
        background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
        display:flex; align-items:center; justify-content:center;
        font-size:13px; flex-shrink:0; margin-top:2px; color:#fff;
        box-shadow: 0 2px 8px rgba(109,90,209,0.18);
    }}

    .bubble {{
        padding: 0.7rem 1rem;
        font-size: 0.91rem;
        line-height: 1.72;
        max-width: 78%;
        word-break: break-word;
    }}
    .bubble.user {{
        background: var(--user-bubble);
        color: #fff;
        border-radius: var(--radius-xl) var(--radius-xl) 5px var(--radius-xl);
        box-shadow: 0 3px 16px rgba(124,114,187,0.18);
    }}
    .bubble.ai {{
        background: var(--ai-bubble-bg);
        color: var(--text-primary);
        border: 1px solid var(--ai-bubble-border);
        border-radius: 5px var(--radius-xl) var(--radius-xl) var(--radius-xl);
        box-shadow: 0 2px 10px rgba(30,27,53,0.06);
    }}
    .bubble.ai code {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        background: rgba(109,90,209,0.07);
        border: 1px solid rgba(109,90,209,0.12);
        border-radius: 4px;
        padding: 1px 5px;
        color: var(--accent-1);
    }}
    .bubble.ai pre {{
        background: #faf9ff;
        border: 1px solid var(--border);
        border-radius: 9px;
        padding: 0.9rem;
        overflow-x: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.81rem;
        margin: 0.5rem 0;
        color: var(--text-primary);
    }}

    /* ── Streamlit widget overrides ── */
    .stTextInput > div > div > input {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 11px !important;
        color: var(--text-primary) !important;
        font-size: 0.88rem !important;
        padding: 0.55rem 0.9rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: var(--border-accent) !important;
        box-shadow: 0 0 0 3px rgba(109,90,209,0.08) !important;
    }}
    .stTextInput > div > div > input::placeholder {{ color: var(--text-muted) !important; }}
    .stTextInput label {{ color: var(--text-secondary) !important; }}

    /* Buttons — default */
    .stButton > button {{
        background: var(--bg-card) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 9px !important;
        font-size: 0.83rem !important;
        font-weight: 500 !important;
        padding: 0.45rem 0.9rem !important;
        transition: all 0.14s !important;
        font-family: 'Inter', sans-serif !important;
    }}
    .stButton > button:hover {{
        background: var(--bg-elevated) !important;
        border-color: rgba(109,90,209,0.25) !important;
        color: var(--text-primary) !important;
    }}
    /* Primary */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #7c5ce7 0%, #6d5ad1 100%) !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 3px 14px rgba(109,90,209,0.25) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        opacity: 0.88 !important;
        box-shadow: 0 5px 20px rgba(109,90,209,0.35) !important;
    }}

    /* New chat button — target by key or by sidebar first button */
    section[data-testid="stSidebar"] .new-chat-btn > div > button {{
        background: rgba(109,90,209,0.06) !important;
        border: 1px solid rgba(109,90,209,0.18) !important;
        color: var(--accent-1) !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        font-size: 0.84rem !important;
    }}
    section[data-testid="stSidebar"] .new-chat-btn > div > button:hover {{
        background: rgba(109,90,209,0.12) !important;
        border-color: rgba(109,90,209,0.3) !important;
    }}

    /* (Chat history button styles are defined above in the chat-hist-btn section) */

    /* Divider */
    hr {{ border:none; border-top:1px solid var(--border) !important; margin:0.85rem 0 !important; }}

    /* Spinner */
    .stSpinner > div {{ border-top-color: var(--accent-1) !important; }}

    /* Alerts */
    .stSuccess {{ background:rgba(22,163,74,0.06) !important; border-color:rgba(22,163,74,0.2) !important; color:#16a34a !important; border-radius:9px !important; }}
    .stError   {{ background:rgba(220,38,38,0.05) !important; border-color:rgba(220,38,38,0.2) !important; border-radius:9px !important; color:#dc2626 !important; }}
    .stWarning {{ background:rgba(202,138,4,0.06) !important; border-color:rgba(202,138,4,0.2) !important; border-radius:9px !important; color:#ca8a04 !important; }}
    .stSuccess p, .stError p, .stWarning p {{ color: inherit !important; }}

    /* Custom success notification */
    .success-notification {{
        background: linear-gradient(135deg, rgba(22, 163, 74, 0.1), rgba(22, 163, 74, 0.05));
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid rgba(22, 163, 74, 0.2);
        margin: 1.5rem 0;
        animation: notificationSlide 0.5s ease-out;
    }}
    @keyframes notificationSlide {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .success-notification h3 {{ color: #16a34a !important; margin: 0 0 0.5rem 0 !important; }}
    .success-notification p {{ color: #374151 !important; margin: 0 !important; font-size: 0.95rem; }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width:4px; height:4px; }}
    ::-webkit-scrollbar-track {{ background:transparent; }}
    ::-webkit-scrollbar-thumb {{ background:rgba(109,90,209,0.15); border-radius:99px; }}
    ::-webkit-scrollbar-thumb:hover {{ background:rgba(109,90,209,0.3); }}

    iframe {{ border:none !important; }}
    [data-testid="stSkeleton"] {{ display: none !important; }}
    div.stVerticalBlock > div:has(div.stMarkdown) > div.stMarkdown hr {{ margin: 0.5rem 0 !important; }}
</style>
""", unsafe_allow_html=True)
# ─── Session State ────────────────────────────────────────────────────────────
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "video_processed" not in st.session_state:
    st.session_state.video_processed = False
if "processing" not in st.session_state:
    st.session_state.processing = False
if "video_id" not in st.session_state:
    st.session_state.video_id = ""
if "youtube_url" not in st.session_state:
    st.session_state.youtube_url = ""
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "last_q_ts" not in st.session_state:
    st.session_state.last_q_ts = None
if "chat_title" not in st.session_state:
    st.session_state.chat_title = ""
if "editing_chat_id" not in st.session_state:
    st.session_state.editing_chat_id = None
if "last_summary" not in st.session_state:
    st.session_state.last_summary = None
if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None
if "last_upload_ts" not in st.session_state:
    st.session_state.last_upload_ts = 0
if "last_process_ts" not in st.session_state:
    st.session_state.last_process_ts = 0
if "last_q_ts" not in st.session_state:
    st.session_state.last_q_ts = 0
if "video_processing" not in st.session_state:
    st.session_state.video_processing = False
if "clear_input_flag" not in st.session_state:
    st.session_state.clear_input_flag = False
if "process_pending_url" not in st.session_state:
    st.session_state.process_pending_url = None

def save_chat():
    if not st.session_state.chat_history:
        return
    chat_file = CHATS_DIR / f"{st.session_state.chat_id}.json"
    data = {
        "chat_id": st.session_state.chat_id,
        "video_id": st.session_state.video_id,
        "youtube_url": st.session_state.youtube_url,
        "title": st.session_state.chat_title,
        "history": st.session_state.chat_history,
    }
    chat_file.write_text(json.dumps(data), encoding="utf-8")

def clear_to_new_chat():
    st.session_state.chat_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.video_processed = False
    st.session_state.video_id = ""
    st.session_state.youtube_url = ""
    st.session_state.chat_title = ""
    st.session_state.conv_mode_active = False
    st.session_state.conv_audio_b64 = ""
    st.session_state.conv_resume = False
    st.session_state.conv_audio_id = ""
    st.session_state.editing_chat_id = None
    st.session_state.last_summary = None

def load_chat(chat_id):
    chat_file = CHATS_DIR / f"{chat_id}.json"
    if chat_file.exists():
        data = json.loads(chat_file.read_text(encoding="utf-8"))
        st.session_state.chat_id = data.get("chat_id", chat_id)
        st.session_state.video_id = data.get("video_id", "")
        st.session_state.youtube_url = data.get("youtube_url", "")
        st.session_state.chat_title = data.get("title", "")
        st.session_state.chat_history = data.get("history", [])
        st.session_state.video_processed = bool(st.session_state.video_id)

def generate_chat_title():
    """Call the backend to auto-generate a descriptive chat title."""
    try:
        # Get transcript snippet if video is loaded
        transcript_snippet = ""
        if st.session_state.video_id:
            from config import get_transcript_file
            tf = get_transcript_file(st.session_state.video_id)
            if tf.exists():
                full = tf.read_text(encoding="utf-8")
                # First ~200 words
                transcript_snippet = " ".join(full.split()[:200])

        resp = requests.post(
            f"{API_BASE}/generate_title",
            json={
                "messages": st.session_state.chat_history[:4],
                "transcript_snippet": transcript_snippet,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            title = resp.json().get("title", "")
            if title:
                st.session_state.chat_title = title
                save_chat()
    except Exception:
        pass  # Title generation is non-critical; silently fail

def rename_chat(chat_id, new_title):
    """Rename a chat by updating its saved JSON file."""
    chat_file = CHATS_DIR / f"{chat_id}.json"
    if chat_file.exists():
        data = json.loads(chat_file.read_text(encoding="utf-8"))
        data["title"] = new_title
        chat_file.write_text(json.dumps(data), encoding="utf-8")
        # If it's the active chat, update session state too
        if chat_id == st.session_state.chat_id:
            st.session_state.chat_title = new_title
    else:
        # If it happens to be not saved yet, just update session
        if chat_id == st.session_state.chat_id:
            st.session_state.chat_title = new_title
            save_chat()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo & Theme Toggle
    col_logo, col_theme = st.columns([3, 1])
    with col_logo:
        st.markdown("""
        <div class="sidebar-top">
            <div class="sidebar-logo">
                <div class="logo-icon">✦</div>
                <div>
                    <div class="logo-text">PocketBrief</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_theme:
        theme_icon = "🌙" if st.session_state.theme == "light" else "☀️"
        if st.button(theme_icon, help="Toggle Light/Dark Mode"):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()

    # New Chat button (No wrapper divs, integrated style)
    st.button("＋  New Chat", use_container_width=True, on_click=clear_to_new_chat, type="primary")

    st.markdown('<hr>', unsafe_allow_html=True)

    # Video status
    st.markdown('''
        <div class="status-pill ready">
            <span class="sdot ready"></span> Ready to chat
        </div>''' if st.session_state.video_processed else '''
        <div class="status-pill idle">
            <span class="sdot idle"></span> No video loaded
        </div>''', unsafe_allow_html=True)
        
    if st.session_state.video_processed:
        if st.button("📝 Summarize This Video", use_container_width=True):
            with st.spinner("Generating fresh summary..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/summarize_video",
                        json={"video_id": st.session_state.video_id, "url": st.session_state.youtube_url},
                        timeout=60
                    )
                    if resp.status_code == 200:
                        summary = resp.json().get("summary", "")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": f"### 📝 Fresh Video Summary\n\n{summary}"
                        })
                        save_chat()
                        st.rerun()
                    else:
                        st.error("Failed to generate summary.")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Chat History (ChatGPT-style grouped list) ──
    from datetime import datetime, timedelta

    if CHATS_DIR.exists():
        chat_files = sorted(CHATS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
        
        # Grouping logic
        today = []
        yesterday = []
        previous = []
        
        now = datetime.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_yesterday = start_of_today - timedelta(days=1)
        
        for f in chat_files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(f))
                if mtime >= start_of_today:
                    today.append(f)
                elif mtime >= start_of_yesterday:
                    yesterday.append(f)
                else:
                    previous.append(f)
            except Exception:
                continue

        def render_chat_group(files, label):
            if not files:
                return
            st.markdown(f'<span class="chat-date-label">{label}</span>', unsafe_allow_html=True)
            # Wrap group in a flex column so spacing feels like ChatGPT's sidebar
            st.markdown('<div class="chat-group">', unsafe_allow_html=True)
            rendered_count = 0
            for f in files:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    hist = data.get("history", [])
                    if not hist: continue
                    
                    title = data.get("title", "") or ""
                    if not title:
                        for m in hist:
                            if m["role"] == "user":
                                title = m["content"]
                                break
                        if not title: title = "New Chat"

                    is_active = (f.stem == st.session_state.chat_id)

                    # Add divider before every item except the first
                    if rendered_count > 0:
                        st.markdown('<div class="chat-divider"></div>', unsafe_allow_html=True)
                    
                    if st.session_state.editing_chat_id == f.stem:
                        new_name = st.text_input("Rename", value=title, key=f"rename_{f.stem}", label_visibility="collapsed")
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            if st.button("Save", key=f"save_{f.stem}", use_container_width=True):
                                rename_chat(f.stem, new_name)
                                st.session_state.editing_chat_id = None
                                st.rerun()
                        with rc2:
                            if st.button("Cancel", key=f"cancel_{f.stem}", use_container_width=True):
                                st.session_state.editing_chat_id = None
                                st.rerun()
                    else:
                        cols = st.columns([0.88, 0.12])
                        with cols[0]:
                            display_title = title[:40] + ("…" if len(title) > 40 else "")
                            if st.button(display_title, key=f"chat_{f.stem}", use_container_width=True):
                                load_chat(f.stem)
                                st.rerun()
                        with cols[1]:
                            if st.button("✎", key=f"edit_{f.stem}", help="Rename chat"):
                                st.session_state.editing_chat_id = f.stem
                                st.rerun()
                    rendered_count += 1
                except Exception:
                    continue
            st.markdown('</div>', unsafe_allow_html=True)

        render_chat_group(today, "Today")
        render_chat_group(yesterday, "Yesterday")
        render_chat_group(previous, "Previous 30 Days")

        if not today and not yesterday and not previous:
            st.markdown('<p class="empty-state-sidebar">No recent chats</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="empty-state-sidebar">No recent chats</p>', unsafe_allow_html=True)

    # Footer removed


# ─── Process Video helper ─────────────────────────────────────────────────────
def do_process_video(youtube_url):
    """Run the full video processing pipeline."""
    st.session_state.video_processing = True
    print(f"\n>>> PROCESSING START: {youtube_url}")
    
    # Status container provides all the feedback needed
    
    # Status container (no emoji in text since status has its own icons/spinners)
    # Step 1: Create a custom status box (The 'Redo' Module approach)
    status_placeholder = st.empty()
    
    def update_custom_status(label, progress="", state="loading"):
        # Map state to icon and CSS class
        icon_html = '<div class="pulse-dot"></div>' if state == "loading" else "✓"
        status_class = f"state-{state}" if state in ["error", "success"] else ""
        
        status_placeholder.markdown(f"""
        <div class="custom-status-box {status_class}">
            <div class="custom-status-label">
                {icon_html} <span>{label}</span>
            </div>
            <div class="custom-status-progress">
                {progress}
            </div>
        </div>
        """, unsafe_allow_html=True)

    update_custom_status("Preparing to process video...", "Checking URL and generating identifiers...")
    
    try:
        import hashlib
        vid_id = hashlib.md5(youtube_url.encode()).hexdigest()
        
        update_custom_status("Processing YouTube video content...", "Downloading, transcribing, and indexing. This may take 30-90 seconds...")
        
        resp = requests.post(
            f"{API_BASE}/process_video",
            json={"url": youtube_url, "video_id": vid_id},
            timeout=3600,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.video_processed = True
            update_custom_status("Video Indexed & Ready!", "Search and analysis modules are now online.", state="complete")
            time.sleep(1) # leave success message for a moment
            status_placeholder.empty() # clear it out when done

            st.session_state.video_id = data["video_id"]
            st.session_state.youtube_url = youtube_url
            # Append to existing history instead of clearing
            # st.session_state.chat_history = []
            # st.session_state.chat_title = "" 
            
            # Auto-add summary
            summary = data.get("summary", "")
            if summary:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"### 📝 Video Summary & Notes\n\n{summary}"
                })
            
            st.session_state.video_processing = False
            st.session_state.clear_input_flag = True
            save_chat()
        else:
            err = resp.json().get("detail", resp.text)
            update_custom_status("❌ Failed", err, state="error")
            st.session_state.video_processing = False
            st.error(f"Backend Error: {err}")
    except Exception as e:
        update_custom_status("⚠️ System Error", str(e), state="error")
        st.session_state.video_processing = False
        st.error(f"Unexpected connection error: {e}")

# ─── Page Header (with ⓘ info tooltip for "How it works") ────────────────────
st.markdown("""
<div class="page-header">
    <div class="hdr-icon">✦</div>
    <div>
        <h1 class="hdr-title">PocketBrief</h1>
        <div class="hdr-sub">
            <span>Ask about your video — or anything else.</span>
            <span class="info-tip">
                <span class="tip-icon">i</span>
                <div class="tip-box">
                    <div class="tip-box-title">How it works</div>
                    <div class="tip-step">
                        <span class="tip-num">1</span>
                        <span>Paste a YouTube URL in the input bar below</span>
                    </div>
                    <div class="tip-step">
                        <span class="tip-num">2</span>
                        <span>Click <b>Process</b> — downloads &amp; indexes the transcript</span>
                    </div>
                    <div class="tip-step">
                        <span class="tip-num">3</span>
                        <span>Ask anything — answers grounded in the video</span>
                    </div>
                    <div class="tip-step">
                        <span class="tip-num">4</span>
                        <span>Or ask general questions anytime without a video</span>
                    </div>
                </div>
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Chat Area ────────────────────────────────────────────────────────────────
if not st.session_state.chat_history:
    st.markdown("""
    <div class="empty-state">
        <span class="es-icon">◈</span>
        <p>No messages yet.<br>Paste a YouTube link below to process, or ask any question to get started.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="msg-row user"><div class="bubble user">{msg["content"]}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            content = msg["content"]
            display_extra = msg.get("display_extra", "")
            is_html = msg.get("is_html", False)
            
            if is_html:
                st.markdown(content, unsafe_allow_html=True)
            else:
                st.markdown(
                    f'''<div class="msg-row ai">
                        <div class="ai-avatar">✦</div>
                        <div class="bubble ai">{content}</div>
                    </div>''',
                    unsafe_allow_html=True,
                )
            if display_extra:
                with st.expander("📺 View Found Videos", expanded=True):
                    st.markdown(display_extra)

# ── Step 1.5: Process Pending Video (YouTube)
if st.session_state.process_pending_url:
    url = st.session_state.process_pending_url
    st.session_state.process_pending_url = None
    do_process_video(url)
    st.rerun()

# ── Step 2: Process Pending Upload (Document/Image)
if st.session_state.pending_upload:
    up = st.session_state.pending_upload
    st.session_state.pending_upload = None 
    with st.spinner(f"Reading & summarizing {up['name']}…"):
        try:
            file_bytes = base64.b64decode(up["data"])
            files = {"file": (up["name"], file_bytes, up["type"])}
            resp = requests.post(f"{API_BASE}/upload_document", files=files, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"### 📄 Document Summary: {up['name']}\n\n{data.get('summary', '')}"
                })
                save_chat()
                st.rerun()
            else:
                st.error(f"❌ Upload failed: {resp.text}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# Removed horizontal rule to reduce gap

# Session state for conversation mode audio passback
if "conv_audio_b64" not in st.session_state:
    st.session_state.conv_audio_b64 = ""
if "conv_resume" not in st.session_state:
    st.session_state.conv_resume = False
if "conv_mode_active" not in st.session_state:
    st.session_state.conv_mode_active = False
if "conv_audio_id" not in st.session_state:
    st.session_state.conv_audio_id = ""

# Render component with conv mode state and audio data
val = voice_input(
    key="voice_chat_input",
    audio_b64=st.session_state.conv_audio_b64,
    resume_listening=st.session_state.conv_resume,
    conv_mode_active=st.session_state.conv_mode_active,
    audio_id=st.session_state.conv_audio_id,
    # New props for better feedback
    pending_upload=bool(st.session_state.pending_upload),
    video_processing=st.session_state.video_processing,
    clear_input=st.session_state.clear_input_flag,
)

# Reset flags after sending to component
st.session_state.clear_input_flag = False

# Clear the audio data after it's been sent to the component
if st.session_state.conv_audio_b64:
    st.session_state.conv_audio_b64 = ""
    st.session_state.conv_resume = False

# ── Step 1: Capture value from combined input bar
if val and isinstance(val, dict):
    v_action = val.get("action")
    v_ts = val.get("ts", 0)
    v_text = val.get("text", "")
    v_is_conv = val.get("convMode", False)

    # A. Handle conversation mode stop
    if v_action == "stop_conv":
        st.session_state.conv_mode_active = False
        st.session_state.conv_audio_b64 = ""
        st.session_state.conv_audio_id = ""
        st.rerun()

    # B. Handle process_video action
    if v_action == "process_video" and v_ts != st.session_state.last_process_ts:
        st.session_state.last_process_ts = v_ts
        if v_text.strip():
            st.session_state.process_pending_url = v_text.strip()
            st.session_state.video_processing = True
            st.rerun() # Rerun to show "Processing..." state first

    # C. Handle upload_file action
    if v_action == "upload_file" and v_ts != st.session_state.last_upload_ts:
        st.session_state.last_upload_ts = v_ts
        st.session_state.pending_upload = {
            "name": val.get("fileName"),
            "type": val.get("fileType"),
            "data": val.get("fileData"),
            "ts": v_ts
        }
        st.rerun()

    # D. Handle standard text/voice question
    if v_text.strip() and v_ts != st.session_state.last_q_ts and not v_action:
        st.session_state.last_q_ts = v_ts
        st.session_state.conv_mode_active = v_is_conv
        st.session_state.pending_question = v_text
        st.session_state.chat_history.append({"role": "user", "content": v_text})
        save_chat()
        st.rerun()


# ── Step 3: Process Pending Question
if st.session_state.pending_question:
    q_text = st.session_state.pending_question
    is_conv = st.session_state.conv_mode_active
    st.session_state.pending_question = None  # clear so we don't repeat

    with st.spinner("Thinking…"):
        try:
            history_text = "\n".join(
                f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
                for m in st.session_state.chat_history[-7:-1]
            )
            req_payload = {
                "question":     q_text,
                "video_id":     st.session_state.video_id or "general",
                "history_text": history_text or "No previous conversation",
            }
            resp = requests.post(f"{API_BASE}/ask", json=req_payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.chat_history.append({
                    "role":          "assistant",
                    "content":       data["answer"],
                    "display_extra": data.get("display_extra"),
                    "audio_path":    data.get("audio_path"),
                })
                save_chat()

                # ── Auto-generate chat title after first AI response ──
                if not st.session_state.chat_title:
                    generate_chat_title()

                # ── Conversation Mode: send audio back to component for playback ──
                if is_conv and data.get("audio_b64"):
                    st.session_state.conv_audio_b64 = data["audio_b64"]
                    st.session_state.conv_audio_id = str(uuid.uuid4())
                    st.session_state.conv_resume = True
                elif is_conv:
                    # No audio but still conv mode — resume listening
                    st.session_state.conv_resume = True
            else:
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": f"⚠ Error: {resp.text}"}
                )
        except Exception as e:
            st.session_state.chat_history.append(
                {"role": "assistant", "content": f"⚠ Error: {e}"}
            )
    st.rerun()
