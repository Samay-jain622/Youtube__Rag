"""Tests for the API source structure without external service calls."""

import ast
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.api.schemas import ChatRequest, VideoRequest


class ApiStructureTests(unittest.TestCase):
    def test_api_sources_are_valid_python(self) -> None:
        for source_file in Path("src/api").glob("*.py"):
            with self.subTest(source_file=source_file):
                ast.parse(source_file.read_text(encoding="utf-8"))

    def test_video_id_validation(self) -> None:
        self.assertEqual(VideoRequest(video_id="3dhcmeOTZ_Q").video_id, "3dhcmeOTZ_Q")
        with self.assertRaises(ValidationError):
            VideoRequest(video_id="not-a-valid-id")

    def test_query_cannot_be_empty(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest(video_id="3dhcmeOTZ_Q", query="")
