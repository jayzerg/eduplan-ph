# src/config.py
"""
Centralized configuration for EduPlan PH.
All constants, dropdown options, and model settings are defined here
to enable single-point updates without searching through UI code.
"""

GRADE_LEVELS = [
    "Kindergarten",
    "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9", "Grade 10",
    "Grade 11", "Grade 12"
]

SUBJECTS = [
    "Mother Tongue",
    "Filipino",
    "English",
    "Mathematics",
    "Science",
    "Araling Panlipunan (Social Studies)",
    "Edukasyon sa Pagpapakatao (Values Education)",
    "Music, Arts, Physical Education, and Health (MAPEH)",
    "Edukasyong Pantahanan at Pangkabuhayan (EPP)",
    "Technology and Livelihood Education (TLE)",
    "General Academic Strand (GAS)",
    "Other"
]

LANGUAGES = ["English", "Filipino", "Taglish (Mixed English and Filipino)"]

PROVIDERS = ["OpenRouter"]

PROVIDER_MODELS = {
    "OpenRouter": [
        "stepfun/step-3.5-flash:free",
        "anthropic/claude-3-haiku:free",
        "google/gemini-pro",
        "meta-llama/llama-3-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free"
    ]
}

DEFAULT_PROVIDER = "OpenRouter"
DEFAULT_MODEL = "stepfun/step-3.5-flash:free"

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

APP_TITLE = "EduPlan PH"
APP_ICON = "🇵🇭"
APP_VERSION = "1.0.2"