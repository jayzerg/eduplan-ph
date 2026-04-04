# src/validators.py
"""
Input validation and sanitization for EduPlan PH.
Prevents empty API calls and provides user-friendly error messages.
"""

import os
import re


# Supported grade levels
SUPPORTED_GRADE_LEVELS = [
    "Kindergarten", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5",
    "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10",
    "Grade 11", "Grade 12"
]

# Supported subjects
SUPPORTED_SUBJECTS = [
    "Mathematics", "Science", "English", "Filipino", "Araling Panlipunan",
    "MAPEH", "Edukasyon sa Pagpapakatao", "Technology and Livelihood Education",
    "Computer Science", "Physical Education", "Health", "Music", "Arts",
    "History", "Literature", "Biology", "Chemistry", "Physics", "General Science"
]

# Supported languages
SUPPORTED_LANGUAGES = [
    "English", "Filipino", "Tagalog", "Cebuano", "Ilocano", "Hiligaynon",
    "Waray", "Kapampangan", "Pangasinan", "Bicolano"
]


def quick_validate(
    topic: str = None,
    api_key: str = None,
    grade_level: str = None,
    subject: str = None,
    language: str = None
) -> dict:
    """
    Perform comprehensive input validation before API invocation.
    
    Validates:
    - Topic (empty, whitespace-only, too short, too long)
    - API key (exists and properly formatted)
    - Grade level (valid selection from supported list)
    - Subject (valid selection from supported list)
    - Language (valid selection from supported list)
    
    Args:
        topic: The lesson topic to validate
        api_key: OpenRouter API key to validate
        grade_level: Selected grade level
        subject: Selected subject area
        language: Selected language for output
    
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": list of error messages,
            "warnings": list of warning messages,
            "sanitized_inputs": dict of cleaned inputs
        }
    """
    errors = []
    warnings = []
    sanitized_inputs = {}
    
    # Validate topic
    topic_result = _validate_topic(topic)
    if topic_result["error"]:
        errors.append(topic_result["error"])
    if topic_result["warning"]:
        warnings.append(topic_result["warning"])
    if topic_result["sanitized"]:
        sanitized_inputs["topic"] = topic_result["sanitized"]
    
    # Validate API key
    api_key_result = _validate_api_key(api_key)
    if api_key_result["error"]:
        errors.append(api_key_result["error"])
    if api_key_result["warning"]:
        warnings.append(api_key_result["warning"])
    if api_key_result["sanitized"]:
        sanitized_inputs["api_key"] = api_key_result["sanitized"]
    
    # Validate grade level
    grade_result = _validate_grade_level(grade_level)
    if grade_result["error"]:
        errors.append(grade_result["error"])
    if grade_result["warning"]:
        warnings.append(grade_result["warning"])
    if grade_result["sanitized"]:
        sanitized_inputs["grade_level"] = grade_result["sanitized"]
    
    # Validate subject
    subject_result = _validate_subject(subject)
    if subject_result["error"]:
        errors.append(subject_result["error"])
    if subject_result["warning"]:
        warnings.append(subject_result["warning"])
    if subject_result["sanitized"]:
        sanitized_inputs["subject"] = subject_result["sanitized"]
    
    # Validate language
    language_result = _validate_language(language)
    if language_result["error"]:
        errors.append(language_result["error"])
    if language_result["warning"]:
        warnings.append(language_result["warning"])
    if language_result["sanitized"]:
        sanitized_inputs["language"] = language_result["sanitized"]
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "sanitized_inputs": sanitized_inputs
    }


def _validate_topic(topic: str) -> dict:
    """Validate topic input."""
    result = {"error": None, "warning": None, "sanitized": None}
    
    if topic is None:
        result["error"] = "Topic is required and cannot be empty."
        return result
    
    # Check for empty or whitespace-only
    if not isinstance(topic, str) or topic.strip() == "":
        result["error"] = "Topic cannot be empty or whitespace-only."
        return result
    
    sanitized = topic.strip()
    
    # Check minimum length (at least 3 characters)
    if len(sanitized) < 3:
        result["error"] = f"Topic is too short. Minimum 3 characters required (got {len(sanitized)})."
        return result
    
    # Check maximum length (500 characters)
    if len(sanitized) > 500:
        result["error"] = f"Topic is too long. Maximum 500 characters allowed (got {len(sanitized)})."
        return result
    
    # Warning for potentially too-specific topics
    if len(sanitized) > 200:
        result["warning"] = "Topic is quite long. Consider using a more concise topic for better results."
    
    result["sanitized"] = sanitized
    return result


