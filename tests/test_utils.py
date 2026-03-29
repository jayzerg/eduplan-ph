# tests/test_utils.py
"""
Unit tests for export functions in EduPlan PH.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import markdown_to_plain_text, export_to_docx, export_to_pdf, export_quiz_to_csv


class TestMarkdownConversion:
    def test_remove_headers(self):
        md = "# Header\n## Subheader\n### Sub-subheader"
        result = markdown_to_plain_text(md)
        assert "#" not in result

    def test_remove_bold_markers(self):
        md = "This is **bold** text"
        result = markdown_to_plain_text(md)
        assert "**" not in result
        assert "bold" in result

    def test_remove_italic_markers(self):
        md = "This is *italic* text"
        result = markdown_to_plain_text(md)
        assert "*" not in result

    def test_preserve_text_content(self):
        md = "**I. OBJECTIVES**\n- Content Standard:\n- Performance Standard:"
        result = markdown_to_plain_text(md)
        assert "OBJECTIVES" in result
        assert "Content Standard" in result


class TestDOCXExport:
    def test_export_basic_content(self):
        content = "**I. OBJECTIVES**\n- Learning objective"
        result = export_to_docx(content, "Test Topic", "Grade 5", "Science")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_empty_content(self):
        result = export_to_docx("", "Topic", "Grade 1", "Math")
        assert isinstance(result, bytes)


class TestPDFExport:
    def test_export_basic_content(self):
        content = "**I. OBJECTIVES**\n- Learning objective"
        result = export_to_pdf(content, "Test Topic", "Grade 5", "Science")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_empty_content(self):
        result = export_to_pdf("", "Topic", "Grade 1", "Math")
        assert isinstance(result, bytes)


class TestCSVExport:
    def test_export_quiz_data(self):
        quiz_data = [
            {
                "number": 1,
                "question": "What is 2+2?",
                "choice_a": "3",
                "choice_b": "4",
                "choice_c": "5",
                "choice_d": "6",
                "correct_answer": "B"
            }
        ]
        result = export_quiz_to_csv(quiz_data)
        assert "Item #" in result
        assert "Question" in result
        assert "What is 2+2?" in result
        assert "4" in result

    def test_export_empty_quiz(self):
        result = export_quiz_to_csv([])
        assert result == "No quiz data available."

    def test_export_no_quiz(self):
        result = export_quiz_to_csv(None)
        assert result == "No quiz data available."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])