"""Tests for query routing behavior."""

import ast
import unittest
from pathlib import Path

from sqlalchemy import create_engine

from src.models.database import Base
import src.models.entities  # noqa: F401


class AgentStructureTests(unittest.TestCase):
    def test_agent_source_is_valid_python(self) -> None:
        source = Path("src/agent/agent.py").read_text(encoding="utf-8")
        ast.parse(source)

    def test_database_schema_can_be_created(self) -> None:
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(test_engine)
        self.assertEqual(
            set(Base.metadata.tables),
            {"videos", "transcript_chunks"},
        )
