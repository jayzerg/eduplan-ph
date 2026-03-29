# src/validators.py
"""
Input validation and sanitization for EduPlan PH.
Prevents empty API calls and provides user-friendly error messages.
"""

import os


def validate_inputs(topic: str, api_key: str) -> dict:
    """
    Validate user inputs before making an API call.
    Checks for valid topic and OpenRouter API key.
    """
    if not topic or topic.strip() == "":
        return {
            "valid": False,
            "message": "Please enter a topic. Example: 'Photosynthesis' or 'The Cry of Pugad Lawin'"
        }

    if len(topic.strip()) < 3:
        return {
            "valid": False,
            "message": "Topic is too short. Please provide at least 3 characters."
        }

    if len(topic.strip()) > 500:
        return {
            "valid": False,
            "message": "Topic is too long. Please keep it under 500 characters."
        }

    available_keys, _ = get_available_api_keys()
    if not any(available_keys.values()):
        return {
            "valid": False,
            "message": "No OpenRouter API key configured. Please add your key to the .env file (local) or Streamlit Cloud Secrets (production)."
        }

    return {
        "valid": True,
        "message": "All inputs valid."
    }


def get_available_api_keys() -> tuple[dict, dict]:
    """
    Check which API keys are available from environment or secrets.
    Returns a tuple of (keys dict, debug info dict).
    Checks Streamlit secrets first, then falls back to .env / environment variables.
    """
    from dotenv import load_dotenv
    load_dotenv()

    keys = {
        "OPENROUTER_API_KEY": ""
    }

    for key_name in keys:
        # Try Streamlit secrets first
        secret_val = ""
        try:
            import streamlit as st
            secret_val = st.secrets.get(key_name, "")
            # Ignore placeholder values
            if secret_val and "your_" in secret_val.lower():
                secret_val = ""
        except Exception:
            secret_val = ""
        
        # Use secret if valid, otherwise fall back to env var
        if secret_val and secret_val.strip():
            keys[key_name] = secret_val.strip()
        else:
            env_val = os.getenv(key_name, "")
            keys[key_name] = env_val.strip() if env_val else ""

    loaded_count = sum(1 for v in keys.values() if v and v.strip())
    debug_info = {
        "loaded_count": loaded_count,
        "keys_loaded": [k for k, v in keys.items() if v and v.strip()]
    }

    return keys, debug_info


def get_api_key_for_provider() -> tuple[str, dict]:
    """
    Get the OpenRouter API key.
    Returns a tuple of (api_key, debug_info).
    """
    available, debug_info = get_available_api_keys()
    key = available.get("OPENROUTER_API_KEY", "")
    return key, debug_info