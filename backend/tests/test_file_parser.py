"""Unit tests for FileParser service."""

from __future__ import annotations

import pytest

from app.core.exceptions import FileParsingError
from app.services.file_parser import FileParser


class TestFileParser:
    """Test suite for file parsing functionality."""

    def test_parse_txt_utf8(self):
        """Should decode UTF-8 encoded text."""
        content = "Hello World\nThis is a protocol\nMaterials: Formaldehyde".encode("utf-8")
        result = FileParser.parse(content, "protocol.txt")
        assert "Hello World" in result
        assert "Formaldehyde" in result

    def test_parse_txt_gbk(self):
        """Should decode GBK encoded Chinese text."""
        content = "实验方案\n材料：甲醛、乙醇".encode("gbk")
        result = FileParser.parse(content, "protocol.txt")
        assert "实验方案" in result

    def test_parse_txt_invalid_encoding_fallback(self):
        """Should fall back to replace mode for undecodable bytes."""
        content = b"\xff\xfe\x00\x01Hello"
        result = FileParser.parse(content, "protocol.txt")
        assert "Hello" in result

    def test_parse_unsupported_extension(self):
        """Should raise FileParsingError for unsupported file types."""
        with pytest.raises(FileParsingError, match="Unsupported"):
            FileParser.parse(b"test", "image.png")

    def test_parse_unsupported_no_extension(self):
        """Should raise FileParsingError for files without extension."""
        with pytest.raises(FileParsingError, match="Unsupported"):
            FileParser.parse(b"test", "noextension")

    def test_parse_docx_empty(self):
        """Should handle minimal docx content."""
        # This test verifies error handling — actual DOCX requires valid binary
        with pytest.raises(FileParsingError, match="Failed to parse"):
            FileParser.parse(b"not a docx file", "test.docx")
