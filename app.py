# app.py
"""
EduPlan PH - AI-Enhanced Lesson Plan Generator for Philippine Educators
Main application entry point. Handles UI layout and user interaction.
"""

import streamlit as st
import os
import sys
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from generator import generate_lesson_plan
from utils import export_to_docx, export_to_pdf, export_quiz_to_csv
from config import (
    GRADE_LEVELS, SUBJECTS, LANGUAGES, 
    PROVIDER_MODELS, DEFAULT_MODEL,
    APP_TITLE, APP_ICON, APP_VERSION
)
from validators import validate_inputs, get_api_key_for_provider, get_available_api_keys

load_dotenv()

st.set_page_config(
    page_title=f"{APP_TITLE} {APP_ICON}",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .stButton > button {
        background-color: #006847;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        border: none;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #004d33;
    }
    .footer {
        text-align: center;
        color: #888;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #eee;
    }

    /* Lesson Plan Document Styling */
    .lesson-plan-doc {
        background-color: #ffffff;
        padding: 2.5rem 3rem;
        border-radius: 8px;
        border: 1px solid #d0d0d0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        font-family: 'Arial', 'Helvetica Neue', sans-serif;
        line-height: 1.7;
        color: #1a1a1a;
        max-width: 100%;
    }
    .lesson-plan-doc h2 {
        color: #00442f;
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 1.8rem;
        margin-bottom: 0.6rem;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid #006847;
        letter-spacing: 0.02em;
    }
    .lesson-plan-doc h3 {
        color: #1a1a2e;
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 1.2rem;
        margin-bottom: 0.4rem;
    }
    .lesson-plan-doc h4 {
        color: #333;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.8rem;
        margin-bottom: 0.3rem;
    }
    .lesson-plan-doc p {
        margin: 0.3rem 0;
        text-align: justify;
        font-size: 0.95rem;
    }
    .lesson-plan-doc ul {
        margin: 0.3rem 0 0.3rem 1.2rem;
        padding-left: 0.8rem;
    }
    .lesson-plan-doc ol {
        margin: 0.3rem 0 0.3rem 1.2rem;
        padding-left: 0.8rem;
    }
    .lesson-plan-doc li {
        margin: 0.2rem 0;
        font-size: 0.95rem;
        line-height: 1.65;
    }
    .lesson-plan-doc strong {
        color: #00442f;
    }
    .lesson-plan-doc hr {
        border: none;
        border-top: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    .lesson-plan-doc blockquote {
        border-left: 3px solid #006847;
        padding-left: 1rem;
        margin: 0.5rem 0;
        color: #444;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(f'<p class="main-header">{APP_TITLE} {APP_ICON}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">AI-Enhanced Lesson Plan Generator for Philippine K-12 Educators &nbsp;|&nbsp; v{APP_VERSION}</p>', unsafe_allow_html=True)

st.markdown("""
Generate DepEd-aligned lesson plans and quizzes in seconds.  
Select your grade level, subject, and topic — then let AI do the heavy lifting.
""")
st.divider()


def _md_inline(text: str) -> str:
    """Convert inline markdown (bold, italic) to HTML."""
    # Bold: **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic: *text* -> <em>text</em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


with st.sidebar:
    st.header("Configuration")
    st.subheader("Lesson Details")
    grade_level = st.selectbox("Grade Level", GRADE_LEVELS, index=1)
    subject = st.selectbox("Subject", SUBJECTS, index=3)
    topic = st.text_input("Topic", placeholder="e.g., Photosynthesis, The Cry of Pugad Lawin")
    additional_notes = st.text_area(
        "Additional Notes (Optional)",
        placeholder="e.g., Focus on the light-dependent reactions. Include a hands-on experiment.",
        height=100
    )

    st.subheader("Output Settings")
    language = st.selectbox("Output Language", LANGUAGES, index=0)
    
    models = PROVIDER_MODELS["OpenRouter"]
    model = st.selectbox("AI Model", models, index=0)

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
    st.caption(f"Built with love for Philippine educators | {APP_VERSION}")

if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = None
if "generation_time" not in st.session_state:
    st.session_state.generation_time = None

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_clicked = st.button("Generate Lesson Plan", use_container_width=True)

if generate_clicked:
    api_key, key_debug = get_api_key_for_provider()
    
    if not api_key:
        st.error("API key retrieval failed. Please check your .env file or secrets.")
        st.info(f"Debug: {key_debug['loaded_count']} keys loaded")
    else:
        validation_result = validate_inputs(topic, api_key)

        if not validation_result["valid"]:
            st.error(validation_result["message"])
        else:
            with st.spinner("Generating your lesson plan... This usually takes 5-15 seconds."):
                start_time = datetime.now()

                result = generate_lesson_plan(
                    grade_level=grade_level,
                    subject=subject,
                    topic=topic,
                    language=language,
                    additional_notes=additional_notes,
                    api_key=api_key,
                    model=model
                )

                elapsed = (datetime.now() - start_time).total_seconds()
                st.session_state.generated_plan = result
                st.session_state.generation_time = elapsed

if st.session_state.generated_plan:
    result = st.session_state.generated_plan

    if result["success"]:
        st.success(f"Lesson plan generated in {st.session_state.generation_time:.1f} seconds")
        st.divider()

        st.markdown("### 📄 Generated Lesson Plan")

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
            docx_bytes = export_to_docx(result["content"], topic, grade_level, subject)
            st.download_button(
                label="Download as Word (.docx)",
                data=docx_bytes,
                file_name=f"EduPlanPH_{subject}_{topic}_{grade_level}.docx".replace(" ", "_"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

        with export_col2:
            pdf_bytes = export_to_pdf(result["content"], topic, grade_level, subject)
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
    EduPlan PH {APP_VERSION} &nbsp;|&nbsp; Built with Streamlit, LangChain &nbsp;|&nbsp;
    Designed to empower Philippine educators
</div>
""", unsafe_allow_html=True)