# app.py
"""
EduPlan PH - AI-Enhanced Lesson Plan Generator for Philippine Educators
Main application entry point. Handles UI layout and user interaction.
"""

import streamlit as st
import os
import sys
import re
import base64
import html
import atexit
import bleach
from datetime import datetime
from PIL import Image
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from generator import generate_lesson_plan, generate_topic_suggestions
from utils import export_to_docx, export_to_pdf, export_quiz_to_csv
from config import (
    GRADE_LEVELS, SUBJECTS, LANGUAGES, 
    DEFAULT_MODEL,
    APP_TITLE, APP_ICON, APP_EMOJI, __version__,
    CURRICULUM_VERSIONS, MATATAG_SUBJECTS, MATATAG_HELPER_TEXT,
    CURRICULUM_ALIGNMENT_LABELS
)
from validators import validate_inputs, get_api_key_for_provider, get_available_api_keys
from cache_manager import get_analytics, clear_all_cache

load_dotenv()

# ThreadPoolExecutor for concurrent request handling
# Thread pool size based on typical server resources (CPU cores * 2 + 1 for I/O-bound tasks)
MAX_WORKERS = min(32, (os.cpu_count() or 1) * 2 + 1)
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="eduplan_worker")

def _cleanup_executor():
    """Shutdown the thread pool executor gracefully on exit."""
    executor.shutdown(wait=True)

atexit.register(_cleanup_executor)

# HTML sanitization configuration for bleach
# Allow safe HTML tags commonly used in lesson plans while preventing XSS attacks
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'hr', 'div', 'span'
]
ALLOWED_ATTRS = {
    '*': ['class'],  # Removed 'style' to avoid CSS injection - use classes instead
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title']
}

