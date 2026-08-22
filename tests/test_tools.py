"""Tests for dependency-free helper tools."""

import unittest

from src.utils.helpers import format_timestamp


class HelperTests(unittest.TestCase):
    def test_format_timestamp(self) -> None:
        self.assertEqual(format_timestamp(125), "02:05")
