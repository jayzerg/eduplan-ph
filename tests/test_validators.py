# tests/test_validators.py
"""
Unit tests for input validation functions in EduPlan PH.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validators import validate_inputs


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

    def test_valid_topic(self):
        result = validate_inputs("Photosynthesis", "fake_key")
        assert result["valid"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])