def sanitize_html_content(html_string: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks while preserving formatting.
    
    Args:
        html_string: Raw HTML string that may contain unsafe content
        
    Returns:
        Sanitized HTML string with dangerous tags and attributes removed
    """
    # First, completely remove script, style, and other dangerous tags with their content
    # This regex removes the entire tag and its content
    dangerous_pattern = r'<(script|style|iframe|object|embed|form|input|textarea|select|button|meta|link|base)[^>]*>.*?</\1>|<(script|style|iframe|object|embed|form|input|textarea|select|button|meta|link|base)[^>]*/?>'
    html_string = re.sub(dangerous_pattern, '', html_string, flags=re.IGNORECASE | re.DOTALL)
    
    # Then use bleach to clean remaining content with allowed tags
    return bleach.clean(
        html_string,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,  # Strip disallowed tags entirely
        strip_comments=True  # Remove HTML comments which can contain sensitive info
    )

# Load Philippine flag icon for page tab
_flag_path = os.path.join(os.path.dirname(__file__), APP_ICON)
_flag_img = Image.open(_flag_path) if os.path.exists(_flag_path) else APP_EMOJI

st.set_page_config(
    page_title=f"{APP_TITLE}",
    page_icon=_flag_img if isinstance(_flag_img, Image.Image) else APP_EMOJI,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Encode flag as base64 for inline HTML rendering
def _flag_b64():
    with open(_flag_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()
_FLAG_B64 = _flag_b64() if os.path.exists(_flag_path) else None

def run_with_progress(task_func, task_args, task_kwargs, text, total_time=10):
    """
    Run a blocking task while updating a progress bar up to 90%.
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.markdown(f"*{text}*")
    
    stop_event = threading.Event()
    result_container = []
    
    def simulate_progress():
        progress = 0.0
        increment = 90.0 / (total_time * 10.0)
        while not stop_event.is_set() and progress < 90:
            time.sleep(0.1)
            progress += increment
            if progress > 90:
                progress = 90.0
            progress_bar.progress(int(progress))
            
        while not stop_event.is_set():
            time.sleep(0.1)
            
        progress_bar.progress(100)
        time.sleep(0.15)
        progress_bar.empty()
        status_text.empty()
        
    t = threading.Thread(target=simulate_progress)
    add_script_run_ctx(t)
    t.start()
    
    try:
        res = task_func(*task_args, **task_kwargs)
        result_container.append(res)
    finally:
        stop_event.set()
        t.join()
        
    return result_container[0]


def generate_lesson_plan_concurrent(grade_level, subject, topic, language, additional_notes, api_key, model, curriculum_version):
    """
    Thread-safe wrapper for generate_lesson_plan to be executed in ThreadPoolExecutor.
    Ensures proper error handling and logging for concurrent operations.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    thread_name = threading.current_thread().name
    logger.info(f"[{thread_name}] Starting lesson plan generation for topic: {topic}")
    
    try:
        result = generate_lesson_plan(
            grade_level=grade_level,
            subject=subject,
            topic=topic,
            language=language,
            additional_notes=additional_notes,
            api_key=api_key,
            model=model,
            curriculum_version=curriculum_version
        )
        
        if result.get("success"):
            logger.info(f"[{thread_name}] Successfully generated lesson plan for topic: {topic}")
        else:
            logger.warning(f"[{thread_name}] Lesson plan generation failed for topic {topic}: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[{thread_name}] Exception during lesson plan generation for topic {topic}: {str(e)}")
        return {
            "success": False,
            "error": f"Concurrent processing error: {str(e)}",
            "content": "",
            "structure_complete": False,
            "missing_sections": []
        }


st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════════
       ACADEMIC AESTHETIC — Color Palette & Design System
       ──────────────────────────────────────────────────────────
       Deep Navy:       #1B2A4A    (primary, headings)
       Oxford Blue:     #002147    (dark accents, sidebar)
       Burgundy:        #6B2737    (call-to-action, emphasis)
       Maroon:          #5A1A2A    (hover states, deep accent)
       Warm Ivory:      #FAF8F3    (page background)
       Parchment:       #F0EDE4    (cards, secondary bg)
       Cream:           #F5F0E8    (alternate surfaces)
       Muted Gold:      #B8973B    (decorative accents, links)
       Antique Gold:    #9A7D30    (hover gold)
       Forest Green:    #2D5F3E    (indicators, success)
       Sage Green:      #5C7A5E    (subtle highlights)
       Charcoal:        #1C1C2E    (body text)
       ═══════════════════════════════════════════════════════════ */

    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Root Variables (Light Mode) ──────────────────────── */
    :root {
        --acad-navy: #1B2A4A;
        --acad-oxford: #002147;
        --acad-burgundy: #6B2737;
        --acad-maroon: #5A1A2A;
        --acad-ivory: #FAF8F3;
        --acad-parchment: #F0EDE4;
        --acad-cream: #F5F0E8;
        --acad-gold: #B8973B;
        --acad-gold-hover: #9A7D30;
        --acad-forest: #2D5F3E;
        --acad-sage: #5C7A5E;
        --acad-charcoal: #1C1C2E;
        --acad-text-secondary: #4A4A5A;
        --acad-border: #D8D3C8;
        --acad-border-light: #E8E3D8;
        --acad-shadow: rgba(27, 42, 74, 0.08);
        --acad-shadow-lg: rgba(27, 42, 74, 0.14);
        --acad-glow-gold: rgba(184, 151, 59, 0.15);
    }

    /* ── Global Typography & Background ──────────────────── */
    .stApp, .main .block-container {
        font-family: 'Inter', 'Georgia', serif !important;
        background-color: var(--acad-ivory) !important;
        color: var(--acad-charcoal) !important;
    }
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Crimson Text', 'Georgia', serif !important;
        color: var(--acad-navy) !important;
    }

    /* ── Main Header & Subtitle ──────────────────────────── */
    .main-header {
        font-family: 'Crimson Text', 'Georgia', serif !important;
        font-size: 2.8rem;
        font-weight: 700;
        color: var(--acad-navy) !important;
        margin-bottom: 0.3rem;
        letter-spacing: 0.01em;
        text-shadow: 0 1px 2px rgba(27, 42, 74, 0.06);
        position: relative;
    }
    .main-header::after {
        content: '';
        display: block;
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, var(--acad-gold), var(--acad-burgundy));
        border-radius: 2px;
        margin-top: 0.5rem;
    }
    .sub-header {
        font-family: 'Inter', sans-serif !important;
        font-size: 1.05rem;
        color: var(--acad-text-secondary) !important;
        margin-bottom: 1.5rem;
        font-weight: 400;
        letter-spacing: 0.02em;
    }

    /* ── Sidebar — Oxford Dark Parchment ─────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(175deg, #0C1829 0%, #142240 50%, #1B2A4A 100%) !important;
        border-right: 1px solid rgba(184, 151, 59, 0.2) !important;
    }
    section[data-testid="stSidebar"] * {
        color: #E8E3D8 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] .stSubheader,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--acad-gold) !important;
        font-family: 'Crimson Text', 'Georgia', serif !important;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: rgba(232, 227, 216, 0.6) !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(184, 151, 59, 0.25) !important;
    }
    /* Sidebar inputs — dark text on light input backgrounds */
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stTextInput > div > div > input,
    section[data-testid="stSidebar"] .stTextArea > div > div > textarea {
        background-color: var(--acad-cream) !important;
        border: 1px solid rgba(184, 151, 59, 0.35) !important;
        border-radius: 6px !important;
        color: var(--acad-charcoal) !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    section[data-testid="stSidebar"] .stTextInput > div > div > input,
    section[data-testid="stSidebar"] .stTextArea > div > div > textarea {
        color: var(--acad-charcoal) !important;
    }
    section[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder,
    section[data-testid="stSidebar"] .stTextArea > div > div > textarea::placeholder {
        color: #8A8578 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div:focus-within,
    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus,
    section[data-testid="stSidebar"] .stTextArea > div > div > textarea:focus {
        border-color: var(--acad-gold) !important;
        box-shadow: 0 0 0 2px var(--acad-glow-gold) !important;
    }

    /* ── Primary Buttons (Burgundy Accent) ───────────────── */
    .stButton > button {
        background: linear-gradient(135deg, var(--acad-burgundy) 0%, var(--acad-maroon) 100%) !important;
        color: #FAF8F3 !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: 0.04em;
        border-radius: 6px !important;
        padding: 0.7rem 2rem !important;
        border: 1px solid rgba(184, 151, 59, 0.2) !important;
        width: 100%;
        box-shadow: 0 2px 8px rgba(107, 39, 55, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative;
        overflow: hidden;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #7D3045 0%, var(--acad-burgundy) 100%) !important;
        box-shadow: 0 4px 16px rgba(107, 39, 55, 0.3) !important;
        border-color: var(--acad-gold) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active {
        transform: translateY(0px);
        box-shadow: 0 1px 4px rgba(107, 39, 55, 0.2) !important;
    }

    /* Sidebar buttons — subtle gold outline variant */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1.5px solid var(--acad-gold) !important;
        color: var(--acad-gold) !important;
        box-shadow: none;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(184, 151, 59, 0.12) !important;
        box-shadow: 0 0 12px var(--acad-glow-gold) !important;
    }

    /* ── Download Buttons — Forest Green Variant ─────────── */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--acad-forest) 0%, #1E4A2E 100%) !important;
        color: #FAF8F3 !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.03em;
        border-radius: 6px !important;
        border: 1px solid rgba(92, 122, 94, 0.3) !important;
        box-shadow: 0 2px 6px rgba(45, 95, 62, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #367A4C 0%, var(--acad-forest) 100%) !important;
        box-shadow: 0 4px 14px rgba(45, 95, 62, 0.25) !important;
        transform: translateY(-1px);
    }

    /* ── Cards & Expanders ───────────────────────────────── */
    [data-testid="stExpander"] {
        background-color: var(--acad-parchment) !important;
        border: 1px solid var(--acad-border) !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 4px var(--acad-shadow);
    }
    [data-testid="stExpander"] summary {
        font-family: 'Crimson Text', serif !important;
        color: var(--acad-navy) !important;
        font-weight: 600;
    }

    /* ── Status Messages ─────────────────────────────────── */
    .stSuccess {
        background-color: rgba(45, 95, 62, 0.08) !important;
        border-left: 4px solid var(--acad-forest) !important;
        color: var(--acad-forest) !important;
    }
    .stError, [data-testid="stNotification"][data-type="error"] {
        background-color: rgba(107, 39, 55, 0.06) !important;
        border-left: 4px solid var(--acad-burgundy) !important;
    }
    .stInfo {
        background-color: rgba(27, 42, 74, 0.06) !important;
        border-left: 4px solid var(--acad-navy) !important;
    }
    .stWarning {
        background-color: rgba(184, 151, 59, 0.08) !important;
        border-left: 4px solid var(--acad-gold) !important;
    }

    /* ── Dividers — Gold Thread ───────────────────────────── */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(
            90deg,
            transparent 0%,
            var(--acad-border) 10%,
            var(--acad-gold) 50%,
            var(--acad-border) 90%,
            transparent 100%
        ) !important;
        opacity: 0.5;
    }

    /* ── Links — Muted Gold ──────────────────────────────── */
    a {
        color: var(--acad-gold) !important;
        text-decoration: none !important;
        border-bottom: 1px solid transparent;
        transition: all 0.2s ease;
    }
    a:hover {
        color: var(--acad-gold-hover) !important;
        border-bottom-color: var(--acad-gold-hover) !important;
    }

    /* ── Spinner ──────────────────────────────────────────── */
    .stSpinner > div > div {
        border-top-color: var(--acad-burgundy) !important;
    }

    /* ── Footer ──────────────────────────────────────────── */
    .footer {
        text-align: center;
        color: var(--acad-text-secondary) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1.2rem;
        border-top: none !important;
        position: relative;
        letter-spacing: 0.03em;
    }
    .footer::before {
        content: '';
        display: block;
        width: 80px;
        height: 2px;
        background: linear-gradient(90deg, var(--acad-gold), var(--acad-burgundy));
        border-radius: 1px;
        margin: 0 auto 1rem auto;
    }

    /* ═══════════════════════════════════════════════════════
       LESSON PLAN DOCUMENT — Scholarly Parchment Card
       ═══════════════════════════════════════════════════════ */
    .lesson-plan-doc {
        background: linear-gradient(170deg, #FFFFFF 0%, var(--acad-cream) 100%);
        padding: 2.5rem 3rem;
        border-radius: 4px;
        border: 1px solid var(--acad-border);
        border-top: 4px solid var(--acad-navy);
        box-shadow:
            0 2px 12px var(--acad-shadow),
            0 0 0 1px var(--acad-border-light),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
        font-family: 'Crimson Text', 'Georgia', serif;
        line-height: 1.8;
        color: var(--acad-charcoal);
        max-width: 100%;
        position: relative;
    }
    /* Gold corner flourish */
    .lesson-plan-doc::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 60px;
        height: 60px;
        background: linear-gradient(225deg, var(--acad-glow-gold) 0%, transparent 60%);
        border-radius: 0 4px 0 0;
    }

    .lesson-plan-doc h2 {
        font-family: 'Crimson Text', 'Georgia', serif !important;
        color: var(--acad-navy) !important;
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 0.6rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid var(--acad-gold);
        letter-spacing: 0.03em;
        text-transform: none;
    }
    .lesson-plan-doc h3 {
        font-family: 'Crimson Text', 'Georgia', serif !important;
        color: var(--acad-oxford) !important;
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1.4rem;
        margin-bottom: 0.4rem;
        padding-left: 0.8rem;
        border-left: 3px solid var(--acad-burgundy);
    }
    .lesson-plan-doc h4 {
        font-family: 'Crimson Text', 'Georgia', serif !important;
        color: var(--acad-forest) !important;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.3rem;
    }
    .lesson-plan-doc p {
        margin: 0.35rem 0;
        text-align: justify;
        font-size: 1rem;
        line-height: 1.75;
    }
    .lesson-plan-doc ul {
        margin: 0.4rem 0 0.4rem 1.4rem;
        padding-left: 0.8rem;
    }
    .lesson-plan-doc ol {
        margin: 0.4rem 0 0.4rem 1.4rem;
        padding-left: 0.8rem;
    }
    .lesson-plan-doc li {
        margin: 0.25rem 0;
        font-size: 1rem;
        line-height: 1.7;
    }
    .lesson-plan-doc li::marker {
        color: var(--acad-gold);
    }
    .lesson-plan-doc strong {
        color: var(--acad-navy) !important;
        font-weight: 700;
    }
    .lesson-plan-doc hr {
        border: none;
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent,
            var(--acad-border) 20%,
            var(--acad-gold) 50%,
            var(--acad-border) 80%,
            transparent
        );
        margin: 1.2rem 0;
        opacity: 0.6;
    }
    .lesson-plan-doc blockquote {
        border-left: 3px solid var(--acad-gold);
        padding-left: 1rem;
        margin: 0.6rem 0;
        color: var(--acad-text-secondary);
        font-style: italic;
        background: rgba(184, 151, 59, 0.04);
        padding: 0.6rem 1rem;
        border-radius: 0 4px 4px 0;
    }

    /* ═══════════════════════════════════════════════════════
       DARK MODE — Candlelit Library
       ═══════════════════════════════════════════════════════ */
    @media (prefers-color-scheme: dark) {
        :root {
            --acad-navy: #8BA4D0;
            --acad-oxford: #6B8CC4;
            --acad-burgundy: #C2748A;
            --acad-maroon: #A85A70;
            --acad-ivory: #121820;
            --acad-parchment: #1A2030;
            --acad-cream: #1E2638;
            --acad-gold: #D4B361;
            --acad-gold-hover: #E5C878;
            --acad-forest: #6AB87A;
            --acad-sage: #7FA882;
            --acad-charcoal: #E0DCD5;
            --acad-text-secondary: #A8A298;
            --acad-border: #2A3240;
            --acad-border-light: #333D4D;
            --acad-shadow: rgba(0, 0, 0, 0.3);
            --acad-shadow-lg: rgba(0, 0, 0, 0.45);
            --acad-glow-gold: rgba(212, 179, 97, 0.2);
        }

        .stApp, .main .block-container {
            background-color: #121820 !important;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(175deg, #0A0F18 0%, #0F1622 50%, #141E2E 100%) !important;
        }

        .lesson-plan-doc {
            background: linear-gradient(170deg, #1A2030 0%, #1E2638 100%);
            border-color: #2A3240;
            border-top-color: #8BA4D0;
        }

        .stButton > button {
            background: linear-gradient(135deg, #7D3045 0%, #6B2737 100%) !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #924060 0%, #7D3045 100%) !important;
        }

        .stDownloadButton > button {
            background: linear-gradient(135deg, #2D5F3E 0%, #1E4A2E 100%) !important;
        }
    }

    /* ── Micro-animations ────────────────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .lesson-plan-doc {
        animation: fadeInUp 0.5s ease-out;
    }
    .main-header {
        animation: fadeInUp 0.4s ease-out;
    }

    /* ── Scrollbar (Academic Dark) ────────────────────────── */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--acad-parchment);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--acad-border);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--acad-gold);
    }

    /* ── Selection color ─────────────────────────────────── */
    ::selection {
        background: rgba(184, 151, 59, 0.25);
        color: var(--acad-navy);
    }

    /* ── MATATAG Curriculum Badge ────────────────────────── */
    .matatag-badge {
        display: inline-block;
        background: linear-gradient(135deg, #0D7377 0%, #14919B 100%);
        color: #FAF8F3 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.3rem 0.8rem;
        border-radius: 4px;
        margin-top: 0.4rem;
        box-shadow: 0 2px 6px rgba(13, 115, 119, 0.25);
    }
    .matatag-badge-sidebar {
        display: inline-block;
        background: linear-gradient(135deg, #0D7377 0%, #14919B 100%);
        color: #FAF8F3 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.25rem 0.7rem;
        border-radius: 4px;
        margin-top: 0.3rem;
        box-shadow: 0 2px 6px rgba(13, 115, 119, 0.25);
    }
    .curriculum-badge {
        display: inline-block;
        background: linear-gradient(135deg, var(--acad-navy) 0%, var(--acad-oxford) 100%);
        color: #FAF8F3 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        padding: 0.35rem 1rem;
        border-radius: 4px;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 6px rgba(27, 42, 74, 0.15);
    }
    .curriculum-badge.matatag-active {
        background: linear-gradient(135deg, #0D7377 0%, #14919B 100%);
        box-shadow: 0 2px 6px rgba(13, 115, 119, 0.2);
    }

    /* ═══════════════════════════════════════════════════════
       RESPONSIVE DESIGN — Adaptive Layout for All Devices
       ═══════════════════════════════════════════════════════ */
    
    /* ── Large Desktop (≥1440px) ─────────────────────────── */
    @media (min-width: 1440px) {
        .main-header {
            font-size: 3.2rem !important;
        }
        .sub-header {
            font-size: 1.2rem !important;
        }
        .lesson-plan-doc {
            padding: 3rem 4rem !important;
            max-width: 1200px;
            margin: 0 auto;
        }
        .stButton > button {
            font-size: 1rem !important;
            padding: 0.8rem 2.5rem !important;
        }
    }

    /* ── Standard Desktop/Laptop (992px - 1439px) ────────── */
    @media (max-width: 1439px) and (min-width: 992px) {
        .main-header {
            font-size: 2.6rem !important;
        }
        .sub-header {
            font-size: 1rem !important;
        }
        .lesson-plan-doc {
            padding: 2.2rem 2.5rem !important;
        }
    }

    /* ── Small Laptop/Tablet Landscape (768px - 991px) ───── */
    @media (max-width: 991px) and (min-width: 768px) {
        .main-header {
            font-size: 2.2rem !important;
        }
        .sub-header {
            font-size: 0.95rem !important;
        }
        .lesson-plan-doc {
            padding: 1.8rem 2rem !important;
        }
        .stButton > button {
            font-size: 0.85rem !important;
            padding: 0.65rem 1.5rem !important;
        }
        section[data-testid="stSidebar"] {
            font-size: 0.9rem !important;
        }
    }

    /* ── Tablet Portrait (576px - 767px) ─────────────────── */
    @media (max-width: 767px) and (min-width: 576px) {
        .main-header {
            font-size: 1.9rem !important;
        }
        .main-header::after {
            width: 50px !important;
        }
        .sub-header {
            font-size: 0.88rem !important;
            margin-bottom: 1.2rem !important;
        }
        .lesson-plan-doc {
            padding: 1.5rem 1.5rem !important;
        }
        .lesson-plan-doc h2 {
            font-size: 1.2rem !important;
        }
        .lesson-plan-doc h3 {
            font-size: 1rem !important;
        }
        .stButton > button {
            font-size: 0.82rem !important;
            padding: 0.6rem 1.2rem !important;
        }
        section[data-testid="stSidebar"] {
            font-size: 0.85rem !important;
        }
        .footer {
            font-size: 0.75rem !important;
        }
    }

    /* ── Mobile Phone (< 576px) ──────────────────────────── */
    @media (max-width: 575px) {
        /* Adjust main container padding */
        .main .block-container {
            padding-top: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* Scale down headers */
        .main-header {
            font-size: 1.6rem !important;
            margin-bottom: 0.2rem !important;
        }
        .main-header::after {
            width: 40px !important;
            height: 2px !important;
            margin-top: 0.4rem !important;
        }
        .sub-header {
            font-size: 0.8rem !important;
            margin-bottom: 1rem !important;
            line-height: 1.4 !important;
        }

        /* Adjust lesson plan document */
        .lesson-plan-doc {
            padding: 1.2rem 1rem !important;
            border-radius: 6px !important;
        }
        .lesson-plan-doc h2 {
            font-size: 1.1rem !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        .lesson-plan-doc h3 {
            font-size: 0.95rem !important;
            margin-top: 1.2rem !important;
        }
        .lesson-plan-doc h4 {
            font-size: 0.9rem !important;
        }
        .lesson-plan-doc p,
        .lesson-plan-doc li {
            font-size: 0.9rem !important;
            line-height: 1.6 !important;
        }
        .lesson-plan-doc ul,
        .lesson-plan-doc ol {
            margin-left: 1rem !important;
            padding-left: 0.5rem !important;
        }

        /* Compact buttons for touch */
        .stButton > button {
            font-size: 0.8rem !important;
            padding: 0.55rem 1rem !important;
            min-height: 44px !important;
        }
        .stDownloadButton > button {
            font-size: 0.78rem !important;
            padding: 0.5rem 0.9rem !important;
        }

        /* Sidebar adjustments */
        section[data-testid="stSidebar"] {
            font-size: 0.8rem !important;
        }
        section[data-testid="stSidebar"] .stSelectbox > div > div,
        section[data-testid="stSidebar"] .stTextInput > div > div > input,
        section[data-testid="stSidebar"] .stTextArea > div > div > textarea {
            font-size: 0.85rem !important;
            padding: 0.4rem !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            font-size: 0.78rem !important;
            padding: 0.5rem 0.8rem !important;
            min-height: 40px !important;
        }

        /* Badges scale down */
        .matatag-badge,
        .matatag-badge-sidebar {
            font-size: 0.62rem !important;
            padding: 0.25rem 0.6rem !important;
        }
        .curriculum-badge {
            font-size: 0.7rem !important;
            padding: 0.3rem 0.8rem !important;
        }

        /* Footer compact */
        .footer {
            font-size: 0.7rem !important;
            margin-top: 2rem !important;
            padding-top: 1rem !important;
        }
        .footer::before {
            width: 60px !important;
            margin-bottom: 0.8rem !important;
        }

        /* Expanders more compact */
        [data-testid="stExpander"] {
            border-radius: 6px !important;
        }
        [data-testid="stExpander"] summary {
            font-size: 0.9rem !important;
            padding: 0.5rem !important;
        }

        /* Ensure touch targets are accessible */
        .stSelectbox > div > div,
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        button,
        a {
            min-height: 44px !important;
        }
    }

    /* ── Extra Small Mobile (< 375px) ────────────────────── */
    @media (max-width: 374px) {
        .main-header {
            font-size: 1.4rem !important;
        }
        .sub-header {
            font-size: 0.75rem !important;
        }
        .lesson-plan-doc {
            padding: 1rem 0.8rem !important;
        }
        .lesson-plan-doc p,
        .lesson-plan-doc li {
            font-size: 0.85rem !important;
        }
    }

    /* ── Print Styles ────────────────────────────────────── */
    @media print {
        .stApp > *:not(.lesson-plan-doc),
        section[data-testid="stSidebar"],
        .stButton,
        .stDownloadButton,
        .footer {
            display: none !important;
        }
        .lesson-plan-doc {
            box-shadow: none !important;
            border: none !important;
            padding: 0 !important;
            max-width: 100% !important;
        }
        body {
            background: white !important;
        }
    }

    /* ── Reduced Motion Preference ───────────────────────── */
    @media (prefers-reduced-motion: reduce) {
        *,
        *::before,
        *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
</style>
""", unsafe_allow_html=True)

