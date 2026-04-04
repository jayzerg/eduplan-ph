# tests/test_validators.py
"""
Unit tests for input validation functions in EduPlan PH.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validators import validate_inputs, quick_validate


class TestValidateInputs:
    def test_empty_topic(self):
        result = validate_inputs("", "fake_key")
        assert result["valid"] == False
        assert "topic" in result["message"].lower()

    def test_whitespace_topic(self):
        result = validate_inputs("   ", "fake_key")
        assert result["valid"] == False

    def test_short_topic(self):
        result = validate_inputs("ab", "fake_key")
        assert result["valid"] == False
        assert "short" in result["message"].lower()

    def test_long_topic(self):
        long_topic = "a" * 501
        result = validate_inputs(long_topic, "fake_key")
        assert result["valid"] == False
        assert "long" in result["message"].lower()

    def test_valid_topic(self, monkeypatch):
        # Mock environment variable for API key
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake_key_12345")
        result = validate_inputs("Photosynthesis", "fake_key_12345")
        assert result["valid"] == True


class TestQuickValidate:
    """Tests for the new quick_validate function."""
    
    def test_valid_all_inputs(self):
        result = quick_validate(
            topic="Photosynthesis",
            api_key="sk-test-abc123456789",
            grade_level="Grade 5",
            subject="Science",
            language="English"
        )
        assert result["valid"] == True
        assert len(result["errors"]) == 0
        assert result["sanitized_inputs"]["topic"] == "Photosynthesis"
        assert result["sanitized_inputs"]["grade_level"] == "Grade 5"
        assert result["sanitized_inputs"]["subject"] == "Science"
        assert result["sanitized_inputs"]["language"] == "English"
    
    def test_empty_topic(self):
        result = quick_validate(topic="", api_key="sk-test-abc123456789")
        assert result["valid"] == False
        assert any("empty" in err.lower() for err in result["errors"])
    
    def test_whitespace_topic(self):
        result = quick_validate(topic="   ", api_key="sk-test-abc123456789")
        assert result["valid"] == False
    
    def test_short_topic(self):
        result = quick_validate(topic="ab", api_key="sk-test-abc123456789")
        assert result["valid"] == False
        assert any("short" in err.lower() for err in result["errors"])
    
    def test_long_topic(self):
        long_topic = "a" * 501
        result = quick_validate(topic=long_topic, api_key="sk-test-abc123456789")
        assert result["valid"] == False
        assert any("long" in err.lower() for err in result["errors"])
    
    def test_invalid_grade_level(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            grade_level="Grade 13"
        )
        assert result["valid"] == False
        assert any("grade level" in err.lower() for err in result["errors"])
    
    def test_invalid_subject(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            grade_level="Grade 5",
            subject="Invalid Subject"
        )
        assert result["valid"] == False
        assert any("subject" in err.lower() for err in result["errors"])
    
    def test_unsupported_language(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            language="Spanish"
        )
        assert result["valid"] == False
        assert any("language" in err.lower() for err in result["errors"])
    
    def test_missing_api_key(self):
        result = quick_validate(topic="Photosynthesis")
        assert result["valid"] == False
        assert any("api key" in err.lower() for err in result["errors"])
    
    def test_placeholder_api_key(self):
        result = quick_validate(topic="Photosynthesis", api_key="your_api_key_here")
        assert result["valid"] == False
        assert any("placeholder" in err.lower() for err in result["errors"])
    
    def test_case_insensitive_grade_level(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            grade_level="grade 5",
            subject="Mathematics"
        )
        assert result["valid"] == True
        assert result["sanitized_inputs"]["grade_level"] == "Grade 5"
    
    def test_case_insensitive_subject(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            grade_level="Grade 5",
            subject="mathematics"
        )
        assert result["valid"] == True
        assert result["sanitized_inputs"]["subject"] == "Mathematics"
    
    def test_default_language(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            grade_level="Grade 5",
            subject="Mathematics"
        )
        assert result["valid"] == True
        assert result["sanitized_inputs"]["language"] == "English"
        assert any("default" in warn.lower() for warn in result["warnings"])
    
    def test_filipino_language(self):
        result = quick_validate(
            topic="Math",
            api_key="sk-test-abc123456789",
            grade_level="Grade 5",
            subject="Mathematics",
            language="Filipino"
        )
        assert result["valid"] == True
        assert result["sanitized_inputs"]["language"] == "Filipino"
    
    def test_multiple_errors(self):
        result = quick_validate(topic="", api_key="")
        assert result["valid"] == False
        assert len(result["errors"]) >= 2  # At least topic and API key errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])