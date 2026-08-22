"""Routing and summarization prompts."""

ROUTER_PROMPT = """
Classify this query as exactly one word:
- summary: full-video summary, timeline, topics, or notes
- qa: a specific question

Query: {query}
"""

SUMMARY_INTENT_PROMPT = """
Extract the requested summarization format and return valid JSON:
{{
  "type": "timeline | section | full",
  "granularity": "minute | coarse | none",
  "style": "bullets | paragraph | notes"
}}

Query: {query}
Output only JSON.
"""