def _validate_api_key(api_key: str) -> dict:
    """Validate OpenRouter API key."""
    result = {"error": None, "warning": None, "sanitized": None}
    
    # If no API key provided, try to get from environment
    if api_key is None or api_key.strip() == "":
        # Try to fetch from environment
        env_key = os.getenv("OPENROUTER_API_KEY", "")
        if env_key and env_key.strip():
            result["sanitized"] = env_key.strip()
            return result
        
        result["error"] = "OpenRouter API key is required. Please provide your API key or set OPENROUTER_API_KEY environment variable."
        return result
    
    sanitized = api_key.strip()
    
    # Basic format validation (API keys are typically alphanumeric strings)
    # OpenRouter keys don't have a specific known prefix, but should be non-empty
    if len(sanitized) < 10:
        result["error"] = "API key appears to be invalid. API keys should be at least 10 characters long."
        return result
    
    # Check for placeholder values
    placeholder_patterns = [
        r"^your_",
        r"^sk-xxx",
        r"^placeholder",
        r"^example",
        r"^\*\*\*\*"
    ]
    for pattern in placeholder_patterns:
        if re.match(pattern, sanitized, re.IGNORECASE):
            result["error"] = "API key appears to be a placeholder. Please provide your actual OpenRouter API key."
            return result
    
    result["sanitized"] = sanitized
    return result


def _validate_grade_level(grade_level: str) -> dict:
    """Validate grade level selection."""
    result = {"error": None, "warning": None, "sanitized": None}
    
    if grade_level is None or grade_level.strip() == "":
        result["error"] = f"Grade level is required. Please select from: {', '.join(SUPPORTED_GRADE_LEVELS[:5])}..."
        return result
    
    sanitized = grade_level.strip()
    
    # Normalize case for comparison
    normalized = sanitized.lower()
    
    # Check against supported grade levels
    matched = None
    for valid_level in SUPPORTED_GRADE_LEVELS:
        if valid_level.lower() == normalized:
            matched = valid_level
            break
    
    if matched is None:
        # Provide helpful error with closest matches
        result["error"] = f"Invalid grade level '{grade_level}'. Supported levels: {', '.join(SUPPORTED_GRADE_LEVELS)}"
        return result
    
    result["sanitized"] = matched
    return result


def _validate_subject(subject: str) -> dict:
    """Validate subject selection."""
    result = {"error": None, "warning": None, "sanitized": None}
    
    if subject is None or subject.strip() == "":
        result["error"] = f"Subject is required. Please select from: {', '.join(SUPPORTED_SUBJECTS[:5])}..."
        return result
    
    sanitized = subject.strip()
    
    # Normalize case for comparison
    normalized = sanitized.lower()
    
    # Check against supported subjects
    matched = None
    for valid_subject in SUPPORTED_SUBJECTS:
        if valid_subject.lower() == normalized:
            matched = valid_subject
            break
    
    if matched is None:
        # Provide helpful error with closest matches
        result["error"] = f"Invalid subject '{subject}'. Supported subjects: {', '.join(SUPPORTED_SUBJECTS)}"
        return result
    
    result["sanitized"] = matched
    return result


def _validate_language(language: str) -> dict:
    """Validate language selection."""
    result = {"error": None, "warning": None, "sanitized": None}
    
    if language is None or language.strip() == "":
        result["warning"] = "No language specified. Defaulting to English."
        result["sanitized"] = "English"
        return result
    
    sanitized = language.strip()
    
    # Normalize case for comparison
    normalized = sanitized.lower()
    
    # Check against supported languages
    matched = None
    for valid_language in SUPPORTED_LANGUAGES:
        if valid_language.lower() == normalized:
            matched = valid_language
            break
    
    if matched is None:
        result["error"] = f"Unsupported language '{language}'. Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
        return result
    
    result["sanitized"] = matched
    return result


def validate_inputs(topic: str, api_key: str) -> dict:
    """
    Validate user inputs before making an API call.
    Checks for valid topic and OpenRouter API key.
    Deprecated: Use quick_validate() for comprehensive validation.
    
    This legacy function only validates topic and API key.
    For full validation including grade_level, subject, and language,
    use quick_validate() instead.
    """
    # Validate just topic and API key for backward compatibility
    result = quick_validate(topic=topic, api_key=api_key)
    
    # Filter out errors related to missing grade_level/subject/language
    # since the old function didn't require those
    filtered_errors = [
        err for err in result["errors"] 
        if "grade level" not in err.lower() 
        and "subject" not in err.lower()
        and "language" not in err.lower()
    ]
    
    if filtered_errors:
        return {
            "valid": False,
            "message": filtered_errors[0]
        }
    
    return {
        "valid": True,
        "message": "All inputs valid."
    }