_flag_html = f'<img src="data:image/png;base64,{_FLAG_B64}" style="height: 2.2rem; vertical-align: middle; margin-left: 0.5rem; border-radius: 3px; box-shadow: 0 1px 4px rgba(0,0,0,0.15);" />' if _FLAG_B64 else APP_EMOJI
st.markdown(f'<p class="main-header">{APP_TITLE} {_flag_html}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">AI-Enhanced Lesson Plan Generator for Philippine K-12 Educators &nbsp;|&nbsp; v{__version__}</p>', unsafe_allow_html=True)

st.markdown("""
Generate DepEd-aligned lesson plans and quizzes in seconds.  
Select your grade level, subject, and topic — then let AI do the heavy lifting.
""")
st.divider()


def _md_inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) to HTML, safely escaping < and >."""
    # First, escape HTML to prevent accidental injection of actual tags
    text = html.escape(text)
    
    # Code: `text` -> <code>text</code>
    text = re.sub(
        r'`(.+?)`', 
        r'<code style="background-color: rgba(184, 151, 59, 0.15); color: var(--acad-gold); padding: 0.1rem 0.3rem; border-radius: 3px; font-family: \'Courier New\', Courier, monospace;">\1</code>', 
        text
    )
    
    # Bold: **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # Italic: *text* -> <em>text</em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    return text

# Initialize session state variables
if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = None
if "generation_time" not in st.session_state:
    st.session_state.generation_time = None
if "curriculum_version" not in st.session_state:
    st.session_state.curriculum_version = "K-12 Standard"

with st.sidebar:
    st.header("Configuration")
    st.subheader("Lesson Details")
    grade_level = st.selectbox("Grade Level", GRADE_LEVELS, index=1)

    # Curriculum Version Toggle
    st.subheader("Curriculum Version")
    curriculum_version = st.radio(
        "Curriculum",
        CURRICULUM_VERSIONS,
        index=CURRICULUM_VERSIONS.index(st.session_state.curriculum_version),
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state.curriculum_version = curriculum_version
    st.caption(MATATAG_HELPER_TEXT)

    if curriculum_version == "MATATAG Pilot":
        st.markdown(
            '<span class="matatag-badge-sidebar">MATATAG Active</span>',
            unsafe_allow_html=True
        )

    # Filter subjects based on curriculum selection
    _subjects = MATATAG_SUBJECTS if curriculum_version == "MATATAG Pilot" else SUBJECTS
    _subject_index = 0 if curriculum_version == "MATATAG Pilot" else 3
    subject = st.selectbox("Subject", _subjects, index=_subject_index)

    # Initialize topic in session state if not present
    if "topic_input_val" not in st.session_state:
        st.session_state.topic_input_val = ""
    if "topic_widget" not in st.session_state:
        st.session_state.topic_widget = ""

    def sync_topic():
        st.session_state.topic_input_val = st.session_state.topic_widget


    # Provide a simple string as the button key if possible to avoid state rerendering loop if hash is inconsistent
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        topic = st.text_input("Topic", key="topic_widget", value=st.session_state.topic_input_val, on_change=sync_topic, placeholder="e.g., Photosynthesis, The Cry of Pugad Lawin")
    with col_t2:
        # Align button with text input
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        suggest_btn = st.button("💡", help="Suggest Topics")

    if suggest_btn:
        api_key, _ = get_api_key_for_provider()
        if not api_key:
            st.error("API Key missing.")
        else:
            suggestion_result = run_with_progress(
                task_func=generate_topic_suggestions,
                task_args=(),
                task_kwargs={
                    "grade_level": grade_level,
                    "subject": subject,
                    "api_key": api_key,
                    "model": DEFAULT_MODEL
                },
                text="Analyzing curriculum and brainstorming topics...",
                total_time=3
            )
            if suggestion_result["success"]:
                st.session_state.topic_suggestions = suggestion_result["suggestions"]
            else:
                st.error(f"Failed: {suggestion_result['error']}")

    if "topic_suggestions" in st.session_state and st.session_state.topic_suggestions:
        st.caption("Suggested Topics (Click to select):")

        def set_topic(suggestion):
            st.session_state.topic_input_val = suggestion
            st.session_state.topic_widget = suggestion
            st.session_state.topic_suggestions = [] # Clear suggestions after selection

        for sug in st.session_state.topic_suggestions:
            # Hash or format the button key to avoid issues with special characters
            btn_key = f"sug_{hash(sug)}"
            st.button(sug, key=btn_key, use_container_width=True, on_click=set_topic, args=(sug,))

    additional_notes = st.text_area(
        "Additional Notes (Optional)",
        placeholder="e.g., Focus on the light-dependent reactions. Include a hands-on experiment.",
        height=100
    )

    st.subheader("Output Settings")
    language = st.selectbox("Output Language", LANGUAGES, index=0)
    
    model = DEFAULT_MODEL
    st.markdown(f"**Active AI Model:** {model}")

    st.divider()
    st.subheader("API Status")
    available_keys, debug_info = get_available_api_keys()
    
    if available_keys.get("OPENROUTER_API_KEY"):
        st.success("OpenRouter: Connected")
    else:
        st.error("No API Key Found")
        st.info("Add your OpenRouter key to `.env` (local) or Streamlit Cloud Secrets.")
    
    with st.expander("Debug Info"):
        st.write(f"Keys loaded: {debug_info['loaded_count']}/1")
        if available_keys.get("OPENROUTER_API_KEY"):
            st.caption("OpenRouter: Loaded")
        else:
            st.caption("OpenRouter: Not configured")

    st.divider()
    st.subheader("Cache Analytics")
    analytics = get_analytics()
    
    col_a, col_b = st.columns(2)
    col_a.metric("Hit Rate", f"{analytics['hit_rate_pct']:.1f}%")
    col_b.metric("SQLite Size", f"{analytics['sqlite_size_mb']:.2f} MB")
    
    with st.expander("Cache Details"):
        st.write(f"**Total Requests:** {analytics['total_requests']}")
        st.write(f"**Cached Items (SQLite):** {analytics['sqlite_items']}")
        st.write(f"**Avg Latency (Cache):** {analytics['avg_latency_cached_ms']:.1f} ms")
        st.write(f"**Avg Latency (Live):** {analytics['avg_latency_live_ms']:.1f} ms")
        if st.button("🧹 Clear All Cache", use_container_width=True):
            clear_all_cache()
            st.rerun()

    st.divider()
    st.caption(f"Built with love for Philippine educators | {__version__}")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_clicked = st.button("Generate Lesson Plan", use_container_width=True)

if generate_clicked:
    api_key, key_debug = get_api_key_for_provider()
    
    # Determine effective curriculum version (with fallback logic)
    effective_curriculum = st.session_state.curriculum_version
    if effective_curriculum == "MATATAG Pilot" and subject not in MATATAG_SUBJECTS:
        st.warning(
            f"'{subject}' is not yet available under the MATATAG Pilot. "
            "Switching to K-12 Standard for this request."
        )
        effective_curriculum = "K-12 Standard"
    
    if not api_key:
        st.error("API key retrieval failed. Please check your .env file or secrets.")
        st.info(f"Debug: {key_debug['loaded_count']} keys loaded")
    else:
        validation_result = validate_inputs(topic, api_key)

        if not validation_result["valid"]:
            st.error(validation_result["message"])
        else:
            start_time = datetime.now()

            # Submit lesson plan generation to thread pool for concurrent processing
            # This allows multiple users to generate lesson plans simultaneously without blocking
            future = executor.submit(
                generate_lesson_plan_concurrent,
                grade_level=grade_level,
                subject=subject,
                topic=topic,
                language=language,
                additional_notes=additional_notes,
                api_key=api_key,
                model=model,
                curriculum_version=effective_curriculum
            )
            
            result = run_with_progress(
                task_func=future.result,  # Wait for the future to complete
                task_args=(),
                task_kwargs={},
                text="Generating your lesson plan... Formulating structure and content.",
                total_time=8
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            st.session_state.generated_plan = result
            st.session_state.generation_time = elapsed

if st.session_state.generated_plan:
    result = st.session_state.generated_plan

    if result.get("success"):
        if result.get("_served_from_cache"):
            latency = result.get("_cache_latency_ms", 0)
            st.success(f"⚡ Lesson plan served from local cache in {latency:.1f}ms")
        else:
            st.success(f"📝 Lesson plan generated in {st.session_state.generation_time:.1f} seconds")
            
        st.divider()

        st.markdown("### 📄 Generated Lesson Plan")

        # Curriculum alignment label
        _cv = result.get("curriculum_version", "K-12 Standard")
        _cv_label = CURRICULUM_ALIGNMENT_LABELS.get(_cv, "Aligned with: K-12 Standard Curriculum")
        _cv_class = "curriculum-badge matatag-active" if _cv == "MATATAG Pilot" else "curriculum-badge"
        st.markdown(
            f'<div class="{_cv_class}">{_cv_label}</div>',
            unsafe_allow_html=True
        )

        # Convert the markdown content to HTML for proper rendering inside the styled container
        plan_content = result["content"]

        # Convert markdown to HTML using Python's built-in markdown-like processing
        # We process line by line for proper structure
        html_lines = []
        for line in plan_content.split('\n'):
            stripped = line.strip()
            if not stripped:
                html_lines.append('')
                continue

            # Markdown headings
            h_match = re.match(r'^(#{1,4})\s+(.*)', stripped)
            if h_match:
                level = len(h_match.group(1))
                text = h_match.group(2).strip()
                text = _md_inline(text)
                html_lines.append(f'<h{level+1}>{text}</h{level+1}>')
                continue

            # Bold-only Roman numeral headers (e.g., **I. OBJECTIVES**)
            bold_section = re.match(r'^\*\*([IVX]+\.\s+.+)\*\*$', stripped)
            if bold_section:
                text = bold_section.group(1)
                html_lines.append(f'<h2>{text}</h2>')
                continue

            # Unordered list items
            bullet_match = re.match(r'^[\-\*•]\s+(.*)', stripped)
            if bullet_match:
                text = _md_inline(bullet_match.group(1))
                html_lines.append(f'<li>{text}</li>')
                continue

            # Sub-list items (indented bullets)
            sub_bullet_match = re.match(r'^\s+[\-\*•]\s+(.*)', line)
            if sub_bullet_match:
                text = _md_inline(sub_bullet_match.group(1))
                html_lines.append(f'<li style="margin-left: 1.5rem;">{text}</li>')
                continue

            # Numbered list items
            num_match = re.match(r'^\d+\.\s+(.*)', stripped)
            if num_match:
                text = _md_inline(num_match.group(1))
                html_lines.append(f'<li>{text}</li>')
                continue

            # Horizontal rules
            if re.match(r'^---+$', stripped):
                html_lines.append('<hr>')
                continue

            # Regular paragraph
            text = _md_inline(stripped)
            html_lines.append(f'<p>{text}</p>')

        html_content = '\n'.join(html_lines)

        # Wrap consecutive <li> elements in <ul> tags
        html_content = re.sub(
            r'((?:<li[^>]*>.*?</li>\s*)+)',
            r'<ul>\1</ul>',
            html_content,
            flags=re.DOTALL
        )

        # Sanitize HTML content to prevent XSS attacks before rendering
        html_content = sanitize_html_content(html_content)

        # Render inside the styled document container
        st.markdown(
            f'<div class="lesson-plan-doc">{html_content}</div>',
            unsafe_allow_html=True
        )

        if not result["structure_complete"]:
            st.warning(f"Warning: Some DepEd sections may be missing: {', '.join(result['missing_sections'])}")

        st.divider()
        st.markdown("### Export Options")

        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            docx_bytes = export_to_docx(result["content"], topic, grade_level, subject, _cv_label)
            st.download_button(
                label="Download as Word (.docx)",
                data=docx_bytes,
                file_name=f"EduPlanPH_{subject}_{topic}_{grade_level}.docx".replace(" ", "_"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

        with export_col2:
            pdf_bytes = export_to_pdf(result["content"], topic, grade_level, subject, _cv_label)
            st.download_button(
                label="Download as PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"EduPlanPH_{subject}_{topic}_{grade_level}.pdf".replace(" ", "_"),
                mime="application/pdf",
                use_container_width=True
            )

        with export_col3:
            if result.get("quiz_data"):
                csv_data = export_quiz_to_csv(result["quiz_data"])
                st.download_button(
                    label="Download Quiz (.csv)",
                    data=csv_data,
                    file_name=f"EduPlanPH_Quiz_{topic}_{grade_level}.csv".replace(" ", "_"),
                    mime="text/csv",
                    use_container_width=True
                )

        st.divider()
        if st.button("Regenerate with Same Settings"):
            st.session_state.generated_plan = None
            st.rerun()

    else:
        st.error(f"Generation failed: {result['error']}")

st.markdown(f"""
<div class="footer">
    EduPlan PH {__version__} &nbsp;|&nbsp; Built with Streamlit, LangChain &nbsp;|&nbsp;
    Designed to empower Philippine educators
</div>
""", unsafe_allow_html=True)