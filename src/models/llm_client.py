"""Shared language-model client."""

from langchain_groq import ChatGroq

from src.utils.config import settings

llm = ChatGroq(model=settings.llm_model, temperature=0.5)
