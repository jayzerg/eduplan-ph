# src/generator.py
"""
AI generation logic for EduPlan PH.
Handles LLM initialization, prompt assembly, chain invocation,
response parsing, and error handling.
"""


from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import re

from prompts import get_lesson_plan_prompt, get_topic_suggestion_prompt
from config import OPENROUTER_API_BASE
from cache_manager import intelligent_cache

REQUIRED_SECTIONS = {
    "I. OBJECTIVES": r"(?:I\.|1\.)\s*OBJECTIVES",
    "II. CONTENT": r"(?:II\.|2\.)\s*CONTENT",
    "III. LEARNING RESOURCES": r"(?:III\.|3\.)\s*LEARNING\s+RESOURCES",
    "IV. PROCEDURES": r"(?:IV\.|4\.)\s*PROCEDURES",
    "V. ASSESSMENT": r"(?:V\.|5\.)\s*(?:ASSESSMENT|EVALUATION|FORMATIVE)",
    "VI. REFLECTION": r"(?:VI\.|6\.)\s*(?:REFLECTION|REMARKS)"
}


def initialize_llm(api_key: str, model: str):
    """
    Initialize OpenRouter LLM via LangChain ChatOpenAI.
    Passes the API key directly to the constructor for compatibility
    with newer langchain-openai versions. It includes default_headers 
    which are strictly required by OpenRouter for free tier models.
    """
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=OPENROUTER_API_BASE,
        default_headers={
            "HTTP-Referer": "http://localhost:8501", # Your local/production domain
            "X-Title": "EduPlan PH" # Your app name
        },
        temperature=0.7,
        max_tokens=4000,
        timeout=60,
    )


def validate_dlp_structure(content: str) -> dict:
    """
    Verify that the generated content contains all required DepEd DLP sections.
    Uses flexible regex matching to allow for common LLM variations.
    """
    missing = []
    for section_name, pattern in REQUIRED_SECTIONS.items():
        if not re.search(pattern, content, re.IGNORECASE):
            missing.append(section_name)

    return {
        "complete": len(missing) == 0,
        "missing_sections": missing
    }


def extract_quiz_from_content(content: str) -> list:
    """
    Parse the generated lesson plan content to extract quiz questions
    into a structured format for CSV export.
    """
    quiz_data = []
    choice_pattern = r'([A-D])\.\s*(.+?)(?=\n\s*[A-D]\.|\n\s*Answer:|$)'
    answer_pattern = r'Answer:\s*([A-D])'

    blocks = re.split(r'(?=\d+\.\s)', content)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        q_match = re.match(r'(\d+)\.\s*(.+?)(?=\n)', block, re.DOTALL)
        if not q_match:
            continue

        question_num = q_match.group(1)
        question_text = q_match.group(2).strip()
        choices = re.findall(choice_pattern, block)
        answer_match = re.search(answer_pattern, block)

        if choices and answer_match:
            quiz_data.append({
                "number": int(question_num),
                "question": question_text,
                "choice_a": next((c[1] for c in choices if c[0] == 'A'), ''),
                "choice_b": next((c[1] for c in choices if c[0] == 'B'), ''),
                "choice_c": next((c[1] for c in choices if c[0] == 'C'), ''),
                "choice_d": next((c[1] for c in choices if c[0] == 'D'), ''),
                "correct_answer": answer_match.group(1)
            })

    return quiz_data


@intelligent_cache(endpoint="topic_suggestions", cache_type="st")
def generate_topic_suggestions(
    grade_level: str,
    subject: str,
    api_key: str,
    model: str
) -> dict:
    """
    Generate a list of 5 topic suggestions using OpenRouter LLM.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "suggestions": [],
            "error": "No OpenRouter API key found. Please configure your API key."
        }

    try:
        llm = initialize_llm(api_key, model)
        prompt = get_topic_suggestion_prompt()
        chain = prompt | llm | StrOutputParser()

        response = chain.invoke({
            "grade_level": grade_level,
            "subject": subject
        })

        # Parse response into a list of strings
        suggestions = []
        for line in response.split('\n'):
            line = line.strip()
            if line and re.match(r'^\d+\.\s+', line):
                # Remove the number and period (e.g., "1. Topic Name" -> "Topic Name")
                topic_name = re.sub(r'^\d+\.\s+', '', line).strip()
                # Remove markdown formatting like ** or *
                topic_name = re.sub(r'^\*\*?(.*?)\*\*?$', r'\1', topic_name)
                suggestions.append(topic_name)

        if not suggestions:
            # Fallback if the AI didn't format as numbered list
            suggestions = [line.strip() for line in response.split('\n') if line.strip()][:5]

        return {
            "success": True,
            "suggestions": suggestions,
            "error": None
        }

    except Exception as e:
        error_str = str(e)
        user_friendly_error = error_str
        
        if "401" in error_str and "User not found" in error_str:
            user_friendly_error = "Authentication failed (401 - User not found). Please verify your OpenRouter API key in .env or Streamlit Secrets is valid and active."
        elif "401" in error_str:
            user_friendly_error = "API Key error (401). Please verify your OpenRouter credentials."
        
        return {
            "success": False,
            "suggestions": [],
            "error": user_friendly_error
        }


@intelligent_cache(endpoint="lesson_plan", cache_type="sqlite")
def generate_lesson_plan(
    grade_level: str,
    subject: str,
    topic: str,
    language: str,
    additional_notes: str,
    api_key: str,
    model: str,
    curriculum_version: str = "K-12 Standard"
) -> dict:
    """
    Generate a complete lesson plan using OpenRouter LLM.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "content": None,
            "quiz_data": [],
            "structure_complete": False,
            "missing_sections": [],
            "provider_used": "OpenRouter",
            "curriculum_version": curriculum_version,
            "error": "No OpenRouter API key found. Please configure your API key."
        }

    try:
        llm = initialize_llm(api_key, model)
        prompt = get_lesson_plan_prompt(curriculum_version)
        chain = prompt | llm | StrOutputParser()

        response = chain.invoke({
            "grade_level": grade_level,
            "subject": subject,
            "topic": topic,
            "language": language,
            "additional_notes": additional_notes if additional_notes else "None provided."
        })

        quiz_data = extract_quiz_from_content(response)
        structure_check = validate_dlp_structure(response)

        return {
            "success": True,
            "content": response,
            "quiz_data": quiz_data,
            "structure_complete": structure_check["complete"],
            "missing_sections": structure_check["missing_sections"],
            "provider_used": "OpenRouter",
            "curriculum_version": curriculum_version,
            "error": None
        }

    except Exception as e:
        error_str = str(e)
        user_friendly_error = error_str
        
        if "401" in error_str and "User not found" in error_str:
            user_friendly_error = "Authentication failed (401 - User not found). Please verify your OpenRouter API key in .env or Streamlit Secrets is valid and active."
        elif "401" in error_str:
            user_friendly_error = "API Key error (401). Please verify your OpenRouter credentials."
            
        return {
            "success": False,
            "content": None,
            "quiz_data": [],
            "structure_complete": False,
            "missing_sections": [],
            "provider_used": "OpenRouter",
            "curriculum_version": curriculum_version,
            "error": user_friendly_error
        }