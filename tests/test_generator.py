# tests/test_generator.py
"""
Unit tests for AI chain output structure in EduPlan PH.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from generator import validate_dlp_structure, extract_quiz_from_content


class TestDLPValidation:
    def test_complete_lesson_plan(self):
        content = """
        **I. OBJECTIVES**
        Content here
        
        **II. CONTENT**
        Subject: Science
        Grade Level: Grade 5
        
        **III. LEARNING RESOURCES**
        Materials listed here
        
        **IV. PROCEDURES**
        Steps here
        
        **V. ASSESSMENT**
        Quiz here
        
        **VI. REFLECTION**
        Reflection notes
        """
        result = validate_dlp_structure(content)
        assert result["complete"] == True
        assert len(result["missing_sections"]) == 0

    def test_incomplete_lesson_plan(self):
        content = """
        **I. OBJECTIVES**
        Content here
        
        **II. CONTENT**
        Subject: Science
        """
        result = validate_dlp_structure(content)
        assert result["complete"] == False
        assert len(result["missing_sections"]) > 0

    def test_empty_content(self):
        result = validate_dlp_structure("")
        assert result["complete"] == False
        assert len(result["missing_sections"]) == 6


class TestQuizExtraction:
    def test_extract_simple_quiz(self):
        content = """
        1. What is photosynthesis?
           A. The process by which plants make food
           B. A type of animal
           C. A chemical compound
           D. A geological event
           Answer: A
        
        2. What do plants need for photosynthesis?
           A. Water
           B. Soil
           C. Rocks
           D. Animals
           Answer: A
        """
        quiz = extract_quiz_from_content(content)
        assert len(quiz) >= 1
        assert quiz[0]["question"]
        assert quiz[0]["correct_answer"]

    def test_extract_no_quiz(self):
        content = """
        **I. OBJECTIVES**
        No quiz questions here.
        """
        quiz = extract_quiz_from_content(content)
        assert len(quiz) == 0

    def test_extract_empty_content(self):
        quiz = extract_quiz_from_content("")
        assert len(quiz) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])