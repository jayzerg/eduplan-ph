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
    "STEM (Science, Technology, Engineering, Mathematics)",
    "ABM (Accountancy, Business, Management)",
    "HUMSS (Humanities and Social Sciences)",
    "TVL (Technical-Vocational-Livelihood)",
    "Other"
]

LANGUAGES = ["English", "Filipino", "Taglish (Mixed English and Filipino)"]

CURRICULUM_VERSIONS = ["K-12 Standard", "MATATAG Pilot"]

MATATAG_SUBJECTS = [
    "Mother Tongue",
    "Filipino",
    "English",
    "Mathematics",
    "Science",
    "Araling Panlipunan (Social Studies)",
    "Edukasyon sa Pagpapakatao (Values Education)",
    "Music, Arts, Physical Education, and Health (MAPEH)",
]

MATATAG_HELPER_TEXT = (
    "MATATAG focuses on decongested competencies prioritizing "
    "foundational skills in literacy, numeracy, and character "
    "development per DepEd's latest framework."
)

CURRICULUM_ALIGNMENT_LABELS = {
    "K-12 Standard": "Aligned with: K-12 Standard Curriculum",
    "MATATAG Pilot": "Aligned with: MATATAG Curriculum 2024",
}

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
APP_ICON = "ph_flag.png"
APP_EMOJI = "🇵🇭"
__version__ = "1.0.2"